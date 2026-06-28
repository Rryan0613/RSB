class ReviewTaxonomyValidationError(ValueError):
    pass


VALID_REVIEW_CATEGORIES = frozenset({
    "data_quality",
    "market_semantics",
    "model_calibration",
    "feature_gap",
    "lineup_context",
    "injury_context",
    "rotation_context",
    "tactical_context",
    "variance",
    "leakage_risk",
    "unknown",
})

VALID_REVIEW_SEVERITIES = frozenset({
    "low",
    "medium",
    "high",
    "critical",
})

VALID_DATA_QUALITIES = frozenset({
    "strong",
    "okay",
    "weak",
    "unknown",
})


def _normalize(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def normalize_review_category(raw: str) -> str:
    normalized = _normalize(raw)
    if normalized not in VALID_REVIEW_CATEGORIES:
        raise ReviewTaxonomyValidationError(
            f"Unknown review_category: {raw!r}. Valid review_categories: {sorted(VALID_REVIEW_CATEGORIES)}"
        )
    return normalized


def normalize_review_severity(raw: str) -> str:
    normalized = _normalize(raw)
    if normalized not in VALID_REVIEW_SEVERITIES:
        raise ReviewTaxonomyValidationError(
            f"Unknown review_severity: {raw!r}. Valid review_severities: {sorted(VALID_REVIEW_SEVERITIES)}"
        )
    return normalized


def normalize_data_quality(raw: str) -> str:
    normalized = _normalize(raw)
    if normalized not in VALID_DATA_QUALITIES:
        raise ReviewTaxonomyValidationError(
            f"Unknown data_quality: {raw!r}. Valid data_qualities: {sorted(VALID_DATA_QUALITIES)}"
        )
    return normalized


def validate_review_taxonomy(review_category: str, severity: str, data_quality: str) -> dict:
    normalized_review_category = normalize_review_category(review_category)
    normalized_severity = normalize_review_severity(severity)
    normalized_data_quality = normalize_data_quality(data_quality)
    return {
        "review_category": normalized_review_category,
        "severity": normalized_severity,
        "data_quality": normalized_data_quality,
    }
