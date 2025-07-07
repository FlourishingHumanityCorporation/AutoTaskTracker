"""Pytest fixtures for full end-to-end (E2E) tests.

This sets up an *isolated* HOME directory so Pensieve (`memos`) stores its
SQLite DB and screenshots in a throw-away place.  All background processes
spawned by the test are recorded and torn down automatically.

The fixture intentionally avoids touching your real /Users/paulrohde/AutoTaskTracker.memos data.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Generator, Dict, List, Any

import pytest

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _spawn(cmd: list[str], *, env: dict[str, str], cwd: str | None = None) -> subprocess.Popen[str]:
    """Spawn a background process, inherit env, capture output to pipes."""
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def e2e_env() -> Generator[Dict[str, Any], None, None]:
    """Yield an isolated environment & process-tracker for E2E tests."""

    temp_home = Path(tempfile.mkdtemp(prefix="pensieve_e2e_"))
    # Memos will create /Users/paulrohde/AutoTaskTracker.memos inside this temp HOME.

    test_env = os.environ.copy()
    test_env["HOME"] = str(temp_home)
    # Streamlit picks its port; ensure deterministic for tests
    test_env.setdefault("STREAMLIT_SERVER_PORT", "8501")

    processes: List[subprocess.Popen[str]] = []

    try:
        # Get the correct memos path from venv
        venv_bin = Path(__file__).resolve().parent.parent.parent / "venv" / "bin"
        memos_cmd = str(venv_bin / "memos")
        
        # Quick init so sqlite DB exists before watcher starts
        subprocess.run([memos_cmd, "init"], env=test_env, check=True, text=True)

        # Enable and start watcher & serve in-process for isolation (no launchd)
        proc_watch = _spawn([memos_cmd, "watch"], env=test_env)
        processes.append(proc_watch)

        proc_serve = _spawn([memos_cmd, "serve"], env=test_env)
        processes.append(proc_serve)

        # Allow services to spin up
        time.sleep(3)

        yield {
            "home": temp_home,
            "env": test_env,
            "processes": processes,
        }
    finally:
        # Teardown: terminate children and remove temp HOME
        for p in processes:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        shutil.rmtree(temp_home, ignore_errors=True)
