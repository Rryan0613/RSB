import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLATE_PATH = ROOT / "data/input/slate.json"


def run_script(*args):
    return subprocess.run(
        [sys.executable, "src/run_slate.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_empty_slate_run_succeeds():
    original_slate = SLATE_PATH.read_text()
    try:
        SLATE_PATH.write_text(json.dumps({"matches": []}, indent=2))
        result = run_script()
    finally:
        SLATE_PATH.write_text(original_slate)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["run_summary"]["matches_analyzed"] == 0
    assert report["run_summary"]["data_quality_summary"]["overall_data_quality"] == "none"
    assert report["predictions"] == []
