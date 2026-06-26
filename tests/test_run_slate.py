import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_empty_slate_run_succeeds():
    result = subprocess.run(
        [sys.executable, "src/run_slate.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["run_summary"]["matches_analyzed"] == 0
    assert report["predictions"] == []
