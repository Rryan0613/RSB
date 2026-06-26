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
