"""Trois niveaux de contrôle de `tasks.py` : `quick` pendant le travail, `verify` (suite complète en parallèle) avant le
push, `verify --data` dans le clone de `forever update` quand seules les données changent. Commandes simulées."""

import sys

import pytest
from test_tasks_verify import load_tasks

PY = sys.executable


@pytest.fixture
def tasks(monkeypatch):
    module = load_tasks()
    seen: list[list[str]] = []
    monkeypatch.setattr(module, "run", lambda cmd, ok_codes=(0,): seen.append(cmd) or True)
    module.seen = seen
    return module


def pytest_calls(tasks):
    return [c for c in tasks.seen if c[:3] == [PY, "-m", "pytest"]]


def test_verify_runs_the_whole_suite_in_parallel(tasks):
    assert tasks.verify()
    (call,) = pytest_calls(tasks)
    assert call[call.index("-n") + 1] == "auto"
    assert "not slow" not in call  # tests lents compris
    for script in ("scripts/check_registry.py", "scripts/check_game_numbers.py", "scripts/check_origins.py"):
        assert any(script in c for c in tasks.seen), script


def test_quick_runs_lint_types_and_the_selected_fast_tests(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "quick_selection", lambda: (["tests/unit/test_cbor.py"], ["test_cbor modifié"]))
    assert tasks.quick()
    assert [PY, "-m", "ruff", "check", "."] in tasks.seen
    assert [PY, "-m", "mypy", "forever"] in tasks.seen
    (call,) = pytest_calls(tasks)
    assert call[call.index("-m", 3) + 1] == "not slow"
    assert call[-1] == "tests/unit/test_cbor.py"


def test_quick_falls_back_to_the_fast_suite(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "quick_selection", lambda: (None, ["conftest.py modifié"]))
    assert tasks.quick()
    (call,) = pytest_calls(tasks)
    assert call[call.index("-m", 3) + 1] == "not slow"
    assert "tests" in call and "-n" in call


def test_quick_without_concerned_tests_runs_no_test(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "quick_selection", lambda: ([], ["docs/research/note.md : aucun test"]))
    assert tasks.quick()
    assert pytest_calls(tasks) == []
    assert [PY, "-m", "ruff", "check", "."] in tasks.seen


def test_data_verify_checks_the_data_and_the_changed_engines_only(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "uncommitted_paths", lambda: ["forever/data/1.60.1.70246/spells.json"])
    assert tasks.verify(data=True, engines=["pvp_dr"])
    for script in ("scripts/check_registry.py", "scripts/check_game_numbers.py", "scripts/check_origins.py"):
        assert any(script in c for c in tasks.seen), script
    assert [PY, "-m", "forever.cli", "verify"] in tasks.seen  # intégrité de la version installée
    (call,) = pytest_calls(tasks)
    assert "tests/unit/test_pvp_sheets.py" in call
    assert "tests/unit/test_manifest.py" in call
    assert "tests" not in call and "tests/unit/test_sim_leveling.py" not in call


def test_data_verify_without_changed_engine_runs_the_data_tests(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "uncommitted_paths", lambda: ["forever/data/1.60.1.70246/spells.json"])
    assert tasks.verify(data=True, engines=[])
    (call,) = pytest_calls(tasks)
    assert "tests/unit/test_manifest.py" in call and "tests/unit/test_pvp_sheets.py" not in call


def test_data_verify_without_engine_list_runs_every_engine(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "uncommitted_paths", lambda: ["forever/data/1.60.1.70246/spells.json"])
    assert tasks.verify(data=True, engines=None)
    (call,) = pytest_calls(tasks)
    assert "tests/unit/test_pvp_sheets.py" in call and "tests/unit/test_sim_leveling.py" in call


def test_data_verify_falls_back_to_the_full_verify_when_code_changed(tasks, monkeypatch):
    monkeypatch.setattr(tasks, "uncommitted_paths", lambda: ["forever/data/x.json", "forever/update.py"])
    assert tasks.verify(data=True, engines=[])
    (call,) = pytest_calls(tasks)
    assert "tests/unit/test_manifest.py" not in call and "-n" in call and "not slow" not in call


def test_command_line_parsing(tasks, monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, "verify", lambda data=False, engines=None: calls.append((data, engines)) or True)
    assert tasks.main(["verify"]) == 0
    assert tasks.main(["verify", "--data", "--engines=pvp_dr,mage_build"]) == 0
    assert tasks.main(["verify", "--data", "--engines="]) == 0
    assert tasks.main(["verify", "--data"]) == 0
    assert calls == [(False, None), (True, ["pvp_dr", "mage_build"]), (True, []), (True, None)]
    assert tasks.main(["inconnue"]) == 2
    assert "quick" in tasks.COMMANDS and "quick" in (tasks.__doc__ or "")
