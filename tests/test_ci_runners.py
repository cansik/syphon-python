"""CI must reject a test interpreter that does not match its matrix entry."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wrong_python_version_fails_before_collection():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "tests/test_runtime.py"), "--python-version", "0.0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 1
    assert "Expected Python 0.0, but selected Python" in result.stdout + result.stderr
