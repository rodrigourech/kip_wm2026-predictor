"""
Trainiert einen Random-Forest-Klassifikator zur Vorhersage von Spielausgängen
(Sieg Team A / Unentschieden / Sieg Team B) auf Basis von match_features.csv.

Methodische Entscheidung: Zeitlicher statt zufälliger Train/Test-Split.
Da das Modell reale, zukünftige Spiele vorhersagen soll, testen wir auf den
chronologisch letzten 20% der Spiele - ein zufälliger Split würde die
Performance zu optimistisch einschätzen (das Modell könnte sonst quasi
"aus der Zukunft in die Vergangenheit" lernen, wenn ähnliche Spiele zeitlich
nah beieinander in Training UND Test landen).

Fehlende Werte (Ballbesitz/Schüsse/Ecken, ~19% der Zeilen) werden mit dem
Median der jeweiligen Spalte aufgefüllt (Random Forest kann nicht direkt mit
NaN umgehen).

Aufruf:
    python src/train_model.py
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from config import DATA_PROCESSED_DIR, PROJECT_ROOT

FEATURES_FILE = DATA_PROCESSED_DIR / "match_features.csv"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Spalten, die NICHT als Modell-Feature verwendet werden (Identifikatoren,
# Zielvariable, oder Werte, die zum Vorhersagezeitpunkt nicht bekannt wären)
NON_FEATURE_COLS = ["fixture_id", "date", "team_a", "team_b", "goals_a", "goals_b", "result"]

TEST_SIZE_FRACTION = 0.2  # letzte 20% der Spiele (chronologisch) als Testset


def load_data() -> pd.DataFrame:
    df = pd.read_csv(FEATURES_FILE)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def chronological_split(df: pd.DataFrame):
    """Teilt nach Datum: die letzten TEST_SIZE_FRACTION der Spiele sind Test."""
    split_idx = int(len(df) * (1 - TEST_SIZE_FRACTION))
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    return train_df, test_df


def main():
    df = load_data()
    print(f"Geladen: {len(df)} Spiele ({df['date'].min().date()} bis {df['date'].max().date()})\n")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    print(f"Verwendete Features ({len(feature_cols)}): {feature_cols}\n")

    train_df, test_df = chronological_split(df)
    print(f"Training: {len(train_df)} Spiele (bis {train_df['date'].max().date()})")
    print(f"Test:     {len(test_df)} Spiele (ab {test_df['date'].min().date()})\n")

    X_train = train_df[feature_cols]
    y_train = train_df["result"]
    X_test = test_df[feature_cols]
    y_test = test_df["result"]

    # Fehlende Werte (v.a. Ballbesitz/Schüsse/Ecken) mit Median aus dem
    # TRAININGSSET auffüllen (nicht mit Test-Median - sonst wieder Leakage)
    imputer = SimpleImputer(strategy="median")
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_imputed, y_train)

    y_pred = model.predict(X_test_imputed)

    print("=" * 60)
    print("EVALUATION")
    print("=" * 60)
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.3f}\n")

    print("Classification Report:")
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix (Zeilen=tatsächlich, Spalten=vorhergesagt):")
    labels = sorted(y_test.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    print(f"{'':>12}" + "".join(f"{l:>12}" for l in labels))
    for label, row in zip(labels, cm):
        print(f"{label:>12}" + "".join(f"{v:>12}" for v in row))

    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE (Top 10)")
    print("=" * 60)
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    for feat, imp in importances.head(10).items():
        print(f"  {feat:<25} {imp:.3f}")

    # Modell + Imputer + Feature-Liste speichern (für spätere Nutzung im Dashboard)
    joblib.dump(model, MODELS_DIR / "random_forest_model.pkl")
    joblib.dump(imputer, MODELS_DIR / "imputer.pkl")
    (MODELS_DIR / "feature_columns.json").write_text(
        json.dumps(feature_cols, indent=2), encoding="utf-8"
    )

    print(f"\nModell gespeichert in: {MODELS_DIR}")


if __name__ == "__main__":
    main()
