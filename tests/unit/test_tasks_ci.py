"""`uv run tasks.py ci [--base=<rev>]` : la CI teste ce qui a changé depuis `base` (lents compris), la suite complète
sans base valable ou quand la sélection le demande (données, fichier partagé) ; `e2e --base` saute si le bout en bout
n'est pas concerné."""

import importlib.util
import sys
from types import SimpleNamespace

import pytest
from conftest import REPO_ROOT

E2E = "tests/e2e/test_update_e2e.py"


def load_tasks():
    spec = importlib.util.spec_from_file_location("tasks_ci_module", REPO_ROOT / "tasks.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tasks(monkeypatch):
    module = load_tasks()
    module.calls = []
    monkeypatch.setattr(module, "run", lambda cmd, ok_codes=(0,): module.calls.append(cmd) or True)
    monkeypatch.setattr(module, "_commit_exists", lambda rev: rev == "base-ok")
    return module


def selecting(monkeypatch, tasks, files):
    seen = {}

    def changed_since(base, root):
        seen["base"] = base
        return ["un/chemin.py"]

    fake = SimpleNamespace(
        changed_since=changed_since,
        TestIndex=lambda root: None,
        select=lambda changed, index: SimpleNamespace(files=files, reasons=[]),
    )
    monkeypatch.setattr(tasks, "_selector", lambda: fake)
    return seen


def pytest_calls(tasks):
    return [c for c in tasks.calls if c[1:3] == ["-m", "pytest"]]


def test_ci_without_base_runs_the_full_suite(tasks):
    assert tasks.ci(None)
    (call,) = pytest_calls(tasks)
    assert "not slow" not in call and not [a for a in call if a.startswith("tests/")]
    assert [sys.executable, "scripts/check_origins.py"] in tasks.calls


def test_ci_with_unknown_base_runs_the_full_suite(tasks, monkeypatch):
    selecting(monkeypatch, tasks, ["tests/unit/test_a.py"])
    assert tasks.ci("base-inconnue")
    (call,) = pytest_calls(tasks)
    assert "tests/unit/test_a.py" not in call


def test_ci_with_base_runs_the_selected_tests_slow_ones_included(tasks, monkeypatch):
    seen = selecting(monkeypatch, tasks, ["tests/unit/test_a.py", "tests/unit/test_b.py"])
    assert tasks.ci("base-ok")
    assert seen["base"] == "base-ok"
    (call,) = pytest_calls(tasks)
    assert call[-2:] == ["tests/unit/test_a.py", "tests/unit/test_b.py"] and "not slow" not in call
    for check in ("check_registry.py", "check_game_numbers.py", "check_origins.py"):
        assert any(check in " ".join(c) for c in tasks.calls)


def test_ci_with_base_and_shared_change_runs_the_full_suite(tasks, monkeypatch):
    selecting(monkeypatch, tasks, None)
    assert tasks.ci("base-ok")
    (call,) = pytest_calls(tasks)
    assert not [a for a in call if a.startswith("tests/")]


def test_ci_with_base_and_nothing_concerned_runs_no_test_but_the_checks(tasks, monkeypatch):
    selecting(monkeypatch, tasks, [])
    assert tasks.ci("base-ok")
    assert pytest_calls(tasks) == []
    assert any("ruff" in c for c in tasks.calls) and any("mypy" in c for c in tasks.calls)


def test_e2e_is_skipped_when_not_concerned(tasks, monkeypatch):
    selecting(monkeypatch, tasks, ["tests/unit/test_a.py"])
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **k: pytest.fail("e2e lancé"))
    assert tasks.e2e("base-ok")


@pytest.mark.parametrize("files", [[E2E], None])
def test_e2e_runs_when_concerned_or_without_selection(tasks, monkeypatch, files):
    selecting(monkeypatch, tasks, files)
    ran = []
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **k: ran.append(a) or SimpleNamespace(returncode=0))
    assert tasks.e2e("base-ok")
    assert ran


def test_e2e_runs_without_base(tasks, monkeypatch):
    ran = []
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **k: ran.append(a) or SimpleNamespace(returncode=0))
    assert tasks.e2e(None)
    assert ran


def test_ci_command_and_base_option(tasks, monkeypatch):
    got = []
    monkeypatch.setattr(tasks, "ci", lambda base=None: got.append(base) or True)
    assert tasks.main(["ci", "--base=base-ok"]) == 0
    assert tasks.main(["ci"]) == 0
    assert got == ["base-ok", None]
    assert "ci" in tasks.COMMANDS and "ci " in (tasks.__doc__ or "")


def test_ci_workflow_passes_a_base_and_runs_nightly():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tasks.py ci" in workflow and "--base=" in workflow
    assert "schedule:" in workflow and "fetch-depth: 0" in workflow
    assert "ubuntu" in workflow and "windows" in workflow
