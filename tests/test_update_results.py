import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_DB_PATH = ROOT / "data/worldcup_ai.db"
REAL_RESULTS_PATH = ROOT / "data/input/results.json"


def _run_update_results(tmp_path, results_data):
    tmp_db = tmp_path / "test.db"
    tmp_results = tmp_path / "results.json"
    tmp_results.write_text(json.dumps(results_data))
    env = {
        **os.environ,
        "RSB_DB_PATH": str(tmp_db),
        "RSB_RESULTS_PATH": str(tmp_results),
    }
    proc = subprocess.run(
        [sys.executable, "src/update_results.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc, tmp_db, tmp_results


def _real_mtimes():
    return {
        "db": REAL_DB_PATH.stat().st_mtime if REAL_DB_PATH.exists() else None,
        "results": REAL_RESULTS_PATH.stat().st_mtime if REAL_RESULTS_PATH.exists() else None,
    }


def test_update_results_empty_list_succeeds(tmp_path):
    before = _real_mtimes()
    proc, tmp_db, _ = _run_update_results(tmp_path, {"results": []})

    assert proc.returncode == 0, proc.stderr
    assert "Saved 0 results." in proc.stdout

    after = _real_mtimes()
    assert after["db"] == before["db"], "data/worldcup_ai.db was modified"
    assert after["results"] == before["results"], "data/input/results.json was modified"
    assert tmp_db.exists(), "subprocess did not create tmp DB"


def test_update_results_with_one_result(tmp_path):
    results_data = {
        "results": [
            {"match_id": "test_001", "home_score": 2, "away_score": 1}
        ]
    }
    before = _real_mtimes()
    proc, tmp_db, _ = _run_update_results(tmp_path, results_data)

    assert proc.returncode == 0, proc.stderr
    assert "Saved 1 results." in proc.stdout

    after = _real_mtimes()
    assert after["db"] == before["db"], "data/worldcup_ai.db was modified"
    assert after["results"] == before["results"], "data/input/results.json was modified"
    assert tmp_db.exists(), "subprocess did not create tmp DB"
