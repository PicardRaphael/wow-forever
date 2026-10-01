"""`uv run tasks.py verify` compte l'étape `origins` (T08b, bloc H) : `scripts/check_origins.py`."""

import importlib.util
import sys

from conftest import REPO_ROOT


def load_tasks():
    spec = importlib.util.spec_from_file_location("tasks_module", REPO_ROOT / "tasks.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verify_runs_origins_step(monkeypatch):
    tasks = load_tasks()
    seen: list[list[str]] = []
    monkeypatch.setattr(tasks, "run", lambda cmd, ok_codes=(0,): seen.append(cmd) or True)
    assert tasks.verify()
    assert [sys.executable, "scripts/check_origins.py"] in seen
    assert "origins" in tasks.COMMANDS and "origins" in (tasks.__doc__ or "")


def test_check_origins_script_exists():
    assert (REPO_ROOT / "scripts" / "check_origins.py").is_file()
