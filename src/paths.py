import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
DATA_INPUT_DIR = DATA_DIR / "input"
DATA_OUTPUT_DIR = DATA_DIR / "output"
DATA_MLB_DIR = DATA_DIR / "mlb"
MODELS_DIR = PROJECT_ROOT / "models"

MODEL_CONFIG_PATH = CONFIG_DIR / "model_config.json"
SPORTS_CONFIG_PATH = CONFIG_DIR / "sports_config.json"
BET_RULES_CONFIG_PATH = CONFIG_DIR / "bet_rules_config.json"

DEFAULT_DB_PATH = DATA_DIR / "worldcup_ai.db"
DEFAULT_SLATE_PATH = DATA_INPUT_DIR / "slate.json"
DEFAULT_RESULTS_PATH = DATA_INPUT_DIR / "results.json"
DEFAULT_MODEL_OUTPUT_PATH = DATA_OUTPUT_DIR / "latest_model_output.json"
DEFAULT_ODDS_OUTPUT_PATH = DATA_OUTPUT_DIR / "latest_odds_output.json"
DEFAULT_PROVIDER_DIAGNOSTICS_PATH = DATA_OUTPUT_DIR / "latest_provider_diagnostics.json"
DEFAULT_CLAUDE_REVIEW_PATH = DATA_INPUT_DIR / "claude_review.json"


def get_db_path() -> Path:
    override = os.environ.get("RSB_DB_PATH")
    return Path(override) if override else DEFAULT_DB_PATH


def get_slate_path() -> Path:
    override = os.environ.get("RSB_SLATE_PATH")
    return Path(override) if override else DEFAULT_SLATE_PATH


def get_model_output_path() -> Path:
    override = os.environ.get("RSB_MODEL_OUTPUT_PATH")
    return Path(override) if override else DEFAULT_MODEL_OUTPUT_PATH


def get_results_path() -> Path:
    override = os.environ.get("RSB_RESULTS_PATH")
    return Path(override) if override else DEFAULT_RESULTS_PATH


def get_mlb_data_dir() -> Path:
    override = os.environ.get("RSB_MLB_DATA_DIR")
    return Path(override) if override else DATA_MLB_DIR


def get_mlb_manual_input_dir() -> Path:
    return get_mlb_data_dir() / "manual_input"


def get_mlb_raw_statcast_dir() -> Path:
    return get_mlb_data_dir() / "raw" / "statcast"


def get_mlb_normalized_statcast_pitch_dir() -> Path:
    return get_mlb_data_dir() / "normalized" / "statcast_pitch"


def get_mlb_snapshot_dir() -> Path:
    return get_mlb_data_dir() / "snapshots"
