from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from availability import (
    availability_source,
    b_team_risk,
    fitness_concerns,
    has_team_availability,
    high_impact_absence_count,
    is_verified_availability_source,
    key_absences,
    lineup_confidence,
    lineup_status,
    minutes_restricted_count,
    recent_returning_player_count,
    returning_players,
    rotation_risk,
    team_availability,
)
from tactical_matchup import (
    confidence as tactical_confidence,
    has_team_tactical,
    is_verified_tactical_source,
    tactical_review_flags,
    tactical_source,
    team_tactical,
)

FEATURE_FIELDS = [
    "fifa_rank",
    "elo",
    "xg_for_l5",
    "xg_against_l5",
    "shots_l5",
    "sog_l5",
    "big_chances_l5",
    "possession_l5",
    "pass_completion_l5",
    "ppda_l5",
    "rest_days",
    "injuries",
    "suspensions",
    "missing_starters",
    "motivation",
    "tournament_experience",
    "squad_value_millions",
]

TRUSTED_FEATURE_SOURCES = {
    "official_feed",
    "verified_dataset",
    "historical_backfill",
    "model_feature_store",
}

ACTION_BLOCK_CODES = {
    "simulation_only_bootstrap",
    "insufficient_training_data",
    "placeholder_features",
    "manual_feature_inputs",
    "missing_feature_fields",
    "provider_odds_missing",
    "manual_odds_used",
    "manual_odds_fallback_used",
    "stale_odds",
    "availability_data_missing",
    "injury_data_unverified",
    "lineup_unconfirmed",
    "low_lineup_confidence",
    "b_team_rotation_risk",
    "key_player_absence",
    "recent_injury_return",
    "minutes_restriction",
    "tactical_data_missing",
    "tactical_data_unverified",
    "low_tactical_confidence",
}

PLACEHOLDER_TERMS = {
    "alpha",
    "beta",
    "sample",
    "test",
    "placeholder",
    "mock",
}


def make_warning(code: str, severity: str, message: str) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
    }


def _data_quality_meta(match: dict) -> dict:
    meta = match.get("data_quality") or {}
    return meta if isinstance(meta, dict) else {}


def _feature_source(match: dict) -> Optional[str]:
    meta = _data_quality_meta(match)
    return meta.get("feature_source") or match.get("feature_source")


def _is_verified_feature_source(match: dict) -> bool:
    return _feature_source(match) in TRUSTED_FEATURE_SOURCES


def _contains_placeholder_term(value: str) -> bool:
    cleaned = str(value or "").lower().replace("_", " ").replace("-", " ")
    tokens = set(cleaned.split())
    return bool(tokens & PLACEHOLDER_TERMS)


def _is_placeholder_match(match: dict) -> bool:
    meta = _data_quality_meta(match)
    if meta.get("is_placeholder") is True:
        return True

    values = [
        match.get("match_id", ""),
        match.get("home_team", ""),
        match.get("away_team", ""),
    ]
    return any(_contains_placeholder_term(value) for value in values)


def _missing_feature_fields(match: dict) -> list:
    missing = []
    for team_key in ["home", "away"]:
        team_metrics = match.get(team_key) or {}
        for field in FEATURE_FIELDS:
            if field not in team_metrics:
                missing.append(f"{team_key}.{field}")
    return missing


def _parse_datetime(value: Optional[str]):
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _odds_last_update(line: dict) -> Optional[str]:
    raw = line.get("raw_json") or {}
    if isinstance(raw, dict):
        return raw.get("last_update")
    return None


def _is_stale_odds(line: dict, max_age_minutes: int) -> bool:
    last_update = _parse_datetime(_odds_last_update(line))
    captured_at = _parse_datetime(line.get("captured_at"))
    if not last_update or not captured_at:
        return False
    age_minutes = (captured_at - last_update).total_seconds() / 60
    return age_minutes > max_age_minutes


def _high_impact_key_absence_names(team_data: dict) -> list:
    names = []
    for absence in key_absences(team_data):
        if not isinstance(absence, dict):
            continue
        impact = absence.get("impact_rating", 0)
        try:
            impact_value = float(impact)
        except (TypeError, ValueError):
            impact_value = 0.0
        if impact_value >= 7:
            names.append(absence.get("name") or absence.get("role") or "unknown_player")
    return names


def _team_label(match: dict, team_key: str) -> str:
    return match.get(f"{team_key}_team") or team_key


