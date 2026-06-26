from tactical_matchup import tactical_feature_set, tactical_review_flags, tactical_snapshot


def test_tactical_feature_set_defaults_to_neutral_when_missing():
    features = tactical_feature_set({})

    assert features["tactical_confidence_min"] == 0.0
    assert features["pressing_intensity_diff"] == 0.0
    assert features["midfield_control_diff"] == 0.0
    assert features["home_set_piece_edge"] == 0.0
    assert features["away_set_piece_edge"] == 0.0


def test_tactical_feature_set_captures_matchup_edges():
    match = {
        "tactical": {
            "home": {
                "tactical_confidence": 0.9,
                "pressing_intensity": 8,
                "build_up_quality": 6,
                "vulnerability_to_press": 3,
                "press_resistance": 6,
                "defensive_line_height": 8,
                "pace_threat": 9,
                "crossing_volume": 7,
                "aerial_threat": 8,
                "aerial_defense": 6,
                "set_piece_attack": 8,
                "set_piece_defense": 6,
                "counterattack_threat": 9,
                "transition_defense": 5,
                "midfield_control": 6,
                "formation_flexibility": 7,
                "manager_tactical_rating": 7,
                "low_block_comfort": 5,
                "chance_creation_centrality": 6,
                "wide_creation": 8,
            },
            "away": {
                "tactical_confidence": 0.8,
                "pressing_intensity": 5,
                "build_up_quality": 8,
                "vulnerability_to_press": 5,
                "press_resistance": 5,
                "defensive_line_height": 9,
                "pace_threat": 6,
                "crossing_volume": 4,
                "aerial_threat": 4,
                "aerial_defense": 5,
                "set_piece_attack": 5,
                "set_piece_defense": 4,
                "counterattack_threat": 6,
                "transition_defense": 4,
                "midfield_control": 8,
                "formation_flexibility": 8,
                "manager_tactical_rating": 9,
                "low_block_comfort": 7,
                "chance_creation_centrality": 8,
                "wide_creation": 4,
            },
        }
    }

    features = tactical_feature_set(match)

    assert features["tactical_confidence_min"] == 0.8
    assert features["pressing_intensity_diff"] == 3
    assert features["home_pace_vs_away_high_line"] == 14
    assert features["home_crossing_vs_away_aerial_defense"] == 2.5
    assert features["home_set_piece_edge"] == 4
    assert features["midfield_control_diff"] == -2
    assert features["manager_tactical_diff"] == -2


def test_tactical_review_flags_identify_major_mismatch_edges():
    match = {
        "tactical": {
            "home": {
                "pressing_intensity": 9,
                "pace_threat": 9,
                "set_piece_attack": 8,
                "build_up_quality": 7,
                "press_resistance": 7,
            },
            "away": {
                "defensive_line_height": 9,
                "transition_defense": 3,
                "build_up_quality": 4,
                "vulnerability_to_press": 7,
                "press_resistance": 3,
                "set_piece_defense": 4,
            },
        }
    }

    flags = tactical_review_flags(match)

    assert "home_pace_vs_away_high_line" in flags
    assert "home_press_vs_away_buildup" in flags
    assert "home_set_piece_edge" in flags


def test_tactical_snapshot_clamps_ratings():
    snapshot = tactical_snapshot({
        "tactical_confidence": 2,
        "pressing_intensity": 99,
        "build_up_quality": -4,
    })

    assert snapshot["tactical_confidence"] == 1.0
    assert snapshot["pressing_intensity"] == 10.0
    assert snapshot["build_up_quality"] == 0.0
