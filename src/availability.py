TRUSTED_AVAILABILITY_SOURCES = {
    "official_feed",
    "official_lineup",
    "verified_dataset",
    "verified_team_news",
    "historical_backfill",
    "model_availability_store",
}

DEFAULT_NORMAL_STARTER_COUNT = 11


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def to_float(value, default=0.0):
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def match_availability(match: dict) -> dict:
    availability = match.get("availability") or {}
    return availability if isinstance(availability, dict) else {}


def team_availability(match: dict, team_key: str) -> dict:
    team_data = match_availability(match).get(team_key) or {}
    return team_data if isinstance(team_data, dict) else {}


def has_team_availability(match: dict, team_key: str) -> bool:
    return bool(team_availability(match, team_key))


def availability_source(team_data: dict, match: dict = None) -> str:
    match = match or {}
    availability = match_availability(match)
    return (
        team_data.get("source")
        or team_data.get("availability_source")
        or availability.get("source")
        or availability.get("availability_source")
        or match.get("availability_source")
        or "unspecified"
    )


def is_verified_availability_source(source: str) -> bool:
    return source in TRUSTED_AVAILABILITY_SOURCES


def lineup_status(team_data: dict) -> str:
    return str(team_data.get("lineup_status") or "unknown").lower()


def lineup_confidence(team_data: dict) -> float:
    return clamp(to_float(team_data.get("lineup_confidence"), 0.0), 0.0, 1.0)


def normal_starter_count(team_data: dict) -> int:
    return max(1, to_int(team_data.get("normal_starter_count"), DEFAULT_NORMAL_STARTER_COUNT))


def expected_starters_available(team_data: dict) -> int:
    default = normal_starter_count(team_data)
    return clamp(to_int(team_data.get("expected_starters_available"), default), 0, default)


def starter_availability_rate(team_data: dict) -> float:
    return expected_starters_available(team_data) / normal_starter_count(team_data)


def lineup_strength_rating(team_data: dict) -> float:
    return clamp(to_float(team_data.get("lineup_strength_rating"), 100.0), 0.0, 100.0)


def rotation_risk(team_data: dict) -> float:
    return clamp(to_float(team_data.get("rotation_risk"), 0.0), 0.0, 10.0)


def b_team_risk(team_data: dict) -> float:
    return clamp(to_float(team_data.get("b_team_risk"), 0.0), 0.0, 10.0)


def replacement_quality_rating(team_data: dict) -> float:
    return clamp(to_float(team_data.get("replacement_quality_rating"), 7.0), 0.0, 10.0)


def key_absences(team_data: dict) -> list:
    values = team_data.get("key_absences") or []
    return values if isinstance(values, list) else []


def returning_players(team_data: dict) -> list:
    values = team_data.get("returning_players") or []
    return values if isinstance(values, list) else []


def fitness_concerns(team_data: dict) -> list:
    values = team_data.get("fitness_concerns") or []
    return values if isinstance(values, list) else []


def impact_rating(item: dict, default=0.0) -> float:
    if not isinstance(item, dict):
        return default
    return clamp(to_float(item.get("impact_rating"), default), 0.0, 10.0)


def absence_impact(team_data: dict) -> float:
    return sum(impact_rating(item) for item in key_absences(team_data))


def high_impact_absence_count(team_data: dict, threshold=7.0) -> int:
    return sum(1 for item in key_absences(team_data) if impact_rating(item) >= threshold)


def minutes_restricted_count(team_data: dict) -> int:
    count = 0
    for player in returning_players(team_data):
        if isinstance(player, dict) and player.get("minutes_restriction") is True:
            count += 1
    for concern in fitness_concerns(team_data):
        if isinstance(concern, dict) and concern.get("minutes_restriction") is True:
            count += 1
    return count


def recent_returning_player_count(team_data: dict, max_days_since_return=14, max_games_since_return=2) -> int:
    count = 0
    for player in returning_players(team_data):
        if not isinstance(player, dict):
            continue
        days = player.get("days_since_return")
        games = player.get("games_since_return")
        is_recent_by_days = days is not None and to_int(days, 999) <= max_days_since_return
        is_recent_by_games = games is not None and to_int(games, 999) <= max_games_since_return
        if is_recent_by_days or is_recent_by_games:
            count += 1
    return count


