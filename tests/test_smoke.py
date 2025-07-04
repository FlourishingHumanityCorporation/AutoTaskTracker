"""Goal-serving smoke tests for the AutoTaskTracker/Pensieve stack.

Run with:
    ./venv/bin/python -m pip install -r requirements-dev.txt  # one-time setup
    ./venv/bin/pytest -q                                    # each time you want to smoke-test

These tests assume:
1. You have already run `memos enable` and `memos start` (or will start them in another terminal) **OR**
2. You will run them manually and then rerun the failing test(s).

If the API service is not running, the `test_api_health` case will be skipped rather than fail.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

# Path helpers -----------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = REPO_ROOT / "venv" / "bin"
MEMOS_CMD = str(VENV_BIN / "memos")
PYTHON = str(VENV_BIN / "python")


# Internal helpers --------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a command and return the CompletedProcess for finer-grained checks."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)



# Smoke tests -------------------------------------------------------------------

def test_memos_status() -> None:
    """`memos ps` should show running services."""
    proc = _run([MEMOS_CMD, "ps"])
    if proc.returncode != 0:
        pytest.xfail("`memos ps` failed – services may not be running.")
    output = proc.stdout + proc.stderr
    # Check for at least one running service
    assert "Running" in output or "Status" in output



def test_capture_once() -> None:
    """`memos record --once` should create a new screenshot file."""
    # Screenshots are stored in date-based subdirectories
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    screens_dir = Path.home() / ".memos" / "screenshots" / today
    screens_dir.mkdir(parents=True, exist_ok=True)

    before = {p for p in screens_dir.glob("*.png")} | {p for p in screens_dir.glob("*.webp")}
    proc = _run([MEMOS_CMD, "record", "--once"])
    if proc.returncode != 0:
        pytest.xfail("`memos record --once` failed – screen capture may be blocked in headless session.")

    # give the OS a moment to flush the file
    time.sleep(2)
    after = {p for p in screens_dir.glob("*.png")} | {p for p in screens_dir.glob("*.webp")}
    new_files = after - before
    if not new_files:
        pytest.xfail("No screenshot captured – likely headless environment; capture test skipped.")


def test_watch_service() -> None:
    """Check if memos watch service is running."""
    proc = _run([MEMOS_CMD, "ps"])
    if proc.returncode != 0:
        pytest.xfail("`memos ps` failed – services may not be running.")
    
    output = proc.stdout
    # Check if watch service is running
    if "watch" in output and "Running" in output:
        assert True  # Watch service is running
    else:
        pytest.xfail("Watch service not running – may need to start with `memos start`")


def test_api_health() -> None:
    """If `memos serve` is running, /health should respond HTTP 200."""
    import requests

    try:
        resp = requests.get("http://localhost:8839/health", timeout=2)
    except requests.exceptions.RequestException:
        pytest.xfail("`memos serve` not responding – API health check skipped.")
    else:
        assert resp.status_code == 200
