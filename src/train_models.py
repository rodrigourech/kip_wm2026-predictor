"""
Trainiert beide Modelle für den WM 2026 Match Predictor auf Basis von
match_features.csv:

  1. Klassifikator (Random Forest): Sieg Team A / Unentschieden / Sieg Team B
     - liefert die Sieg-Wahrscheinlichkeit fürs Dashboard.
  2. Regressor (Random Forest, Multi-Output): erwartete Tore pro Team
     (goals_a, goals_b) - ergänzt den Klassifikator um ein konkretes
     Spielergebnis, ersetzt ihn aber nicht.

Methodische Entscheidungen (gelten für beide Modelle):
  - Zeitlicher statt zufälliger Train/Test-Split: da das Modell reale,
    zukünftige Spiele vorhersagen soll, testen wir auf den chronologisch
    letzten 20% der Spiele - ein zufälliger Split würde die Performance zu
    optimistisch einschätzen (das Modell könnte sonst aus zeitlich nahen,
    ähnlichen Spielen in Training und Test "schummeln").
  - Fehlende Werte (Ballbesitz/Schüsse/Ecken, ~19% der Zeilen) werden per
    Median-Imputation aufgefüllt, wobei der Median NUR aus dem Trainingsset
    berechnet wird (nicht aus dem Testset - sonst erneutes Data Leakage).
  - Random Forest Regressor statt der in der Fussball-Analytik "klassischen"
    Poisson-Regression für die Tore-Vorhersage - Begründung: Konsistenz mit
    dem Klassifikator und Fähigkeit, nichtlineare Interaktionseffekte
    zwischen Features abzubilden.

Aufruf:
    python src/train_models.py
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
)

from config import DATA_PROCESSED_DIR, PROJECT_ROOT

FEATURES_FILE = DATA_PROCESSED_DIR / "match_features.csv"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Spalten, die NICHT als Modell-Feature verwendet werden (Identifikatoren,
# Zielvariablen, oder Werte, die zum Vorhersagezeitpunkt nicht bekannt wären)
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
    return df.iloc[:split_idx], df.iloc[split_idx:]


def train_classifier(train_df, test_df, feature_cols, imputer, X_train_imputed, X_test_imputed):
    print("\n" + "#" * 60)
    print("# MODELL 1: KLASSIFIKATOR (Sieg A / Unentschieden / Sieg B)")
    print("#" * 60)

    y_train = train_df["result"]
    y_test = test_df["result"]

    model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
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

    joblib.dump(model, MODELS_DIR / "random_forest_model.pkl")
    joblib.dump(imputer, MODELS_DIR / "imputer.pkl")
    (MODELS_DIR / "feature_columns.json").write_text(json.dumps(feature_cols, indent=2), encoding="utf-8")
    print(f"\nModell gespeichert: random_forest_model.pkl, imputer.pkl, feature_columns.json")


def train_goals_regressor(train_df, test_df, feature_cols, imputer, X_train_imputed, X_test_imputed):
    print("\n" + "#" * 60)
    print("# MODELL 2: REGRESSOR (erwartete Tore pro Team)")
    print("#" * 60)

    y_train = train_df[["goals_a", "goals_b"]]
    y_test = test_df[["goals_a", "goals_b"]]

    # RandomForestRegressor unterstützt Multi-Output nativ (goals_a + goals_b
    # in einem Modell statt zwei separaten)
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train_imputed, y_train)

    y_pred = model.predict(X_test_imputed)

    print("=" * 60)
    print("EVALUATION")
    print("=" * 60)
    for i, target in enumerate(["goals_a", "goals_b"]):
        mae = mean_absolute_error(y_test[target], y_pred[:, i])
        rmse = np.sqrt(mean_squared_error(y_test[target], y_pred[:, i]))
        print(f"  {target}: MAE={mae:.3f} Tore, RMSE={rmse:.3f} Tore")

    # Aus den vorhergesagten Toren abgeleitetes Ergebnis - nur als Cross-Check
    # gegen den Klassifikator, NICHT als Ersatz für die Dashboard-Siegwahrscheinlichkeit
    predicted_result = np.where(
        y_pred[:, 0] > y_pred[:, 1] + 0.5, "A",
        np.where(y_pred[:, 1] > y_pred[:, 0] + 0.5, "B", "Draw"),
    )
    actual_result = test_df["result"].values
    accuracy_from_goals = (predicted_result == actual_result).mean()
    print(f"\n  Abgeleitete Ergebnis-Accuracy (aus Toren, Toleranz 0.5): {accuracy_from_goals:.3f}")
    print("  (Reiner Vergleichswert - fürs Dashboard weiterhin Modell 1 für Sieg-Wahrscheinlichkeit nutzen)")

    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE (Top 10, gemittelt über beide Zielgrössen)")
    print("=" * 60)
    importances = pd.Series(
        np.mean([est.feature_importances_ for est in model.estimators_], axis=0),
        index=feature_cols,
    ).sort_values(ascending=False)
    for feat, imp in importances.head(10).items():
        print(f"  {feat:<25} {imp:.3f}")

    joblib.dump(model, MODELS_DIR / "goals_regressor_model.pkl")
    joblib.dump(imputer, MODELS_DIR / "goals_imputer.pkl")
    (MODELS_DIR / "goals_feature_columns.json").write_text(json.dumps(feature_cols, indent=2), encoding="utf-8")
    print(f"\nModell gespeichert: goals_regressor_model.pkl, goals_imputer.pkl, goals_feature_columns.json")


def main():
    df = load_data()
    print(f"Geladen: {len(df)} Spiele ({df['date'].min().date()} bis {df['date'].max().date()})\n")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    print(f"Verwendete Features ({len(feature_cols)}): {feature_cols}\n")

    train_df, test_df = chronological_split(df)
    print(f"Training: {len(train_df)} Spiele (bis {train_df['date'].max().date()})")
    print(f"Test:     {len(test_df)} Spiele (ab {test_df['date'].min().date()})")

    X_train = train_df[feature_cols]
    X_test = test_df[feature_cols]

    # Gemeinsame Imputation für beide Modelle (gleiche Features, gleicher Split)
    imputer = SimpleImputer(strategy="median")
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    train_classifier(train_df, test_df, feature_cols, imputer, X_train_imputed, X_test_imputed)
    train_goals_regressor(train_df, test_df, feature_cols, imputer, X_train_imputed, X_test_imputed)

    print("\n" + "#" * 60)
    print(f"# Beide Modelle trainiert und gespeichert in: {MODELS_DIR}")
    print("#" * 60)


if __name__ == "__main__":
    main()
