import math


class PropResultValidationError(ValueError):
    pass


VALID_SETTLEMENT_STATUSES = frozenset({
    "won",
    "lost",
    "push",
    "void",
    "pending",
    "unknown",
})

FINAL_SETTLEMENT_STATUSES = frozenset({
    "won",
    "lost",
    "push",
    "void",
})


def _normalize_slug(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_required_slug(value, name: str) -> str:
    if not isinstance(value, str):
        raise PropResultValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    normalized = _normalize_slug(value)
    if not normalized:
        raise PropResultValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return normalized


def _validate_required_id(value, name: str) -> str:
    if not isinstance(value, str):
        raise PropResultValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise PropResultValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return stripped


def _validate_optional_str(value, name: str) -> "str | None":
    if value is None:
        return None
    if not isinstance(value, str):
        raise PropResultValidationError(
            f"{name} must be a string or None, got {type(value).__name__!r}"
        )
    stripped = value.strip()
    if not stripped:
        raise PropResultValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return stripped


def _validate_numeric(value, name: str) -> "float | None":
    if value is None:
        return None
    if isinstance(value, bool):
        raise PropResultValidationError(f"{name} must not be a bool")
    if not isinstance(value, (int, float)):
        raise PropResultValidationError(
            f"{name} must be int or float, got {type(value).__name__!r}"
        )
    if math.isnan(value):
        raise PropResultValidationError(f"{name} must not be NaN")
    if math.isinf(value):
        raise PropResultValidationError(f"{name} must not be infinite")
    return float(value)


def _validate_optional_bool(value, name: str) -> "bool | None":
    if value is None:
        return None
    if not isinstance(value, bool):
        raise PropResultValidationError(
            f"{name} must be a bool or None, got {type(value).__name__!r}"
        )
    return value


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PropResultValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def normalize_market_type(market_type: str) -> str:
    return _validate_required_slug(market_type, "market_type")


def normalize_selection(selection: str) -> str:
    return _validate_required_slug(selection, "selection")


def normalize_settlement_status(status: str) -> str:
    normalized = _validate_required_slug(status, "settlement_status")
    if normalized not in VALID_SETTLEMENT_STATUSES:
        raise PropResultValidationError(
            f"settlement_status {normalized!r} is not valid; "
            f"must be one of {sorted(VALID_SETTLEMENT_STATUSES)}"
        )
    return normalized


def build_prop_result(
    *,
    event_id,
    market_type,
    selection,
    line=None,
    actual_value=None,
    settlement_status,
    settled_at=None,
    source=None,
    settlement_rule=None,
    start_required=None,
    participation_required=None,
    void_condition=None,
    void_reason=None,
    metadata=None,
) -> dict:
    validated_event_id = _validate_required_id(event_id, "event_id")
    validated_market_type = normalize_market_type(market_type)
    validated_selection = normalize_selection(selection)
    validated_line = _validate_numeric(line, "line")
    validated_actual_value = _validate_numeric(actual_value, "actual_value")
    validated_status = normalize_settlement_status(settlement_status)
    validated_settled_at = _validate_optional_str(settled_at, "settled_at")
    validated_source = _validate_optional_str(source, "source")
    validated_settlement_rule = _validate_optional_str(settlement_rule, "settlement_rule")
    validated_start_required = _validate_optional_bool(start_required, "start_required")
    validated_participation_required = _validate_optional_bool(
        participation_required, "participation_required"
    )
    validated_void_condition = _validate_optional_str(void_condition, "void_condition")
    validated_void_reason = _validate_optional_str(void_reason, "void_reason")
    validated_metadata = _validate_metadata(metadata)

    if validated_status in FINAL_SETTLEMENT_STATUSES and validated_settled_at is None:
        raise PropResultValidationError(
            f"settlement_status={validated_status!r} requires settled_at to be provided"
        )
    if validated_status in {"pending", "unknown"} and validated_settled_at is not None:
        raise PropResultValidationError(
            f"settlement_status={validated_status!r} requires settled_at to be None"
        )
    if validated_status != "void" and validated_void_reason is not None:
        raise PropResultValidationError(
            f"void_reason must be None when settlement_status={validated_status!r}"
        )

    return {
        "event_id": validated_event_id,
        "market_type": validated_market_type,
        "selection": validated_selection,
        "line": validated_line,
        "actual_value": validated_actual_value,
        "settlement_status": validated_status,
        "settled_at": validated_settled_at,
        "source": validated_source,
        "settlement_rule": validated_settlement_rule,
        "start_required": validated_start_required,
        "participation_required": validated_participation_required,
        "void_condition": validated_void_condition,
        "void_reason": validated_void_reason,
        "metadata": validated_metadata,
    }
