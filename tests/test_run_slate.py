import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_DB_PATH = ROOT / "data/worldcup_ai.db"
REAL_SLATE_PATH = ROOT / "data/input/slate.json"
REAL_OUTPUT_PATH = ROOT / "data/output/latest_model_output.json"


def _run_script(tmp_path, *args):
    tmp_db = tmp_path / "test.db"
    tmp_slate = tmp_path / "slate.json"
    tmp_output = tmp_path / "model_output.json"
    tmp_slate.write_text(json.dumps({"matches": []}, indent=2))
    env = {
        **os.environ,
        "RSB_DB_PATH": str(tmp_db),
        "RSB_SLATE_PATH": str(tmp_slate),
        "RSB_MODEL_OUTPUT_PATH": str(tmp_output),
    }
    return subprocess.run(
        [sys.executable, "src/run_slate.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    ), tmp_db, tmp_output


def _real_file_mtimes():
    return {
        "db": REAL_DB_PATH.stat().st_mtime if REAL_DB_PATH.exists() else None,
        "output": REAL_OUTPUT_PATH.stat().st_mtime if REAL_OUTPUT_PATH.exists() else None,
        "slate": REAL_SLATE_PATH.stat().st_mtime if REAL_SLATE_PATH.exists() else None,
    }


def test_empty_slate_run_succeeds(tmp_path):
    before = _real_file_mtimes()
    result, tmp_db, tmp_output = _run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["run_summary"]["matches_analyzed"] == 0
    assert report["run_summary"]["data_quality_summary"]["overall_data_quality"] == "none"
    assert report["predictions"] == []

    after = _real_file_mtimes()
    assert after["db"] == before["db"], "data/worldcup_ai.db was modified"
    assert after["output"] == before["output"], "data/output/latest_model_output.json was modified"
    assert after["slate"] == before["slate"], "data/input/slate.json was modified"

    assert tmp_db.exists(), "subprocess did not create tmp DB"
    assert tmp_output.exists(), "subprocess did not write tmp model output"