def _assess_availability(match: dict) -> list:
    warnings = []
    missing_teams = [team_key for team_key in ["home", "away"] if not has_team_availability(match, team_key)]
    if missing_teams:
        warnings.append(make_warning(
            "availability_data_missing",
            "blocker",
            f"Missing availability context for: {', '.join(missing_teams)}.",
        ))
        return warnings

    for team_key in ["home", "away"]:
        team_data = team_availability(match, team_key)
        team_name = _team_label(match, team_key)
        source = availability_source(team_data, match)
        status = lineup_status(team_data)
        confidence = lineup_confidence(team_data)
        team_rotation_risk = rotation_risk(team_data)
        team_b_risk = b_team_risk(team_data)
        high_absence_names = _high_impact_key_absence_names(team_data)
        recent_returns = recent_returning_player_count(team_data)
        minutes_restricted = minutes_restricted_count(team_data)

        if not is_verified_availability_source(source):
            warnings.append(make_warning(
                "injury_data_unverified",
                "blocker",
                f"{team_name} availability source is {source}; injury/lineup data is not verified.",
            ))

        if status != "confirmed":
            warnings.append(make_warning(
                "lineup_unconfirmed",
                "blocker",
                f"{team_name} lineup status is {status}; confirmed XI is not available.",
            ))

        if confidence < 0.7:
            warnings.append(make_warning(
                "low_lineup_confidence",
                "blocker",
                f"{team_name} lineup confidence is {confidence:.2f}, below 0.70.",
            ))

        if team_rotation_risk >= 7 or team_b_risk >= 7:
            warnings.append(make_warning(
                "b_team_rotation_risk",
                "blocker",
                f"{team_name} has high rotation/B-team risk: rotation={team_rotation_risk:.1f}, b_team={team_b_risk:.1f}.",
            ))

        if high_impact_absence_count(team_data) > 0:
            warnings.append(make_warning(
                "key_player_absence",
                "blocker",
                f"{team_name} has high-impact key absences: {', '.join(high_absence_names)}.",
            ))

        if recent_returns > 0:
            warnings.append(make_warning(
                "recent_injury_return",
                "blocker",
                f"{team_name} has {recent_returns} recent injury return(s) requiring caution.",
            ))

        if minutes_restricted > 0:
            warnings.append(make_warning(
                "minutes_restriction",
                "blocker",
                f"{team_name} has {minutes_restricted} player(s) with minutes restrictions or fitness limits.",
            ))

        if fitness_concerns(team_data) and not recent_returns and not minutes_restricted:
            warnings.append(make_warning(
                "fitness_concerns_present",
                "warning",
                f"{team_name} has listed fitness concerns that should be reviewed.",
            ))

        if returning_players(team_data) and recent_returns == 0:
            warnings.append(make_warning(
                "returning_players_present",
                "warning",
                f"{team_name} has returning players listed; review role and minutes context.",
            ))

    return warnings


def _assess_tactical(match: dict) -> list:
    warnings = []
    missing_teams = [team_key for team_key in ["home", "away"] if not has_team_tactical(match, team_key)]
    if missing_teams:
        warnings.append(make_warning(
            "tactical_data_missing",
            "blocker",
            f"Missing tactical matchup context for: {', '.join(missing_teams)}.",
        ))
        return warnings

    for team_key in ["home", "away"]:
        team_data = team_tactical(match, team_key)
        team_name = _team_label(match, team_key)
        source = tactical_source(team_data, match)
        confidence = tactical_confidence(team_data)

        if not is_verified_tactical_source(source):
            warnings.append(make_warning(
                "tactical_data_unverified",
                "blocker",
                f"{team_name} tactical source is {source}; matchup data is not verified.",
            ))

        if confidence < 0.65:
            warnings.append(make_warning(
                "low_tactical_confidence",
                "blocker",
                f"{team_name} tactical confidence is {confidence:.2f}, below 0.65.",
            ))

    flags = tactical_review_flags(match)
    if flags:
        warnings.append(make_warning(
            "tactical_mismatch_review_required",
            "warning",
            f"Potential tactical mismatch flags require review: {', '.join(flags)}.",
        ))

    return warnings


