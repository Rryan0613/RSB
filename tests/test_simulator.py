from simulator import estimate_goal_rates, run_monte_carlo


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


def test_availability_context_changes_goal_rates():
    base_home, base_away = estimate_goal_rates(sample_match())
    match = sample_match()
    match["availability"] = {
        "home": {
            "lineup_strength_rating": 95,
            "expected_starters_available": 11,
            "normal_starter_count": 11,
            "rotation_risk": 0,
            "b_team_risk": 0,
            "key_absences": [],
            "returning_players": [],
        },
        "away": {
            "lineup_strength_rating": 72,
            "expected_starters_available": 8,
            "normal_starter_count": 11,
            "rotation_risk": 8,
            "b_team_risk": 7,
            "key_absences": [{"impact_rating": 8}],
            "returning_players": [{"impact_rating": 7, "minutes_restriction": True, "games_since_return": 1}],
        },
    }

    adjusted_home, adjusted_away = estimate_goal_rates(match)

    assert adjusted_home > base_home
    assert adjusted_away < base_away


def test_tactical_context_changes_goal_rates():
    base_home, base_away = estimate_goal_rates(sample_match())
    match = sample_match()
    match["tactical"] = {
        "home": {
            "pressing_intensity": 9,
            "pace_threat": 9,
            "set_piece_attack": 9,
            "counterattack_threat": 9,
            "midfield_control": 8,
            "manager_tactical_rating": 8,
        },
        "away": {
            "build_up_quality": 4,
            "press_resistance": 3,
            "vulnerability_to_press": 8,
            "defensive_line_height": 9,
            "transition_defense": 3,
            "set_piece_defense": 3,
            "midfield_control": 5,
            "manager_tactical_rating": 5,
        },
    }

    adjusted_home, adjusted_away = estimate_goal_rates(match)

    assert adjusted_home > base_home
    assert adjusted_away < base_away


def test_monte_carlo_output_includes_goal_rate_adjustments():
    result = run_monte_carlo(sample_match(), simulations=500, seed=7)

    assert "goal_rate_adjustments" in result
    assert "total_home_goal_adjustment" in result