def returning_player_risk(team_data: dict) -> float:
    risk = 0.0
    for player in returning_players(team_data):
        if not isinstance(player, dict):
            continue
        player_risk = to_float(player.get("risk_rating"), 0.0)
        if player_risk == 0.0:
            player_risk = impact_rating(player) * 0.5
        if player.get("minutes_restriction") is True:
            player_risk += 2.0
        games = player.get("games_since_return")
        days = player.get("days_since_return")
        if games is not None and to_int(games, 999) <= 1:
            player_risk += 1.5
        if days is not None and to_int(days, 999) <= 7:
            player_risk += 1.0
        risk += clamp(player_risk, 0.0, 10.0)
    return risk


def team_availability_snapshot(team_data: dict) -> dict:
    return {
        "lineup_status": lineup_status(team_data),
        "lineup_confidence": lineup_confidence(team_data),
        "normal_starter_count": normal_starter_count(team_data),
        "expected_starters_available": expected_starters_available(team_data),
        "starter_availability_rate": starter_availability_rate(team_data),
        "lineup_strength_rating": lineup_strength_rating(team_data),
        "rotation_risk": rotation_risk(team_data),
        "b_team_risk": b_team_risk(team_data),
        "replacement_quality_rating": replacement_quality_rating(team_data),
        "key_absence_count": len(key_absences(team_data)),
        "high_impact_absence_count": high_impact_absence_count(team_data),
        "key_absence_impact": absence_impact(team_data),
        "returning_player_count": len(returning_players(team_data)),
        "recent_returning_player_count": recent_returning_player_count(team_data),
        "returning_player_risk": returning_player_risk(team_data),
        "minutes_restricted_count": minutes_restricted_count(team_data),
        "fitness_concern_count": len(fitness_concerns(team_data)),
    }


def availability_feature_set(match: dict) -> dict:
    home = team_availability_snapshot(team_availability(match, "home"))
    away = team_availability_snapshot(team_availability(match, "away"))

    return {
        "home_lineup_strength_rating": home["lineup_strength_rating"],
        "away_lineup_strength_rating": away["lineup_strength_rating"],
        "lineup_strength_diff": home["lineup_strength_rating"] - away["lineup_strength_rating"],
        "home_starter_availability_rate": home["starter_availability_rate"],
        "away_starter_availability_rate": away["starter_availability_rate"],
        "starter_availability_rate_diff": home["starter_availability_rate"] - away["starter_availability_rate"],
        "expected_starters_available_diff": home["expected_starters_available"] - away["expected_starters_available"],
        "lineup_confidence_min": min(home["lineup_confidence"], away["lineup_confidence"]),
        "lineup_confidence_diff": home["lineup_confidence"] - away["lineup_confidence"],
        "rotation_risk_diff": home["rotation_risk"] - away["rotation_risk"],
        "b_team_risk_diff": home["b_team_risk"] - away["b_team_risk"],
        "replacement_quality_diff": home["replacement_quality_rating"] - away["replacement_quality_rating"],
        "key_absence_count_diff": home["key_absence_count"] - away["key_absence_count"],
        "high_impact_absence_count_diff": home["high_impact_absence_count"] - away["high_impact_absence_count"],
        "key_absence_impact_diff": home["key_absence_impact"] - away["key_absence_impact"],
        "returning_player_count_diff": home["returning_player_count"] - away["returning_player_count"],
        "recent_returning_player_count_diff": home["recent_returning_player_count"] - away["recent_returning_player_count"],
        "returning_player_risk_diff": home["returning_player_risk"] - away["returning_player_risk"],
        "minutes_restricted_count_diff": home["minutes_restricted_count"] - away["minutes_restricted_count"],
        "fitness_concern_count_diff": home["fitness_concern_count"] - away["fitness_concern_count"],
    }
