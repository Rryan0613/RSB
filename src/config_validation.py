import json
from pathlib import Path


class ConfigValidationError(Exception):
    pass


def load_json_config(path: Path) -> dict:
    try:
        text = path.read_text()
    except OSError as e:
        raise ConfigValidationError(f"Cannot read config file '{path}': {e}") from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Invalid JSON in '{path}': {e}") from e


def validate_required_keys(config: dict, required_keys: list, config_name: str) -> None:
    for key in required_keys:
        if key not in config:
            raise ConfigValidationError(
                f"'{config_name}' is missing required key: '{key}'"
            )


def validate_model_config(config: dict) -> None:
    name = "model_config"
    validate_required_keys(
        config,
        ["project", "version", "target_market", "minimum_completed_matches_to_train",
         "minimum_edge", "simulation_seed"],
        name,
    )

    str_fields = ["project", "version", "target_market"]
    for field in str_fields:
        val = config[field]
        if not isinstance(val, str):
            raise ConfigValidationError(
                f"'{name}' field '{field}' must be str, got {type(val).__name__}"
            )

    int_field = "minimum_completed_matches_to_train"
    val = config[int_field]
    if isinstance(val, bool) or not isinstance(val, int):
        raise ConfigValidationError(
            f"'{name}' field '{int_field}' must be int, got {type(val).__name__}"
        )

    edge_val = config["minimum_edge"]
    if isinstance(edge_val, bool) or not isinstance(edge_val, (int, float)):
        raise ConfigValidationError(
            f"'{name}' field 'minimum_edge' must be a number, got {type(edge_val).__name__}"
        )

    seed_val = config["simulation_seed"]
    if seed_val is not None and (isinstance(seed_val, bool) or not isinstance(seed_val, int)):
        raise ConfigValidationError(
            f"'{name}' field 'simulation_seed' must be int or null, got {type(seed_val).__name__}"
        )


def validate_sports_config(config: dict) -> None:
    name = "sports_config"
    validate_required_keys(config, ["active_sport", "sports"], name)

    if not isinstance(config["active_sport"], str):
        raise ConfigValidationError(
            f"'{name}' field 'active_sport' must be str, got {type(config['active_sport']).__name__}"
        )
    if not isinstance(config["sports"], dict):
        raise ConfigValidationError(
            f"'{name}' field 'sports' must be dict, got {type(config['sports']).__name__}"
        )


def validate_bet_rules_config(config: dict) -> None:
    name = "bet_rules_config"
    validate_required_keys(config, ["active_profile", "profiles"], name)

    if not isinstance(config["active_profile"], str):
        raise ConfigValidationError(
            f"'{name}' field 'active_profile' must be str, got {type(config['active_profile']).__name__}"
        )
    if not isinstance(config["profiles"], dict):
        raise ConfigValidationError(
            f"'{name}' field 'profiles' must be dict, got {type(config['profiles']).__name__}"
        )
