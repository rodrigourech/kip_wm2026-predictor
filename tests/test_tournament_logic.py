import itertools
import json
import random
from pathlib import Path

import pytest

import monte_carlo_simulation as sim


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANNEX_C_JSON = PROJECT_ROOT / "data" / "raw" / "annex_c.json"


def test_group_structure_contains_12_groups_and_48_unique_teams():
    groups = sim.load_groups()

    assert set(groups) == set("ABCDEFGHIJKL")
    assert all(len(teams) == 4 for teams in groups.values())

    all_teams = [team for teams in groups.values() for team in teams]
    assert len(all_teams) == 48
    assert len(set(all_teams)) == 48


def test_four_teams_create_six_unique_group_matches():
    teams = ["A", "B", "C", "D"]
    matches = list(itertools.combinations(teams, 2))

    assert len(matches) == 6
    assert all(a != b for a, b in matches)
    assert len({frozenset(match) for match in matches}) == 6


def test_annex_c_has_495_unique_combinations():
    data = json.loads(ANNEX_C_JSON.read_text(encoding="utf-8"))
    rows = data["rows"]
    combinations = [row["qualified_groups"] for row in rows]

    assert len(rows) == 495
    assert len(set(combinations)) == 495


def test_annex_c_assigns_each_qualified_third_place_once():
    data = json.loads(ANNEX_C_JSON.read_text(encoding="utf-8"))
    expected_slots = set(sim.THIRD_PLACE_SLOTS)

    for row in data["rows"]:
        qualified = row["qualified_groups"]
        assigned = [row[slot] for slot in sim.THIRD_PLACE_SLOTS]

        assert len(qualified) == 8
        assert len(set(qualified)) == 8
        assert set(qualified).issubset(set("ABCDEFGHIJKL"))
        assert expected_slots.issubset(row.keys())
        assert all(value.startswith("3") and len(value) == 2 for value in assigned)
        assert {value[1] for value in assigned} == set(qualified)


def test_knockout_winners_follow_official_fifa_match_schedule():
    expected_bracket = {
        89: (74, 77),
        90: (73, 75),
        91: (76, 78),
        92: (79, 80),
        93: (83, 84),
        94: (81, 82),
        95: (86, 88),
        96: (85, 87),
        97: (89, 90),
        98: (93, 94),
        99: (91, 92),
        100: (95, 96),
        101: (97, 98),
        102: (99, 100),
        104: (101, 102),
    }

    assert sim.KNOCKOUT_BRACKET == expected_bracket

    r32_winners = {match: f"winner_{match}" for match in range(73, 89)}
    round_of_16 = sim.build_knockout_round_matches(r32_winners, range(89, 97))

    assert round_of_16[89] == ("winner_74", "winner_77")
    assert round_of_16[90] == ("winner_73", "winner_75")
    assert round_of_16[96] == ("winner_85", "winner_87")


def test_complete_tournament_ends_with_exactly_one_champion(monkeypatch):
    groups = sim.load_groups()
    annex_c = sim.load_annex_c()
    all_teams = {team for teams in groups.values() for team in teams}

    def deterministic_prediction(team_a, team_b, cache, models, histories, static_feat):
        return {
            "proba": {"A": 1.0, "Draw": 0.0, "B": 0.0},
            "goals_a": 2.0,
            "goals_b": 0.0,
        }

    monkeypatch.setattr(sim, "get_match_prediction", deterministic_prediction)

    static_feat = {
        team: {"feat": {"form_points": 1.0}, "ranking": 1500.0}
        for team in all_teams
    }
    histories = {team: [] for team in all_teams}

    result = sim.simulate_tournament(
        groups=groups,
        annex_c_by_combo=annex_c,
        cache={},
        models=(),
        histories=histories,
        static_feat=static_feat,
        rng=random.Random(42),
    )

    assert result["champion"] in all_teams
    assert isinstance(result["champion"], str)
    assert len(result["knockout_details"]["final"]) == 1
    assert result["knockout_details"]["final"][0][4] == result["champion"]
