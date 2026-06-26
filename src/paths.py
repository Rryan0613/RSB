from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
DATA_INPUT_DIR = DATA_DIR / "input"
DATA_OUTPUT_DIR = DATA_DIR / "output"
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
