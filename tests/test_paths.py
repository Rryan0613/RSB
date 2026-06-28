import subprocess
import sys
from pathlib import Path

import paths
from paths import get_db_path, get_slate_path, get_model_output_path, get_results_path

ROOT = Path(__file__).resolve().parents[1]
SLATE_PATH = ROOT / "data/input/slate.json"


def test_project_root_is_repo_root():
    assert paths.PROJECT_ROOT == ROOT


def test_all_path_constants_are_absolute():
    constants = [
        paths.PROJECT_ROOT,
        paths.CONFIG_DIR,
        paths.DATA_DIR,
        paths.DATA_INPUT_DIR,
        paths.DATA_OUTPUT_DIR,
        paths.MODELS_DIR,
        paths.MODEL_CONFIG_PATH,
        paths.SPORTS_CONFIG_PATH,
        paths.BET_RULES_CONFIG_PATH,
        paths.DEFAULT_DB_PATH,
        paths.DEFAULT_SLATE_PATH,
        paths.DEFAULT_RESULTS_PATH,
        paths.DEFAULT_MODEL_OUTPUT_PATH,
        paths.DEFAULT_ODDS_OUTPUT_PATH,
        paths.DEFAULT_PROVIDER_DIAGNOSTICS_PATH,
        paths.DEFAULT_CLAUDE_REVIEW_PATH,
    ]
    for p in constants:
        assert p.is_absolute(), f"{p} is not absolute"


def test_key_paths_point_to_expected_locations():
    assert paths.MODEL_CONFIG_PATH == ROOT / "config" / "model_config.json"
    assert paths.SPORTS_CONFIG_PATH == ROOT / "config" / "sports_config.json"
    assert paths.BET_RULES_CONFIG_PATH == ROOT / "config" / "bet_rules_config.json"
    assert paths.DEFAULT_DB_PATH == ROOT / "data" / "worldcup_ai.db"
    assert paths.DEFAULT_SLATE_PATH == ROOT / "data" / "input" / "slate.json"
    assert paths.DEFAULT_RESULTS_PATH == ROOT / "data" / "input" / "results.json"
    assert paths.DEFAULT_MODEL_OUTPUT_PATH == ROOT / "data" / "output" / "latest_model_output.json"
    assert paths.DEFAULT_ODDS_OUTPUT_PATH == ROOT / "data" / "output" / "latest_odds_output.json"
    assert paths.DEFAULT_PROVIDER_DIAGNOSTICS_PATH == ROOT / "data" / "output" / "latest_provider_diagnostics.json"
    assert paths.DEFAULT_CLAUDE_REVIEW_PATH == ROOT / "data" / "input" / "claude_review.json"
    assert paths.MODELS_DIR == ROOT / "models"


def test_config_files_exist_at_resolved_paths():
    assert paths.MODEL_CONFIG_PATH.exists()
    assert paths.SPORTS_CONFIG_PATH.exists()
    assert paths.BET_RULES_CONFIG_PATH.exists()


def test_run_slate_module_loads_from_outside_project_root(tmp_path):
    """Importing run_slate from an external cwd resolves config via paths.py, not cwd.

    This test does NOT call main(), init_db(), or write to any project file.
    It only imports run_slate at module level (which reads model_config.json) and
    asserts that path constants and the loaded version are correct.
    """
    db_path = ROOT / "data" / "worldcup_ai.db"
    output_path = ROOT / "data" / "output" / "latest_model_output.json"

    slate_before = SLATE_PATH.read_text()
    db_mtime_before = db_path.stat().st_mtime if db_path.exists() else None
    output_mtime_before = output_path.stat().st_mtime if output_path.exists() else None

    src = str(ROOT / "src")
    cmd = (
        f"import sys; sys.path.insert(0, {src!r}); "
        f"import run_slate; "
        f"from paths import MODEL_CONFIG_PATH, DEFAULT_SLATE_PATH, DEFAULT_MODEL_OUTPUT_PATH, DEFAULT_DB_PATH; "
        f"assert run_slate.MODEL_VERSION == '0.1.9.4', run_slate.MODEL_VERSION; "
        f"assert MODEL_CONFIG_PATH.is_absolute(); "
        f"assert DEFAULT_SLATE_PATH.is_absolute(); "
        f"assert DEFAULT_MODEL_OUTPUT_PATH.is_absolute(); "
        f"assert DEFAULT_DB_PATH.is_absolute(); "
        f"assert MODEL_CONFIG_PATH.exists(), str(MODEL_CONFIG_PATH); "
        f"assert DEFAULT_SLATE_PATH.exists(), str(DEFAULT_SLATE_PATH); "
    )
    result = subprocess.run(
        [sys.executable, "-c", cmd],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    assert SLATE_PATH.read_text() == slate_before, "slate.json was modified"
    db_mtime_after = db_path.stat().st_mtime if db_path.exists() else None
    output_mtime_after = output_path.stat().st_mtime if output_path.exists() else None
    assert db_mtime_after == db_mtime_before, "data/worldcup_ai.db was written"
    assert output_mtime_after == output_mtime_before, "data/output/latest_model_output.json was written"


def test_default_paths_point_to_project_root_files():
    assert get_db_path() == ROOT / "data" / "worldcup_ai.db"
    assert get_slate_path() == ROOT / "data" / "input" / "slate.json"
    assert get_model_output_path() == ROOT / "data" / "output" / "latest_model_output.json"


def test_rsb_db_path_env_overrides_db_path(tmp_path, monkeypatch):
    override = tmp_path / "override.db"
    monkeypatch.setenv("RSB_DB_PATH", str(override))
    assert get_db_path() == override


def test_rsb_slate_path_env_overrides_slate_path(tmp_path, monkeypatch):
    override = tmp_path / "override_slate.json"
    monkeypatch.setenv("RSB_SLATE_PATH", str(override))
    assert get_slate_path() == override


def test_rsb_model_output_path_env_overrides_model_output_path(tmp_path, monkeypatch):
    override = tmp_path / "override_output.json"
    monkeypatch.setenv("RSB_MODEL_OUTPUT_PATH", str(override))
    assert get_model_output_path() == override


def test_default_results_path_returns_project_root_file():
    assert get_results_path() == ROOT / "data" / "input" / "results.json"


def test_rsb_results_path_env_overrides_results_path(tmp_path, monkeypatch):
    override = tmp_path / "override_results.json"
    monkeypatch.setenv("RSB_RESULTS_PATH", str(override))
    assert get_results_path() == override
