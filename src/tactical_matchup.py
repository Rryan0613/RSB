TRUSTED_TACTICAL_SOURCES = {
    "official_feed",
    "verified_dataset",
    "verified_scouting_report",
    "historical_backfill",
    "model_tactical_store",
}

DEFAULT_RATING = 5.0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def to_float(value, default=0.0):
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def match_tactical(match: dict) -> dict:
    tactical = match.get("tactical") or {}
    return tactical if isinstance(tactical, dict) else {}


def team_tactical(match: dict, team_key: str) -> dict:
    team_data = match_tactical(match).get(team_key) or {}
    return team_data if isinstance(team_data, dict) else {}


def has_team_tactical(match: dict, team_key: str) -> bool:
    return bool(team_tactical(match, team_key))


def tactical_source(team_data: dict, match: dict = None) -> str:
    match = match or {}
    tactical = match_tactical(match)
    return (
        team_data.get("source")
        or team_data.get("tactical_source")
        or tactical.get("source")
        or tactical.get("tactical_source")
        or match.get("tactical_source")
        or "unspecified"
    )


def is_verified_tactical_source(source: str) -> bool:
    return source in TRUSTED_TACTICAL_SOURCES


def rating(team_data: dict, field: str, default=DEFAULT_RATING) -> float:
    return clamp(to_float(team_data.get(field), default), 0.0, 10.0)


def confidence(team_data: dict) -> float:
    return clamp(to_float(team_data.get("tactical_confidence"), 0.0), 0.0, 1.0)


def pressing_intensity(team_data: dict) -> float:
    return rating(team_data, "pressing_intensity")


def build_up_quality(team_data: dict) -> float:
    return rating(team_data, "build_up_quality")


def defensive_line_height(team_data: dict) -> float:
    return rating(team_data, "defensive_line_height")


def pace_threat(team_data: dict) -> float:
    return rating(team_data, "pace_threat")


def crossing_volume(team_data: dict) -> float:
    return rating(team_data, "crossing_volume")


def aerial_threat(team_data: dict) -> float:
    return rating(team_data, "aerial_threat")


def aerial_defense(team_data: dict) -> float:
    return rating(team_data, "aerial_defense")


def set_piece_attack(team_data: dict) -> float:
    return rating(team_data, "set_piece_attack")


def set_piece_defense(team_data: dict) -> float:
    return rating(team_data, "set_piece_defense")


def counterattack_threat(team_data: dict) -> float:
    return rating(team_data, "counterattack_threat")


def transition_defense(team_data: dict) -> float:
    return rating(team_data, "transition_defense")


def midfield_control(team_data: dict) -> float:
    return rating(team_data, "midfield_control")


def formation_flexibility(team_data: dict) -> float:
    return rating(team_data, "formation_flexibility")


def manager_tactical_rating(team_data: dict) -> float:
    return rating(team_data, "manager_tactical_rating")


def low_block_comfort(team_data: dict) -> float:
    return rating(team_data, "low_block_comfort")


def chance_creation_centrality(team_data: dict) -> float:
    return rating(team_data, "chance_creation_centrality")


def wide_creation(team_data: dict) -> float:
    return rating(team_data, "wide_creation")


def press_resistance(team_data: dict) -> float:
    return rating(team_data, "press_resistance")


def vulnerability_to_press(team_data: dict) -> float:
    return rating(team_data, "vulnerability_to_press")


def tactical_snapshot(team_data: dict) -> dict:
    return {
        "tactical_confidence": confidence(team_data),
        "pressing_intensity": pressing_intensity(team_data),
        "build_up_quality": build_up_quality(team_data),
        "defensive_line_height": defensive_line_height(team_data),
        "pace_threat": pace_threat(team_data),
        "crossing_volume": crossing_volume(team_data),
        "aerial_threat": aerial_threat(team_data),
        "aerial_defense": aerial_defense(team_data),
        "set_piece_attack": set_piece_attack(team_data),
        "set_piece_defense": set_piece_defense(team_data),
        "counterattack_threat": counterattack_threat(team_data),
        "transition_defense": transition_defense(team_data),
        "midfield_control": midfield_control(team_data),
        "formation_flexibility": formation_flexibility(team_data),
        "manager_tactical_rating": manager_tactical_rating(team_data),
        "low_block_comfort": low_block_comfort(team_data),
        "chance_creation_centrality": chance_creation_centrality(team_data),
        "wide_creation": wide_creation(team_data),
        "press_resistance": press_resistance(team_data),
        "vulnerability_to_press": vulnerability_to_press(team_data),
    }


