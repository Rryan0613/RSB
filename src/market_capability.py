class MarketCapabilityValidationError(ValueError):
    pass


VALID_LINE_VALUE_TYPES = frozenset({"integer", "float"})

_MARKET_CAPABILITY_KEYS = (
    "sport",
    "league",
    "market_type",
    "selection_type",
    "requires_line",
    "allows_line",
    "line_value_type",
    "requires_player",
    "requires_team",
    "requires_opponent",
    "requires_starting_status",
    "start_required_supported",
    "participation_required_supported",
    "void_condition_supported",
    "settlement_rule_required",
    "supported_selection_values",
    "required_fields",
    "optional_fields",
    "metadata",
)


def _normalize_slug(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_required_slug(value, name: str) -> str:
    if not isinstance(value, str):
        raise MarketCapabilityValidationError(
            f"{name} must be a string, got {type(value).__name__!r}"
        )
    normalized = _normalize_slug(value)
    if not normalized:
        raise MarketCapabilityValidationError(
            f"{name} must not be empty or whitespace-only"
        )
    return normalized


def _validate_bool(value, name: str) -> bool:
    if not isinstance(value, bool):
        raise MarketCapabilityValidationError(
            f"{name} must be a bool, got {type(value).__name__!r}"
        )
    return value


def _validate_line_value_type(value) -> "str | None":
    if value is None:
        return None
    if not isinstance(value, str):
        raise MarketCapabilityValidationError(
            f"line_value_type must be a string or None, got {type(value).__name__!r}"
        )
    normalized = _normalize_slug(value)
    if normalized not in VALID_LINE_VALUE_TYPES:
        raise MarketCapabilityValidationError(
            f"line_value_type {value!r} is not valid; "
            f"must be one of {sorted(VALID_LINE_VALUE_TYPES)}"
        )
    return normalized


def _validate_supported_selection_values(value) -> "list[str] | None":
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise MarketCapabilityValidationError(
            f"supported_selection_values must be a list or tuple, "
            f"got {type(value).__name__!r}"
        )
    if len(value) == 0:
        raise MarketCapabilityValidationError(
            "supported_selection_values must not be empty when provided"
        )
    normalized_values = []
    seen = set()
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise MarketCapabilityValidationError(
                f"supported_selection_values[{i}] must be a string, "
                f"got {type(item).__name__!r}"
            )
        normalized = _normalize_slug(item)
        if not normalized:
            raise MarketCapabilityValidationError(
                f"supported_selection_values[{i}] must not be empty or whitespace-only"
            )
        if normalized in seen:
            raise MarketCapabilityValidationError(
                f"supported_selection_values contains duplicate value: {normalized!r}"
            )
        seen.add(normalized)
        normalized_values.append(normalized)
    return normalized_values


def _validate_field_list(value, name: str) -> "list[str]":
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise MarketCapabilityValidationError(
            f"{name} must be a list or tuple, got {type(value).__name__!r}"
        )
    normalized_values = []
    seen = set()
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise MarketCapabilityValidationError(
                f"{name}[{i}] must be a string, got {type(item).__name__!r}"
            )
        normalized = _normalize_slug(item)
        if not normalized:
            raise MarketCapabilityValidationError(
                f"{name}[{i}] must not be empty or whitespace-only"
            )
        if normalized in seen:
            raise MarketCapabilityValidationError(
                f"{name} contains duplicate value: {normalized!r}"
            )
        seen.add(normalized)
        normalized_values.append(normalized)
    return normalized_values


def _validate_metadata(value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise MarketCapabilityValidationError(
            f"metadata must be a dict, got {type(value).__name__!r}"
        )
    return dict(value)


def normalize_sport(sport) -> str:
    return _validate_required_slug(sport, "sport")


def normalize_league(league) -> str:
    return _validate_required_slug(league, "league")


def normalize_market_type(market_type) -> str:
    return _validate_required_slug(market_type, "market_type")


def normalize_selection_type(selection_type) -> str:
    return _validate_required_slug(selection_type, "selection_type")


def build_market_capability(
    *,
    sport,
    league,
    market_type,
    selection_type,
    requires_line=False,
    allows_line=False,
    line_value_type=None,
    requires_player=False,
    requires_team=False,
    requires_opponent=False,
    requires_starting_status=False,
    start_required_supported=False,
    participation_required_supported=False,
    void_condition_supported=False,
    settlement_rule_required=False,
    supported_selection_values=None,
    required_fields=None,
    optional_fields=None,
    metadata=None,
) -> dict:
    validated_sport = normalize_sport(sport)
    validated_league = normalize_league(league)
    validated_market_type = normalize_market_type(market_type)
    validated_selection_type = normalize_selection_type(selection_type)

    validated_requires_line = _validate_bool(requires_line, "requires_line")
    validated_allows_line = _validate_bool(allows_line, "allows_line")
    validated_requires_player = _validate_bool(requires_player, "requires_player")
    validated_requires_team = _validate_bool(requires_team, "requires_team")
    validated_requires_opponent = _validate_bool(requires_opponent, "requires_opponent")
    validated_requires_starting_status = _validate_bool(
        requires_starting_status, "requires_starting_status"
    )
    validated_start_required_supported = _validate_bool(
        start_required_supported, "start_required_supported"
    )
    validated_participation_required_supported = _validate_bool(
        participation_required_supported, "participation_required_supported"
    )
    validated_void_condition_supported = _validate_bool(
        void_condition_supported, "void_condition_supported"
    )
    validated_settlement_rule_required = _validate_bool(
        settlement_rule_required, "settlement_rule_required"
    )

    if validated_requires_line and not validated_allows_line:
        raise MarketCapabilityValidationError(
            "requires_line=True requires allows_line=True"
        )
    if not validated_allows_line and line_value_type is not None:
        raise MarketCapabilityValidationError(
            "line_value_type must be None when allows_line=False"
        )
    if validated_allows_line and line_value_type is None:
        raise MarketCapabilityValidationError(
            "line_value_type is required when allows_line=True"
        )
    validated_line_value_type = _validate_line_value_type(line_value_type)

    validated_supported_selection_values = _validate_supported_selection_values(
        supported_selection_values
    )
    validated_required_fields = _validate_field_list(required_fields, "required_fields")
    validated_optional_fields = _validate_field_list(optional_fields, "optional_fields")

    overlap = set(validated_required_fields) & set(validated_optional_fields)
    if overlap:
        raise MarketCapabilityValidationError(
            f"required_fields and optional_fields must not overlap: {sorted(overlap)}"
        )

    validated_metadata = _validate_metadata(metadata)

    return {
        "sport": validated_sport,
        "league": validated_league,
        "market_type": validated_market_type,
        "selection_type": validated_selection_type,
        "requires_line": validated_requires_line,
        "allows_line": validated_allows_line,
        "line_value_type": validated_line_value_type,
        "requires_player": validated_requires_player,
        "requires_team": validated_requires_team,
        "requires_opponent": validated_requires_opponent,
        "requires_starting_status": validated_requires_starting_status,
        "start_required_supported": validated_start_required_supported,
        "participation_required_supported": validated_participation_required_supported,
        "void_condition_supported": validated_void_condition_supported,
        "settlement_rule_required": validated_settlement_rule_required,
        "supported_selection_values": validated_supported_selection_values,
        "required_fields": validated_required_fields,
        "optional_fields": validated_optional_fields,
        "metadata": validated_metadata,
    }


def build_sport_market_profile(
    *,
    sport,
    league,
    supported_markets=None,
    metadata=None,
) -> dict:
    validated_sport = normalize_sport(sport)
    validated_league = normalize_league(league)
    validated_metadata = _validate_metadata(metadata)

    if supported_markets is None:
        supported_markets = []
    if not isinstance(supported_markets, (list, tuple)):
        raise MarketCapabilityValidationError(
            f"supported_markets must be a list or tuple, "
            f"got {type(supported_markets).__name__!r}"
        )

    validated_supported_markets = []
    seen_pairs = set()
    for idx, item in enumerate(supported_markets):
        if not isinstance(item, dict):
            raise MarketCapabilityValidationError(
                f"supported_markets[{idx}] must be a dict, got {type(item).__name__!r}"
            )

        expected_keys = set(_MARKET_CAPABILITY_KEYS)
        actual_keys = set(item)
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        if missing:
            raise MarketCapabilityValidationError(
                f"supported_markets[{idx}] is missing required keys: {sorted(missing)}"
            )
        if extra:
            raise MarketCapabilityValidationError(
                f"supported_markets[{idx}] has unexpected keys: {sorted(extra)}"
            )

        if item["sport"] != validated_sport:
            raise MarketCapabilityValidationError(
                f"supported_markets[{idx}] sport {item['sport']!r} does not match "
                f"profile sport {validated_sport!r}"
            )
        if item["league"] != validated_league:
            raise MarketCapabilityValidationError(
                f"supported_markets[{idx}] league {item['league']!r} does not match "
                f"profile league {validated_league!r}"
            )

        pair = (item["market_type"], item["selection_type"])
        if pair in seen_pairs:
            raise MarketCapabilityValidationError(
                f"duplicate supported market for "
                f"(market_type, selection_type)={pair!r}"
            )
        seen_pairs.add(pair)

        validated_supported_markets.append(dict(item))

    return {
        "sport": validated_sport,
        "league": validated_league,
        "supported_markets": validated_supported_markets,
        "market_count": len(validated_supported_markets),
        "metadata": validated_metadata,
    }
