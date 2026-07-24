import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
import sklearn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"
FEATURES_CSV = PROJECT_ROOT / "data" / "processed" / "match_features.csv"


def test_classifier_returns_valid_three_class_probabilities():
    if sklearn.__version__ != "1.5.2":
        pytest.skip(
            f"Modellartefakte wurden mit scikit-learn 1.5.2 gespeichert; installiert ist {sklearn.__version__}."
        )

    model = joblib.load(MODELS_DIR / "random_forest_model.pkl")
    imputer = joblib.load(MODELS_DIR / "imputer.pkl")
    feature_columns = json.loads(
        (MODELS_DIR / "feature_columns.json").read_text(encoding="utf-8")
    )

    sample = (
        pd.read_csv(FEATURES_CSV)
        .sort_values(["date", "fixture_id"])
        .head(10)
    )
    probabilities = model.predict_proba(imputer.transform(sample[feature_columns]))

    assert probabilities.shape == (len(sample), 3)
    assert set(model.classes_) == {"A", "Draw", "B"}
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()
    assert np.allclose(probabilities.sum(axis=1), 1.0)
