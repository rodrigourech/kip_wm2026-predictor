"""
Trainiert ein Regressionsmodell zur Vorhersage der erwarteten Tore pro Team
(goals_a, goals_b) - ergänzt das bestehende Klassifikationsmodell
(train_model.py, Sieg A / Unentschieden / Sieg B), ersetzt es nicht.

Methodische Entscheidung: Random Forest Regressor statt der in der
Fussball-Analytik "klassischen" Poisson-Regression - Begründung: Konsistenz
mit dem Rest des Projekts (Random Forest ist bereits das Kernmodell laut
Exposé) und Fähigkeit, nichtlineare Interaktionseffekte zwischen Features
abzubilden. Poisson-Regression wäre die statistisch "sauberere" Wahl für
Zähldaten (Tore), aber ein zweites Modell-Framework hätte zusätzliche
Komplexität ohne klaren Mehrwert für dieses Projekt bedeutet.

Gleicher chronologischer Split und dieselben Features wie train_model.py,
damit die Ergebnisse vergleichbar bleiben.

Aufruf:
    python src/train_goals_model.py
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error

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


def main():
    df = load_data()
    print(f"Geladen: {len(df)} Spiele ({df['date'].min().date()} bis {df['date'].max().date()})\n")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    print(f"Verwendete Features ({len(feature_cols)}): {feature_cols}\n")

    train_df, test_df = chronological_split(df)
    print(f"Training: {len(train_df)} Spiele (bis {train_df['date'].max().date()})")
    print(f"Test:     {len(test_df)} Spiele (ab {test_df['date'].min().date()})\n")

    X_train = train_df[feature_cols]
    X_test = test_df[feature_cols]
    y_train = train_df[["goals_a", "goals_b"]]
    y_test = test_df[["goals_a", "goals_b"]]

    # Gleiche Median-Imputation wie beim Klassifikationsmodell (nur aus
    # Trainingsdaten berechnet, um Data Leakage zu vermeiden)
    imputer = SimpleImputer(strategy="median")
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    # RandomForestRegressor unterstützt Multi-Output nativ (goals_a + goals_b
    # in einem Modell statt zwei separaten)
    model = RandomForestRegressor(
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
    for i, target in enumerate(["goals_a", "goals_b"]):
        mae = mean_absolute_error(y_test[target], y_pred[:, i])
        rmse = np.sqrt(mean_squared_error(y_test[target], y_pred[:, i]))
        print(f"  {target}: MAE={mae:.3f} Tore, RMSE={rmse:.3f} Tore")

    # Aus den vorhergesagten Toren abgeleitetes Ergebnis - nur als Cross-Check
    # gegen das Klassifikationsmodell, NICHT als Ersatz für die Dashboard-
    # Siegwahrscheinlichkeit (die bleibt beim Klassifikationsmodell)
    predicted_result = np.where(
        y_pred[:, 0] > y_pred[:, 1] + 0.5, "A",
        np.where(y_pred[:, 1] > y_pred[:, 0] + 0.5, "B", "Draw"),
    )
    actual_result = test_df["result"].values
    accuracy_from_goals = (predicted_result == actual_result).mean()
    print(f"\n  Abgeleitete Ergebnis-Accuracy (aus Toren, Toleranz 0.5): {accuracy_from_goals:.3f}")
    print("  (Reiner Vergleichswert - fürs Dashboard weiterhin train_model.py für Sieg-Wahrscheinlichkeit nutzen)")

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
    (MODELS_DIR / "goals_feature_columns.json").write_text(
        json.dumps(feature_cols, indent=2), encoding="utf-8"
    )

    print(f"\nModell gespeichert in: {MODELS_DIR}")


if __name__ == "__main__":
    main()
