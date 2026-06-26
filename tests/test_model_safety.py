import pytest

from model import feature_schema_hash, model_path_for_version, safe_model_tag, validate_feature_schema


def test_safe_model_tag_normalizes_version_strings():
    assert safe_model_tag("v0.1.8.1") == "v0_1_8_1"
    assert safe_model_tag("Home Win") == "home_win"


def test_model_path_for_version_is_versioned():
    path = model_path_for_version("0.1.8.1", "home_win")

    assert str(path).endswith("models/home_win_model_0_1_8_1.joblib")


def test_feature_schema_hash_is_stable_and_order_sensitive():
    assert feature_schema_hash(["a", "b"]) == feature_schema_hash(["a", "b"])
    assert feature_schema_hash(["a", "b"]) != feature_schema_hash(["b", "a"])


def test_validate_feature_schema_accepts_numeric_features():
    validate_feature_schema({"a": 1, "b": 2.5}, ["a", "b"])


def test_validate_feature_schema_rejects_missing_features():
    with pytest.raises(ValueError, match="Missing features"):
        validate_feature_schema({"a": 1}, ["a", "b"])


def test_validate_feature_schema_rejects_non_numeric_features():
    with pytest.raises(ValueError, match="Non-numeric features"):
        validate_feature_schema({"a": 1, "b": "bad"}, ["a", "b"])
