import pytest

from features import make_features


def test_make_features_contains_expected_keys():
    match = {
        "match_id": "test_match",
        "date": "2026-06-26",
        "home_team": "Alpha FC",
        "away_team": "Beta FC",
        "neutral_site": True,
        "home": {"elo": 1845, "rest_days": 5, "missing_starters": 0, "xg_for_l5": 1.8, "xg_against_l5": 1.1},
        "away": {"elo": 1710, "rest_days": 4, "missing_starters": 2, "xg_for_l5": 1.2, "xg_against_l5": 1.6},
        "odds": {"home_win": -120}
    }

    features = make_features(match)

    assert "elo_diff" in features
    assert "rest_days_diff" in features
    assert "missing_starters_diff" in features
    assert "home_attack_vs_away_defense" in features
    assert "away_attack_vs_home_defense" in features
    assert "neutral_site" in features
    assert "lineup_strength_diff" in features
    assert "starter_availability_rate_diff" in features
    assert "b_team_risk_diff" in features
    assert "key_absence_impact_diff" in features
    assert "home_press_vs_away_buildup" in features
    assert "away_pace_vs_home_high_line" in features
    assert "home_set_piece_edge" in features
    assert "midfield_control_diff" in features


def test_make_features_uses_team_metric_differences():
    match = {
        "match_id": "test_match",
        "date": "2026-06-26",
        "home_team": "Alpha FC",
        "away_team": "Beta FC",
        "neutral_site": True,
        "home": {"elo": 1845, "rest_days": 5, "missing_starters": 0},
        "away": {"elo": 1710, "rest_days": 4, "missing_starters": 2},
        "odds": {"home_win": -120}
    }

    features = make_features(match)

    assert features["elo_diff"] == 135
    assert features["rest_days_diff"] == 1
    assert features["missing_starters_diff"] == -2
    assert features["neutral_site"] == 1


def test_make_features_uses_availability_context():
    match = {
        "match_id": "test_match",
        "date": "2026-06-26",
        "home_team": "Alpha FC",
        "away_team": "Beta FC",
        "neutral_site": True,
        "home": {"elo": 1845},
        "away": {"elo": 1710},
        "availability": {
            "home": {
                "lineup_strength_rating": 80,
                "expected_starters_available": 9,
                "normal_starter_count": 11,
                "rotation_risk": 7,
                "b_team_risk": 6,
                "key_absences": [{"name": "Player A", "impact_rating": 8}],
            },
            "away": {
                "lineup_strength_rating": 95,
                "expected_starters_available": 11,
                "normal_starter_count": 11,
                "rotation_risk": 1,
                "b_team_risk": 0,
                "key_absences": [],
            },
        },
        "odds": {"home_win": -120},
    }

    features = make_features(match)

    assert features["lineup_strength_diff"] == -15
    assert round(features["starter_availability_rate_diff"], 4) == round((9 / 11) - 1, 4)
    assert features["rotation_risk_diff"] == 6
    assert features["b_team_risk_diff"] == 6
    assert features["key_absence_impact_diff"] == 8


def test_make_features_uses_tactical_matchup_context():
    match = {
        "match_id": "test_match",
        "date": "2026-06-26",
        "home_team": "Alpha FC",
        "away_team": "Beta FC",
        "neutral_site": True,
        "home": {"elo": 1845},
        "away": {"elo": 1710},
        "tactical": {
            "home": {
                "tactical_confidence": 0.9,
                "pressing_intensity": 8,
                "build_up_quality": 6,
                "vulnerability_to_press": 3,
                "press_resistance": 6,
                "pace_threat": 9,
                "defensive_line_height": 7,
                "set_piece_attack": 8,
                "set_piece_defense": 6,
                "transition_defense": 5,
                "midfield_control": 6,
            },
            "away": {
                "tactical_confidence": 0.8,
                "pressing_intensity": 5,
                "build_up_quality": 8,
                "vulnerability_to_press": 5,
                "press_resistance": 5,
                "pace_threat": 6,
                "defensive_line_height": 9,
                "set_piece_attack": 5,
                "set_piece_defense": 4,
                "transition_defense": 4,
                "midfield_control": 8,
            },
        },
        "odds": {"home_win": -120},
    }

    features = make_features(match)

    assert features["tactical_confidence_min"] == 0.8
    assert features["home_pace_vs_away_high_line"] == 14
    assert features["home_set_piece_edge"] == 4
    assert features["midfield_control_diff"] == -2


# ---------------------------------------------------------------------------
# v0.1.9.1 derived ratio features
# ---------------------------------------------------------------------------

_BASE_MATCH = {
    "match_id": "test_match",
    "date": "2026-06-26",
    "home_team": "Alpha FC",
    "away_team": "Beta FC",
    "neutral_site": True,
    "home": {
        "elo": 1845,
        "xg_for_l5": 1.8,
        "xg_against_l5": 1.1,
        "shots_l5": 14.0,
        "sog_l5": 5.4,
        "big_chances_l5": 2.8,
        "ppda_l5": 8.7,
    },
    "away": {
        "elo": 1710,
        "xg_for_l5": 1.2,
        "xg_against_l5": 1.6,
        "shots_l5": 10.2,
        "sog_l5": 3.7,
        "big_chances_l5": 1.7,
        "ppda_l5": 11.2,
    },
    "odds": {"home_win": -120},
}


def test_make_features_contains_new_derived_keys():
    features = make_features(_BASE_MATCH)
    assert "sot_accuracy_diff" in features
    assert "xg_per_shot_diff" in features
    assert "pressing_efficiency_diff" in features
    assert "big_chance_rate_diff" in features


def test_sot_accuracy_diff_value():
    features = make_features(_BASE_MATCH)
    assert features["sot_accuracy_diff"] == pytest.approx(5.4 / 14.0 - 3.7 / 10.2, rel=1e-5)


def test_xg_per_shot_diff_value():
    features = make_features(_BASE_MATCH)
    assert features["xg_per_shot_diff"] == pytest.approx(1.8 / 14.0 - 1.2 / 10.2, rel=1e-5)


def test_pressing_efficiency_diff_value():
    features = make_features(_BASE_MATCH)
    assert features["pressing_efficiency_diff"] == pytest.approx(1.0 / 8.7 - 1.0 / 11.2, rel=1e-5)


def test_big_chance_rate_diff_value():
    features = make_features(_BASE_MATCH)
    assert features["big_chance_rate_diff"] == pytest.approx(2.8 / 14.0 - 1.7 / 10.2, rel=1e-5)


def test_shot_based_features_zero_shots_no_error():
    match = {
        **_BASE_MATCH,
        "home": {**_BASE_MATCH["home"], "shots_l5": 0},
        "away": {**_BASE_MATCH["away"], "shots_l5": 0},
    }
    features = make_features(match)
    assert "sot_accuracy_diff" in features
    assert "xg_per_shot_diff" in features
    assert "big_chance_rate_diff" in features


def test_pressing_efficiency_diff_zero_ppda_no_error():
    match = {
        **_BASE_MATCH,
        "home": {**_BASE_MATCH["home"], "ppda_l5": 0},
        "away": {**_BASE_MATCH["away"], "ppda_l5": 0},
    }
    features = make_features(match)
    assert "pressing_efficiency_diff" in features
