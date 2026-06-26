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
