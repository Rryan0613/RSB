from data_quality import (
    apply_recommendation_guardrail,
    assess_data_quality,
    summarize_data_quality,
)


def make_match(feature_source=None, match_id="2026-06-26_canada_france"):
    match = {
        "match_id": match_id,
        "date": "2026-06-26",
        "home_team": "Canada",
        "away_team": "France",
        "home": {
            "fifa_rank": 27,
            "elo": 1740,
            "xg_for_l5": 1.5,
            "xg_against_l5": 1.2,
            "shots_l5": 12.0,
            "sog_l5": 4.3,
            "big_chances_l5": 2.0,
            "possession_l5": 51,
            "pass_completion_l5": 81,
            "ppda_l5": 10.2,
            "rest_days": 5,
            "injuries": 1,
            "suspensions": 0,
            "missing_starters": 1,
            "motivation": 8,
            "tournament_experience": 5,
            "squad_value_millions": 250,
        },
        "away": {
            "fifa_rank": 2,
            "elo": 1980,
            "xg_for_l5": 2.1,
            "xg_against_l5": 0.8,
            "shots_l5": 15.6,
            "sog_l5": 6.1,
            "big_chances_l5": 3.1,
            "possession_l5": 58,
            "pass_completion_l5": 87,
            "ppda_l5": 7.8,
            "rest_days": 5,
            "injuries": 1,
            "suspensions": 0,
            "missing_starters": 0,
            "motivation": 9,
            "tournament_experience": 9,
            "squad_value_millions": 1050,
        },
        "odds": {"home_win": 230},
    }
    if feature_source:
        match["data_quality"] = {"feature_source": feature_source}
    return match


def make_provider_choice():
    return {
        "source": "provider_qualified",
        "decision": {
            "sportsbook_count": 3,
        },
        "line": {
            "raw_json": {
                "last_update": "2026-06-26T15:39:30Z",
            },
            "captured_at": "2026-06-26T15:40:08+00:00",
        },
    }


def warning_codes(assessment):
    return {warning["code"] for warning in assessment["warnings"]}


def test_bootstrap_and_manual_features_block_actionable_prediction():
    assessment = assess_data_quality(
        match=make_match(),
        model_status="simulation_only_bootstrap",
        trained_count=0,
        min_train=20,
        odds_choice=make_provider_choice(),
    )

    assert assessment["data_quality"] == "weak"
    assert assessment["actionable"] is False
    assert assessment["recommendation_guardrail"] == "blocked"
    assert assessment["do_not_bet_real_money"] is True
    assert "simulation_only_bootstrap" in warning_codes(assessment)
    assert "manual_feature_inputs" in warning_codes(assessment)
    assert "do_not_bet_real_money" in warning_codes(assessment)


def test_verified_trained_provider_prediction_can_be_actionable():
    assessment = assess_data_quality(
        match=make_match(feature_source="verified_dataset"),
        model_status="existing_model",
        trained_count=25,
        min_train=20,
        odds_choice=make_provider_choice(),
    )

    assert assessment["data_quality"] == "strong"
    assert assessment["actionable"] is True
    assert assessment["recommendation_guardrail"] == "clear"
    assert assessment["warnings"] == []


def test_manual_odds_fallback_blocks_actionable_prediction():
    assessment = assess_data_quality(
        match=make_match(feature_source="verified_dataset"),
        model_status="existing_model",
        trained_count=25,
        min_train=20,
        odds_choice={"source": "manual_fallback", "line": {}},
    )

    assert assessment["actionable"] is False
    assert "manual_odds_fallback_used" in warning_codes(assessment)


def test_missing_feature_fields_block_actionable_prediction():
    match = make_match(feature_source="verified_dataset")
    match["home"].pop("elo")

    assessment = assess_data_quality(
        match=match,
        model_status="existing_model",
        trained_count=25,
        min_train=20,
        odds_choice=make_provider_choice(),
    )

    assert assessment["actionable"] is False
    assert "missing_feature_fields" in warning_codes(assessment)


def test_stale_odds_block_actionable_prediction():
    stale_choice = make_provider_choice()
    stale_choice["line"]["captured_at"] = "2026-06-26T16:30:08+00:00"

    assessment = assess_data_quality(
        match=make_match(feature_source="verified_dataset"),
        model_status="existing_model",
        trained_count=25,
        min_train=20,
        odds_choice=stale_choice,
        max_odds_age_minutes=15,
    )

    assert assessment["actionable"] is False
    assert "stale_odds" in warning_codes(assessment)


def test_guardrail_converts_bet_to_pass_when_blocked():
    assessment = assess_data_quality(
        match=make_match(),
        model_status="simulation_only_bootstrap",
        trained_count=0,
        min_train=20,
        odds_choice=make_provider_choice(),
    )

    assert apply_recommendation_guardrail("bet", assessment) == "pass"
    assert apply_recommendation_guardrail("pass", assessment) == "pass"


def test_summarize_data_quality_counts_warnings():
    predictions = [
        {
            "data_quality": "weak",
            "actionable": False,
            "recommendation_guardrail": "blocked",
            "quality_warnings": [
                {"code": "simulation_only_bootstrap", "severity": "blocker"},
                {"code": "do_not_bet_real_money", "severity": "blocker"},
            ],
        },
        {
            "data_quality": "strong",
            "actionable": True,
            "recommendation_guardrail": "clear",
            "quality_warnings": [],
        },
    ]

    summary = summarize_data_quality(predictions)

    assert summary["overall_data_quality"] == "weak"
    assert summary["prediction_count"] == 2
    assert summary["actionable_predictions"] == 1
    assert summary["blocked_predictions"] == 1
    assert summary["do_not_bet_real_money"] is True
    assert summary["warning_counts_by_code"]["simulation_only_bootstrap"] == 1
