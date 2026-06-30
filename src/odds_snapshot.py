import math


class OddsSnapshotValidationError(ValueError):
    pass


VALID_ODDS_FORMATS = frozenset({"american", "decimal"})


def _normalize_slug(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_required_slug(value, name: str) -> str:
    if not isinstance(value, str):
        raise OddsSnapshotValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    normalized = _normalize_slug(value)
    if not normalized:
        raise OddsSnapshotValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return normalized


def _validate_required_id(value, name: str) -> str:
    if not isinstance(value, str):
        raise OddsSnapshotValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise OddsSnapshotValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return stripped


def _validate_optional_str(value, name: str) -> "str | None":
    if value is None:
        return None
    if not isinstance(value, str):
        raise OddsSnapshotValidationError(
            f"{name} must be a string or None, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise OddsSnapshotValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return stripped


def _validate_line(value) -> "float | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise OddsSnapshotValidationError("line must not be a bool")
    if not isinstance(value, (int, float)):
        raise OddsSnapshotValidationError(
            f"line must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise OddsSnapshotValidationError("line must not be NaN")
    if math.isinf(value):
        raise OddsSnapshotValidationError("line must not be infinite")
    return float(value)


def _validate_odds(value, odds_format: str) -> float:
    if isinstance(value, bool):
        raise OddsSnapshotValidationError("odds must not be a bool")
    if not isinstance(value, (int, float)):
        raise OddsSnapshotValidationError(
            f"odds must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise OddsSnapshotValidationError("odds must not be NaN")
    if math.isinf(value):
        raise OddsSnapshotValidationError("odds must not be infinite")
    if odds_format == "american" and value == 0:
        raise OddsSnapshotValidationError("American odds must not be zero")
    if odds_format == "decimal" and value <= 1.0:
        raise OddsSnapshotValidationError(
            f"Decimal odds must be greater than 1.0, got {value!r}"
        )
    return float(value)


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise OddsSnapshotValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def normalize_provider(provider: str) -> str:
    return _validate_required_slug(provider, "provider")


def normalize_sportsbook(sportsbook: str) -> str:
    return _validate_required_slug(sportsbook, "sportsbook")


def normalize_market_type(market_type: str) -> str:
    return _validate_required_slug(market_type, "market_type")


def normalize_selection(selection: str) -> str:
    return _validate_required_slug(selection, "selection")


def normalize_odds_format(odds_format: str) -> str:
    normalized = _validate_required_slug(odds_format, "odds_format")
    if normalized not in VALID_ODDS_FORMATS:
        raise OddsSnapshotValidationError(
            f"odds_format {normalized!r} is not supported; must be one of {sorted(VALID_ODDS_FORMATS)}"
        )
    return normalized


def build_odds_snapshot(
    provider: str,
    sportsbook: str,
    event_id: str,
    market_type: str,
    selection: str,
    odds,
    odds_format: str,
    odds_found_at: str,
    *,
    line=None,
    source=None,
    metadata=None,
) -> dict:
    validated_provider = normalize_provider(provider)
    validated_sportsbook = normalize_sportsbook(sportsbook)
    validated_event_id = _validate_required_id(event_id, "event_id")
    validated_market_type = normalize_market_type(market_type)
    validated_selection = normalize_selection(selection)
    validated_line = _validate_line(line)
    validated_odds_format = normalize_odds_format(odds_format)
    validated_odds = _validate_odds(odds, validated_odds_format)
    validated_odds_found_at = _validate_required_id(odds_found_at, "odds_found_at")
    validated_source = _validate_optional_str(source, "source")
    validated_metadata = _validate_metadata(metadata)

    return {
        "provider": validated_provider,
        "sportsbook": validated_sportsbook,
        "event_id": validated_event_id,
        "market_type": validated_market_type,
        "selection": validated_selection,
        "line": validated_line,
        "odds": validated_odds,
        "odds_format": validated_odds_format,
        "odds_found_at": validated_odds_found_at,
        "source": validated_source,
        "metadata": validated_metadata,
    }
