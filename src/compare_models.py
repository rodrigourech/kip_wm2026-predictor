"""
Modellvergleich (Stretchgoal laut Exposé): Random Forest vs. Logistic
Regression vs. Gradient Boosting für die Sieg/Unentschieden/Niederlage-
Klassifikation.

Nutzt exakt denselben chronologischen Split, dieselben Features und dieselbe
Median-Imputation wie train_models.py, damit der Vergleich fair ist (keine
unterschiedlichen Trainingsdaten pro Modell).

Aufruf:
    python src/compare_models.py
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler

from config import DATA_PROCESSED_DIR, PROJECT_ROOT

FEATURES_FILE = DATA_PROCESSED_DIR / "match_features.csv"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

NON_FEATURE_COLS = ["fixture_id", "date", "team_a", "team_b", "goals_a", "goals_b", "result"]
TEST_SIZE_FRACTION = 0.2


def load_data() -> pd.DataFrame:
    df = pd.read_csv(FEATURES_FILE)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def chronological_split(df: pd.DataFrame):
    split_idx = int(len(df) * (1 - TEST_SIZE_FRACTION))
    return df.iloc[:split_idx], df.iloc[split_idx:]


def evaluate_model(name, model, X_train, y_train, X_test, y_test):
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro")

    print("\n" + "#" * 60)
    print(f"# {name}")
    print("#" * 60)
    print(f"Accuracy:      {acc:.3f}")
    print(f"F1 (macro):    {f1_macro:.3f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    labels = sorted(y_test.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    print("Confusion Matrix (Zeilen=tatsächlich, Spalten=vorhergesagt):")
    print(f"{'':>12}" + "".join(f"{l:>12}" for l in labels))
    for label, row in zip(labels, cm):
        print(f"{label:>12}" + "".join(f"{v:>12}" for v in row))

    return {"model": name, "accuracy": round(acc, 4), "f1_macro": round(f1_macro, 4)}


def main():
    df = load_data()
    print(f"Geladen: {len(df)} Spiele ({df['date'].min().date()} bis {df['date'].max().date()})\n")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    print(f"Verwendete Features ({len(feature_cols)}): {feature_cols}\n")

    train_df, test_df = chronological_split(df)
    print(f"Training: {len(train_df)} Spiele (bis {train_df['date'].max().date()})")
    print(f"Test:     {len(test_df)} Spiele (ab {test_df['date'].min().date()})")

    X_train_raw = train_df[feature_cols]
    y_train = train_df["result"]
    X_test_raw = test_df[feature_cols]
    y_test = test_df["result"]

    # Gleiche Median-Imputation wie train_models.py (nur aus Trainingsset)
    imputer = SimpleImputer(strategy="median")
    X_train_imputed = imputer.fit_transform(X_train_raw)
    X_test_imputed = imputer.transform(X_test_raw)

    # Logistic Regression braucht standardisierte Features (Random Forest/GB
    # sind skaleninvariant und brauchen das nicht, schadet aber auch nicht -
    # wir skalieren trotzdem für alle drei, um exakt dieselben Eingabedaten
    # zu verwenden und den Vergleich sauber zu halten)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)

    results = []

    results.append(evaluate_model(
        "Random Forest (bestehendes Modell)",
        RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1),
        X_train_scaled, y_train, X_test_scaled, y_test,
    ))

    results.append(evaluate_model(
        "Logistic Regression",
        LogisticRegression(max_iter=1000, random_state=42),
        X_train_scaled, y_train, X_test_scaled, y_test,
    ))

    results.append(evaluate_model(
        "Gradient Boosting",
        GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42),
        X_train_scaled, y_train, X_test_scaled, y_test,
    ))

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG - MODELLVERGLEICH")
    print("=" * 60)
    print(f"{'Modell':<38}{'Accuracy':>12}{'F1 (macro)':>14}")
    print("-" * 64)
    for r in sorted(results, key=lambda x: -x["accuracy"]):
        print(f"{r['model']:<38}{r['accuracy']:>12.3f}{r['f1_macro']:>14.3f}")

    output_path = MODELS_DIR / "model_comparison.json"
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nErgebnisse gespeichert: {output_path}")


if __name__ == "__main__":
    main()
