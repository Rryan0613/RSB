from simulator import run_monte_carlo


def sample_match():
    return {
        "match_id": "test_match",
        "date": "2026-06-26",
        "home_team": "Alpha FC",
        "away_team": "Beta FC",
        "neutral_site": True,
        "home": {"xg_for_l5": 1.8, "xg_against_l5": 1.1, "rest_days": 5, "missing_starters": 0},
        "away": {"xg_for_l5": 1.2, "xg_against_l5": 1.6, "rest_days": 4, "missing_starters": 2},
        "odds": {"home_win": -120}
    }


def test_monte_carlo_reproducible_with_fixed_seed():
    first = run_monte_carlo(sample_match(), simulations=500, seed=42)
    second = run_monte_carlo(sample_match(), simulations=500, seed=42)

    assert first == second
    assert first["seed_used"] == 42


def test_monte_carlo_probability_outputs_are_in_range():
    result = run_monte_carlo(sample_match(), simulations=500, seed=1)

    for key in ["home_win_probability", "draw_probability", "away_win_probability", "btts_probability", "over_25_probability"]:
        assert 0 <= result[key] <= 1
