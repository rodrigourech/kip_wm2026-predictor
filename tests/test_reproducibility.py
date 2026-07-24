import random

import monte_carlo_simulation as sim


def test_same_seed_produces_same_simulated_match(monkeypatch):
    def fixed_prediction(team_a, team_b, cache, models, histories, static_feat):
        return {
            "proba": {"A": 0.45, "Draw": 0.25, "B": 0.30},
            "goals_a": 1.7,
            "goals_b": 1.1,
        }

    monkeypatch.setattr(sim, "get_match_prediction", fixed_prediction)

    args = ("Team A", "Team B", {}, (), {}, {})
    result_1 = sim.simulate_group_match(*args, rng=random.Random(1234))
    result_2 = sim.simulate_group_match(*args, rng=random.Random(1234))

    assert result_1 == result_2
