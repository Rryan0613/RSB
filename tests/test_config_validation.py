import json
import pytest
from pathlib import Path

import paths
from config_validation import (
    ConfigValidationError,
    load_json_config,
    validate_bet_rules_config,
    validate_model_config,
    validate_required_keys,
    validate_sports_config,
)

VALID_MODEL_CONFIG = {
    "project": "worldcup-ai",
    "version": "0.1.8.4",
    "target_market": "home_win",
    "minimum_completed_matches_to_train": 20,
    "minimum_edge": 0.03,
    "simulation_seed": None,
}

VALID_SPORTS_CONFIG = {
    "active_sport": "worldcup",
    "sports": {
        "worldcup": {
            "label": "FIFA World Cup",
            "provider_sport_key": "soccer_fifa_world_cup",
        }
    },
}

VALID_BET_RULES_CONFIG = {
    "active_profile": "worldcup_default",
    "profiles": {
        "worldcup_default": {
            "allowed_markets": ["h2h"],
        }
    },
}


# --- load_json_config ---

def test_load_json_config_parses_valid_file(tmp_path):
    f = tmp_path / "cfg.json"
    f.write_text('{"key": "value"}')
    result = load_json_config(f)
    assert result == {"key": "value"}


def test_load_json_config_raises_on_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not valid json")
    with pytest.raises(ConfigValidationError, match="Invalid JSON"):
        load_json_config(f)


def test_load_json_config_raises_on_missing_file(tmp_path):
    f = tmp_path / "nonexistent.json"
    with pytest.raises(ConfigValidationError, match="Cannot read config file"):
        load_json_config(f)


# --- validate_required_keys ---

def test_validate_required_keys_passes_when_all_present():
    validate_required_keys({"a": 1, "b": 2}, ["a", "b"], "test_config")


def test_validate_required_keys_raises_with_missing_key_name():
    with pytest.raises(ConfigValidationError, match="missing required key: 'b'"):
        validate_required_keys({"a": 1}, ["a", "b"], "test_config")


# --- validate_model_config ---

def test_valid_model_config_passes():
    validate_model_config(VALID_MODEL_CONFIG)


def test_model_config_missing_required_key_raises_with_key_name():
    config = {k: v for k, v in VALID_MODEL_CONFIG.items() if k != "target_market"}
    with pytest.raises(ConfigValidationError, match="'target_market'"):
        validate_model_config(config)


def test_model_config_missing_version_raises():
    config = {k: v for k, v in VALID_MODEL_CONFIG.items() if k != "version"}
    with pytest.raises(ConfigValidationError, match="'version'"):
        validate_model_config(config)


def test_model_config_missing_minimum_edge_raises():
    config = {k: v for k, v in VALID_MODEL_CONFIG.items() if k != "minimum_edge"}
    with pytest.raises(ConfigValidationError, match="'minimum_edge'"):
        validate_model_config(config)


def test_model_config_wrong_type_project_raises_with_field_name():
    config = {**VALID_MODEL_CONFIG, "project": 123}
    with pytest.raises(ConfigValidationError, match="'project'"):
        validate_model_config(config)


def test_model_config_wrong_type_version_raises_with_field_name():
    config = {**VALID_MODEL_CONFIG, "version": 184}
    with pytest.raises(ConfigValidationError, match="'version'"):
        validate_model_config(config)


def test_model_config_wrong_type_minimum_completed_matches_raises():
    config = {**VALID_MODEL_CONFIG, "minimum_completed_matches_to_train": "twenty"}
    with pytest.raises(ConfigValidationError, match="'minimum_completed_matches_to_train'"):
        validate_model_config(config)


def test_model_config_bool_rejected_for_int_field():
    # bool is a subclass of int in Python; validation must reject it
    config = {**VALID_MODEL_CONFIG, "minimum_completed_matches_to_train": True}
    with pytest.raises(ConfigValidationError, match="'minimum_completed_matches_to_train'"):
        validate_model_config(config)


def test_model_config_wrong_type_minimum_edge_raises():
    config = {**VALID_MODEL_CONFIG, "minimum_edge": "high"}
    with pytest.raises(ConfigValidationError, match="'minimum_edge'"):
        validate_model_config(config)