def assess_data_quality(
    match: dict,
    model_status: str,
    trained_count: int,
    min_train: int,
    odds_choice: Optional[dict] = None,
    provider_context: Optional[dict] = None,
    max_odds_age_minutes: int = 15,
) -> dict:
    warnings = []

    if model_status == "simulation_only_bootstrap":
        warnings.append(make_warning(
            "simulation_only_bootstrap",
            "blocker",
            "Model is using simulation-only bootstrap because no trained model is available yet.",
        ))

    if trained_count < min_train:
        warnings.append(make_warning(
            "insufficient_training_data",
            "blocker",
            f"Only {trained_count} completed matches are available; minimum required is {min_train}.",
        ))

    if _is_placeholder_match(match):
        warnings.append(make_warning(
            "placeholder_features",
            "blocker",
            "Match appears to contain sample, test, mock, or placeholder identifiers.",
        ))

    feature_source = _feature_source(match)
    if not _is_verified_feature_source(match):
        label = feature_source or "unspecified"
        warnings.append(make_warning(
            "manual_feature_inputs",
            "blocker",
            f"Feature source is {label}; values are not marked as verified data.",
        ))

    missing_fields = _missing_feature_fields(match)
    if missing_fields:
        warnings.append(make_warning(
            "missing_feature_fields",
            "blocker",
            f"Missing feature fields: {', '.join(missing_fields)}.",
        ))

    warnings.extend(_assess_availability(match))
    warnings.extend(_assess_tactical(match))

    if odds_choice:
        source = odds_choice.get("source")
        if source == "manual":
            warnings.append(make_warning(
                "manual_odds_used",
                "blocker",
                "Prediction used manual slate odds instead of qualified provider odds.",
            ))
        elif source == "manual_fallback":
            warnings.append(make_warning(
                "manual_odds_fallback_used",
                "blocker",
                "Provider odds were requested but manual slate odds were used as fallback.",
            ))
        elif source == "provider_qualified":
            decision = odds_choice.get("decision") or {}
            sportsbook_count = decision.get("sportsbook_count")
            if sportsbook_count is not None and sportsbook_count < 3:
                warnings.append(make_warning(
                    "low_sportsbook_coverage",
                    "warning",
                    f"Qualified price was based on only {sportsbook_count} sportsbook(s).",
                ))

            line = odds_choice.get("line") or {}
            if _is_stale_odds(line, max_age_minutes=max_odds_age_minutes):
                warnings.append(make_warning(
                    "stale_odds",
                    "blocker",
                    f"Provider odds last update is older than {max_odds_age_minutes} minutes.",
                ))
    elif provider_context:
        warnings.append(make_warning(
            "provider_odds_missing",
            "blocker",
            "Provider odds were requested but no odds choice was resolved for this match.",
        ))

    provider_summary = (provider_context or {}).get("summary") or {}
    bookmaker_summary = provider_summary.get("bookmaker_summary") or {}
    missing_books = bookmaker_summary.get("missing_expected_bookmakers") or []
    if missing_books:
        warnings.append(make_warning(
            "missing_expected_bookmakers",
            "warning",
            f"Missing expected sportsbooks from provider response: {', '.join(missing_books)}.",
        ))

    blocker_codes = [warning["code"] for warning in warnings if warning["code"] in ACTION_BLOCK_CODES]
    actionable = len(blocker_codes) == 0
    if not actionable:
        warnings.append(make_warning(
            "do_not_bet_real_money",
            "blocker",
            "Guardrails mark this prediction as research-only. Do not treat it as a real-money wager.",
        ))

    if any(warning["severity"] == "blocker" for warning in warnings):
        quality = "weak"
    elif warnings:
        quality = "okay"
    else:
        quality = "strong"

    return {
        "data_quality": quality,
        "warnings": warnings,
        "actionable": actionable,
        "recommendation_guardrail": "clear" if actionable else "blocked",
        "guardrail_reasons": blocker_codes,
        "do_not_bet_real_money": not actionable,
    }


def apply_recommendation_guardrail(technical_recommendation: str, assessment: dict) -> str:
    if technical_recommendation == "bet" and not assessment.get("actionable", False):
        return "pass"
    return technical_recommendation


def summarize_data_quality(predictions: list) -> dict:
    warning_counter = Counter()
    severity_counter = Counter()
    quality_counter = Counter()
    blocked = 0
    actionable = 0

    for pred in predictions:
        quality_counter[pred.get("data_quality", "unknown")] += 1
        if pred.get("actionable"):
            actionable += 1
        if pred.get("recommendation_guardrail") == "blocked":
            blocked += 1

        for warning in pred.get("quality_warnings", []):
            warning_counter[warning.get("code", "unknown")] += 1
            severity_counter[warning.get("severity", "unknown")] += 1

    if quality_counter.get("weak"):
        overall = "weak"
    elif quality_counter.get("okay"):
        overall = "okay"
    elif quality_counter.get("strong"):
        overall = "strong"
    else:
        overall = "none"

    return {
        "overall_data_quality": overall,
        "prediction_count": len(predictions),
        "actionable_predictions": actionable,
        "blocked_predictions": blocked,
        "do_not_bet_real_money": blocked > 0,
        "warning_counts_by_code": dict(sorted(warning_counter.items())),
        "warning_counts_by_severity": dict(sorted(severity_counter.items())),
        "quality_counts": dict(sorted(quality_counter.items())),
    }
