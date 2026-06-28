import pytest

from review_taxonomy import (
    ReviewTaxonomyValidationError,
    VALID_REVIEW_CATEGORIES,
    VALID_REVIEW_SEVERITIES,
    VALID_DATA_QUALITIES,
    normalize_review_category,
    normalize_review_severity,
    normalize_data_quality,
    validate_review_taxonomy,
)


# --- normalize_review_category ---

def test_normalize_review_category_all_canonical_values():
    canonical = [
        "data_quality", "market_semantics", "model_calibration", "feature_gap",
        "lineup_context", "injury_context", "rotation_context", "tactical_context",
        "variance", "leakage_risk", "unknown",
    ]
    for category in canonical:
        assert normalize_review_category(category) == category


def test_normalize_review_category_mixed_case():
    assert normalize_review_category("Data_Quality") == "data_quality"
    assert normalize_review_category("LEAKAGE_RISK") == "leakage_risk"
    assert normalize_review_category("Variance") == "variance"


def test_normalize_review_category_strips_whitespace():
    assert normalize_review_category("  data_quality  ") == "data_quality"
    assert normalize_review_category("  unknown  ") == "unknown"


def test_normalize_review_category_space_separated():
    assert normalize_review_category("data quality") == "data_quality"
    assert normalize_review_category("leakage risk") == "leakage_risk"


def test_normalize_review_category_hyphenated():
    assert normalize_review_category("data-quality") == "data_quality"
    assert normalize_review_category("model-calibration") == "model_calibration"


def test_normalize_review_category_unknown_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        normalize_review_category("match_result")


def test_normalize_review_category_empty_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        normalize_review_category("")


# --- normalize_review_severity ---

def test_normalize_review_severity_all_canonical_values():
    canonical = ["low", "medium", "high", "critical"]
    for severity in canonical:
        assert normalize_review_severity(severity) == severity


def test_normalize_review_severity_mixed_case():
    assert normalize_review_severity("LOW") == "low"
    assert normalize_review_severity("Critical") == "critical"
    assert normalize_review_severity("HIGH") == "high"


def test_normalize_review_severity_strips_whitespace():
    assert normalize_review_severity("  medium  ") == "medium"


def test_normalize_review_severity_unknown_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        normalize_review_severity("urgent")


def test_normalize_review_severity_empty_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        normalize_review_severity("")


# --- normalize_data_quality ---

def test_normalize_data_quality_all_canonical_values():
    canonical = ["strong", "okay", "weak", "unknown"]
    for quality in canonical:
        assert normalize_data_quality(quality) == quality


def test_normalize_data_quality_mixed_case():
    assert normalize_data_quality("STRONG") == "strong"
    assert normalize_data_quality("Okay") == "okay"
    assert normalize_data_quality("WEAK") == "weak"


def test_normalize_data_quality_strips_whitespace():
    assert normalize_data_quality("  strong  ") == "strong"


def test_normalize_data_quality_unknown_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        normalize_data_quality("good")


def test_normalize_data_quality_empty_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        normalize_data_quality("")


# --- validate_review_taxonomy ---

def test_validate_review_taxonomy_returns_exactly_three_keys():
    result = validate_review_taxonomy("data_quality", "high", "weak")
    assert set(result.keys()) == {"review_category", "severity", "data_quality"}


def test_validate_review_taxonomy_canonical_inputs():
    result = validate_review_taxonomy("data_quality", "high", "weak")
    assert result["review_category"] == "data_quality"
    assert result["severity"] == "high"
    assert result["data_quality"] == "weak"


def test_validate_review_taxonomy_normalizes_inputs():
    result = validate_review_taxonomy("Data-Quality", "HIGH", "Weak")
    assert result["review_category"] == "data_quality"
    assert result["severity"] == "high"
    assert result["data_quality"] == "weak"


def test_validate_review_taxonomy_invalid_category_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        validate_review_taxonomy("match_result", "low", "strong")


def test_validate_review_taxonomy_invalid_severity_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        validate_review_taxonomy("variance", "severe", "okay")


def test_validate_review_taxonomy_invalid_data_quality_raises():
    with pytest.raises(ReviewTaxonomyValidationError):
        validate_review_taxonomy("variance", "low", "excellent")


# --- leakage_risk label ---

def test_leakage_risk_is_valid_taxonomy_label():
    assert normalize_review_category("leakage_risk") == "leakage_risk"
    result = validate_review_taxonomy("leakage_risk", "high", "weak")
    assert result["review_category"] == "leakage_risk"
    assert result["severity"] == "high"
    assert result["data_quality"] == "weak"


# --- banned imports ---

def test_review_taxonomy_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "review_taxonomy.py"
    tree = ast.parse(src.read_text())
    banned = {"sqlite3", "database", "json", "subprocess", "pathlib"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