def test_model_config_simulation_seed_none_passes():
    config = {**VALID_MODEL_CONFIG, "simulation_seed": None}
    validate_model_config(config)


def test_model_config_simulation_seed_int_passes():
    config = {**VALID_MODEL_CONFIG, "simulation_seed": 42}
    validate_model_config(config)


def test_model_config_simulation_seed_wrong_type_raises():
    config = {**VALID_MODEL_CONFIG, "simulation_seed": "random"}
    with pytest.raises(ConfigValidationError, match="'simulation_seed'"):
        validate_model_config(config)


# --- validate_sports_config ---

def test_valid_sports_config_passes():
    validate_sports_config(VALID_SPORTS_CONFIG)


def test_sports_config_missing_active_sport_raises():
    config = {k: v for k, v in VALID_SPORTS_CONFIG.items() if k != "active_sport"}
    with pytest.raises(ConfigValidationError, match="'active_sport'"):
        validate_sports_config(config)


def test_sports_config_missing_sports_raises():
    config = {k: v for k, v in VALID_SPORTS_CONFIG.items() if k != "sports"}
    with pytest.raises(ConfigValidationError, match="'sports'"):
        validate_sports_config(config)


def test_sports_config_wrong_type_active_sport_raises():
    config = {**VALID_SPORTS_CONFIG, "active_sport": 99}
    with pytest.raises(ConfigValidationError, match="'active_sport'"):
        validate_sports_config(config)


def test_sports_config_wrong_type_sports_raises():
    config = {**VALID_SPORTS_CONFIG, "sports": "worldcup"}
    with pytest.raises(ConfigValidationError, match="'sports'"):
        validate_sports_config(config)


# --- validate_bet_rules_config ---

def test_valid_bet_rules_config_passes():
    validate_bet_rules_config(VALID_BET_RULES_CONFIG)


def test_bet_rules_missing_active_profile_raises():
    config = {k: v for k, v in VALID_BET_RULES_CONFIG.items() if k != "active_profile"}
    with pytest.raises(ConfigValidationError, match="'active_profile'"):
        validate_bet_rules_config(config)


def test_bet_rules_missing_profiles_raises():
    config = {k: v for k, v in VALID_BET_RULES_CONFIG.items() if k != "profiles"}
    with pytest.raises(ConfigValidationError, match="'profiles'"):
        validate_bet_rules_config(config)


def test_bet_rules_wrong_type_active_profile_raises():
    config = {**VALID_BET_RULES_CONFIG, "active_profile": 0}
    with pytest.raises(ConfigValidationError, match="'active_profile'"):
        validate_bet_rules_config(config)


def test_bet_rules_wrong_type_profiles_raises():
    config = {**VALID_BET_RULES_CONFIG, "profiles": ["list", "not", "dict"]}
    with pytest.raises(ConfigValidationError, match="'profiles'"):
        validate_bet_rules_config(config)


# --- mutation safety ---

def test_validate_model_config_does_not_mutate():
    original = dict(VALID_MODEL_CONFIG)
    validate_model_config(dict(original))
    assert VALID_MODEL_CONFIG == original


def test_validate_sports_config_does_not_mutate():
    original = {"active_sport": "worldcup", "sports": {"worldcup": {}}}
    copy = dict(original)
    validate_sports_config(copy)
    assert original == {"active_sport": "worldcup", "sports": {"worldcup": {}}}


def test_validate_bet_rules_config_does_not_mutate():
    original = {"active_profile": "p", "profiles": {"p": {}}}
    copy = dict(original)
    validate_bet_rules_config(copy)
    assert original == {"active_profile": "p", "profiles": {"p": {}}}


# --- real config files pass validation ---

def test_real_model_config_passes_validation():
    config = load_json_config(paths.MODEL_CONFIG_PATH)
    validate_model_config(config)


def test_real_sports_config_passes_validation():
    config = load_json_config(paths.SPORTS_CONFIG_PATH)
    validate_sports_config(config)


def test_real_bet_rules_config_passes_validation():
    config = load_json_config(paths.BET_RULES_CONFIG_PATH)
    validate_bet_rules_config(config)
