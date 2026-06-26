from availability import availability_feature_set, team_availability_snapshot


def test_availability_feature_set_defaults_to_neutral_when_missing():
    features = availability_feature_set({})

    assert features["lineup_strength_diff"] == 0.0
    assert features["starter_availability_rate_diff"] == 0.0
    assert features["rotation_risk_diff"] == 0.0
    assert features["b_team_risk_diff"] == 0.0
    assert features["key_absence_impact_diff"] == 0


def test_availability_feature_set_captures_lineup_and_absence_context():
    match = {
        "availability": {
            "home": {
                "lineup_status": "projected",
                "lineup_confidence": 0.55,
                "normal_starter_count": 11,
                "expected_starters_available": 8,
                "lineup_strength_rating": 76,
                "rotation_risk": 8,
                "b_team_risk": 7,
                "replacement_quality_rating": 5,
                "key_absences": [
                    {"name": "Starter A", "impact_rating": 8},
                    {"name": "Starter B", "impact_rating": 6},
                ],
                "returning_players": [
                    {
                        "name": "Returning A",
                        "impact_rating": 7,
                        "days_since_return": 6,
                        "games_since_return": 1,
                        "minutes_restriction": True,
                    }
                ],
            },
            "away": {
                "lineup_status": "confirmed",
                "lineup_confidence": 0.95,
                "normal_starter_count": 11,
                "expected_starters_available": 11,
                "lineup_strength_rating": 94,
                "rotation_risk": 1,
                "b_team_risk": 0,
                "replacement_quality_rating": 8,
                "key_absences": [],
                "returning_players": [],
            },
        }
    }

    features = availability_feature_set(match)

    assert features["lineup_strength_diff"] == -18
    assert round(features["starter_availability_rate_diff"], 4) == round((8 / 11) - 1, 4)
    assert features["rotation_risk_diff"] == 7
    assert features["b_team_risk_diff"] == 7
    assert features["key_absence_count_diff"] == 2
    assert features["key_absence_impact_diff"] == 14
    assert features["recent_returning_player_count_diff"] == 1
    assert features["minutes_restricted_count_diff"] == 1


def test_team_availability_snapshot_calculates_returning_player_risk():
    snapshot = team_availability_snapshot({
        "returning_players": [
            {
                "impact_rating": 8,
                "days_since_return": 4,
                "games_since_return": 1,
                "minutes_restriction": True,
            }
        ]
    })

    assert snapshot["returning_player_count"] == 1
    assert snapshot["recent_returning_player_count"] == 1
    assert snapshot["minutes_restricted_count"] == 1
    assert snapshot["returning_player_risk"] > 0
