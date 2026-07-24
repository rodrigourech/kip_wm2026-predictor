import json
from pathlib import Path

import pandas as pd
import pytest

from build_features import compute_rolling_features
from monte_carlo_simulation import build_row


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_CSV = PROJECT_ROOT / "data" / "processed" / "match_features.csv"
FEATURE_COLUMNS_JSON = PROJECT_ROOT / "models" / "feature_columns.json"


def test_ranking_difference_is_calculated_correctly():
    histories = {"Team A": [], "Team B": []}
    static_feat = {
        "Team A": {"feat": {"form_points": 2.0}, "ranking": 1850.0},
        "Team B": {"feat": {"form_points": 1.5}, "ranking": 1725.0},
    }

    row = build_row("Team A", "Team B", histories, static_feat)

    assert row["ranking_diff"] == pytest.approx(125.0)


def test_rolling_features_use_only_previous_matches():
    history = [
        {"date": "2026-01-01", "points": 3, "goals_for": 2, "goals_against": 0},
        {"date": "2026-02-01", "points": 0, "goals_for": 0, "goals_against": 1},
        {"date": "2026-03-01", "points": 1, "goals_for": 1, "goals_against": 1},
    ]

    before_second = compute_rolling_features(history, "2026-02-01")
    before_third = compute_rolling_features(history, "2026-03-01")

    assert before_second["form_games_count"] == 1
    assert before_second["form_points"] == pytest.approx(3.0)
    assert before_third["form_games_count"] == 2

    history_with_future_change = history + [
        {"date": "2026-04-01", "points": 3, "goals_for": 9, "goals_against": 0}
    ]
    unchanged = compute_rolling_features(history_with_future_change, "2026-03-01")

    assert unchanged == before_third


def test_target_columns_are_not_model_features():
    feature_columns = json.loads(FEATURE_COLUMNS_JSON.read_text(encoding="utf-8"))
    target_columns = {"result", "goals_a", "goals_b", "winner"}

    assert target_columns.isdisjoint(feature_columns)


def test_all_expected_model_features_exist_in_processed_data():
    feature_columns = json.loads(FEATURE_COLUMNS_JSON.read_text(encoding="utf-8"))
    df = pd.read_csv(FEATURES_CSV, nrows=5)

    missing = sorted(set(feature_columns) - set(df.columns))
    assert not missing, f"Fehlende Modellfeatures: {missing}"
