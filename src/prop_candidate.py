import math


class PropCandidateValidationError(ValueError):
    pass


def _normalize_slug(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_required_slug(value, name: str) -> str:
    if not isinstance(value, str):
        raise PropCandidateValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    normalized = _normalize_slug(value)
    if not normalized:
        raise PropCandidateValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return normalized


def _validate_required_id(value, name: str) -> str:
    if not isinstance(value, str):
        raise PropCandidateValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise PropCandidateValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return stripped


def _validate_optional_str(value, name: str) -> "str | None":
    if value is None:
        return None
    if not isinstance(value, str):
        raise PropCandidateValidationError(
            f"{name} must be a string or None, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise PropCandidateValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return stripped


def _validate_line(value) -> "float | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise PropCandidateValidationError("line must not be a bool")
    if not isinstance(value, (int, float)):
        raise PropCandidateValidationError(
            f"line must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise PropCandidateValidationError("line must not be NaN")
    if math.isinf(value):
        raise PropCandidateValidationError("line must not be infinite")
    return float(value)


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PropCandidateValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def normalize_sport(sport: str) -> str:
    return _validate_required_slug(sport, "sport")


def normalize_league(league: str) -> str:
    return _validate_required_slug(league, "league")


def normalize_market_type(market_type: str) -> str:
    return _validate_required_slug(market_type, "market_type")


def normalize_selection(selection: str) -> str:
    return _validate_required_slug(selection, "selection")


def build_prop_candidate(
    sport: str,
    league: str,
    event_id: str,
    market_type: str,
    selection: str,
    *,
    line=None,
    player_id=None,
    player_name=None,
    team_id=None,
    team_name=None,
    opponent_id=None,
    opponent_name=None,
    created_at=None,
    metadata=None,
) -> dict:
    validated_sport = normalize_sport(sport)
    validated_league = normalize_league(league)
    validated_event_id = _validate_required_id(event_id, "event_id")
    validated_market_type = normalize_market_type(market_type)
    validated_selection = normalize_selection(selection)
    validated_line = _validate_line(line)
    validated_player_id = _validate_optional_str(player_id, "player_id")
    validated_player_name = _validate_optional_str(player_name, "player_name")
    validated_team_id = _validate_optional_str(team_id, "team_id")
    validated_team_name = _validate_optional_str(team_name, "team_name")
    validated_opponent_id = _validate_optional_str(opponent_id, "opponent_id")
    validated_opponent_name = _validate_optional_str(opponent_name, "opponent_name")
    validated_created_at = _validate_optional_str(created_at, "created_at")
    validated_metadata = _validate_metadata(metadata)

    return {
        "sport": validated_sport,
        "league": validated_league,
        "event_id": validated_event_id,
        "market_type": validated_market_type,
        "selection": validated_selection,
        "line": validated_line,
        "player_id": validated_player_id,
        "player_name": validated_player_name,
        "team_id": validated_team_id,
        "team_name": validated_team_name,
        "opponent_id": validated_opponent_id,
        "opponent_name": validated_opponent_name,
        "created_at": validated_created_at,
        "metadata": validated_metadata,
    }
