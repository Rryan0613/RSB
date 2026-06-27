class StageMarketValidationError(ValueError):
    pass


VALID_STAGES = frozenset({
    "group",
    "round_of_32",
    "round_of_16",
    "quarterfinal",
    "semifinal",
    "final",
    "league",
})

VALID_MARKET_TYPES = frozenset({
    "regulation_result",
    "to_advance",
})

DRAW_ALLOWED_MARKET_TYPES = frozenset({
    "regulation_result",
})


def _normalize(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def normalize_stage(raw: str) -> str:
    normalized = _normalize(raw)
    if normalized not in VALID_STAGES:
        raise StageMarketValidationError(
            f"Unknown stage: {raw!r}. Valid stages: {sorted(VALID_STAGES)}"
        )
    return normalized


def normalize_market_type(raw: str) -> str:
    normalized = _normalize(raw)
    if normalized not in VALID_MARKET_TYPES:
        raise StageMarketValidationError(
            f"Unknown market_type: {raw!r}. Valid market_types: {sorted(VALID_MARKET_TYPES)}"
        )
    return normalized


def allows_draw(market_type: str) -> bool:
    normalized = normalize_market_type(market_type)
    return normalized in DRAW_ALLOWED_MARKET_TYPES


def validate_stage_market(stage: str, market_type: str) -> dict:
    normalized_stage = normalize_stage(stage)
    normalized_market_type = normalize_market_type(market_type)
    return {
        "stage": normalized_stage,
        "market_type": normalized_market_type,
        "allows_draw": normalized_market_type in DRAW_ALLOWED_MARKET_TYPES,
    }