def press_vs_buildup_edge(pressing_team: dict, buildup_team: dict) -> float:
    return pressing_intensity(pressing_team) + vulnerability_to_press(buildup_team) - build_up_quality(buildup_team) - press_resistance(buildup_team)


def pace_vs_high_line_edge(attacking_team: dict, defending_team: dict) -> float:
    return pace_threat(attacking_team) + defensive_line_height(defending_team) - transition_defense(defending_team)


def crossing_vs_aerial_edge(attacking_team: dict, defending_team: dict) -> float:
    attacking_cross_profile = (crossing_volume(attacking_team) + aerial_threat(attacking_team)) / 2
    return attacking_cross_profile - aerial_defense(defending_team)


def set_piece_edge(attacking_team: dict, defending_team: dict) -> float:
    return set_piece_attack(attacking_team) - set_piece_defense(defending_team)


def counterattack_edge(attacking_team: dict, defending_team: dict) -> float:
    return counterattack_threat(attacking_team) + defensive_line_height(defending_team) - transition_defense(defending_team)


def central_creation_edge(attacking_team: dict, defending_team: dict) -> float:
    return chance_creation_centrality(attacking_team) + midfield_control(attacking_team) - midfield_control(defending_team)


def wide_creation_edge(attacking_team: dict, defending_team: dict) -> float:
    return wide_creation(attacking_team) + crossing_volume(attacking_team) - aerial_defense(defending_team)


def tactical_feature_set(match: dict) -> dict:
    home_data = team_tactical(match, "home")
    away_data = team_tactical(match, "away")
    home = tactical_snapshot(home_data)
    away = tactical_snapshot(away_data)

    return {
        "tactical_confidence_min": min(home["tactical_confidence"], away["tactical_confidence"]),
        "tactical_confidence_diff": home["tactical_confidence"] - away["tactical_confidence"],
        "pressing_intensity_diff": home["pressing_intensity"] - away["pressing_intensity"],
        "build_up_quality_diff": home["build_up_quality"] - away["build_up_quality"],
        "press_resistance_diff": home["press_resistance"] - away["press_resistance"],
        "home_press_vs_away_buildup": press_vs_buildup_edge(home_data, away_data),
        "away_press_vs_home_buildup": press_vs_buildup_edge(away_data, home_data),
        "home_pace_vs_away_high_line": pace_vs_high_line_edge(home_data, away_data),
        "away_pace_vs_home_high_line": pace_vs_high_line_edge(away_data, home_data),
        "home_crossing_vs_away_aerial_defense": crossing_vs_aerial_edge(home_data, away_data),
        "away_crossing_vs_home_aerial_defense": crossing_vs_aerial_edge(away_data, home_data),
        "home_set_piece_edge": set_piece_edge(home_data, away_data),
        "away_set_piece_edge": set_piece_edge(away_data, home_data),
        "home_counterattack_edge": counterattack_edge(home_data, away_data),
        "away_counterattack_edge": counterattack_edge(away_data, home_data),
        "home_central_creation_edge": central_creation_edge(home_data, away_data),
        "away_central_creation_edge": central_creation_edge(away_data, home_data),
        "home_wide_creation_edge": wide_creation_edge(home_data, away_data),
        "away_wide_creation_edge": wide_creation_edge(away_data, home_data),
        "midfield_control_diff": home["midfield_control"] - away["midfield_control"],
        "formation_flexibility_diff": home["formation_flexibility"] - away["formation_flexibility"],
        "manager_tactical_diff": home["manager_tactical_rating"] - away["manager_tactical_rating"],
        "low_block_comfort_diff": home["low_block_comfort"] - away["low_block_comfort"],
        "transition_defense_diff": home["transition_defense"] - away["transition_defense"],
    }


def tactical_review_flags(match: dict) -> list:
    flags = []
    home = team_tactical(match, "home")
    away = team_tactical(match, "away")

    if pace_vs_high_line_edge(home, away) >= 8:
        flags.append("home_pace_vs_away_high_line")
    if pace_vs_high_line_edge(away, home) >= 8:
        flags.append("away_pace_vs_home_high_line")
    if press_vs_buildup_edge(home, away) >= 5:
        flags.append("home_press_vs_away_buildup")
    if press_vs_buildup_edge(away, home) >= 5:
        flags.append("away_press_vs_home_buildup")
    if set_piece_edge(home, away) >= 3:
        flags.append("home_set_piece_edge")
    if set_piece_edge(away, home) >= 3:
        flags.append("away_set_piece_edge")

    return flags
