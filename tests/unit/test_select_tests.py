"""Sélection des tests de `uv run tasks.py quick` et de la vérification des données du clone (`scripts/select_tests.py`).

Analyse statique seulement (imports, chaînes des fichiers de test, noms de `conftest.py`) : rien n'est lancé."""

import importlib.util

import pytest
from conftest import REPO_ROOT

from forever.engine_inputs import ENGINES


@pytest.fixture(scope="module")
def sel():
    spec = importlib.util.spec_from_file_location("select_tests", REPO_ROOT / "scripts" / "select_tests.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def index(sel):
    return sel.TestIndex(REPO_ROOT)


def picked(sel, index, *changed):
    selection = sel.select(list(changed), index)
    assert selection.files is not None, selection.reasons
    return set(selection.files)


def test_a_changed_test_file_selects_itself(sel, index):
    assert picked(sel, index, "tests/unit/test_cbor.py") == {"tests/unit/test_cbor.py"}


def test_a_deleted_test_file_selects_nothing(sel, index):
    assert picked(sel, index, "tests/unit/test_supprime_depuis.py") == set()


def test_a_module_selects_the_tests_that_import_it(sel, index):
    files = picked(sel, index, "forever/pipeline/gitops.py")
    assert "tests/unit/test_gitops.py" in files
    assert "tests/unit/test_update_publish.py" in files  # par forever.update, qui importe gitops
    assert "tests/unit/test_engine_armor.py" not in files


def test_a_lazy_import_counts(sel, index):
    """Import dans une fonction (`from forever.pipeline.verify import verify_version` dans update.py)."""
    assert "tests/unit/test_update_publish.py" in picked(sel, index, "forever/pipeline/verify.py")


def test_a_conftest_helper_brings_its_imports(sel, index):
    """`game_data` (fixture de conftest) importe `forever.gamedata` dans son corps ; test_cooldown_period ne l'importe
    pas lui-même."""
    assert "tests/unit/test_cooldown_period.py" in picked(sel, index, "forever/gamedata.py")


def test_shared_test_files_fall_back_to_the_fast_suite(sel, index):
    for path in ("tests/conftest.py", "pyproject.toml", "uv.lock", "tasks.py", "scripts/select_tests.py"):
        selection = sel.select([path], index)
        assert selection.files is None, path
        assert any(path in r for r in selection.reasons)


def test_research_notes_select_nothing(sel, index):
    assert picked(sel, index, "docs/research/une-note.md", "tasks/T99-plan.md") == set()


def test_a_data_file_selects_the_tests_that_name_it(sel, index):
    files = picked(sel, index, "docs/MECHANICS_REGISTRY.yaml")
    assert "tests/unit/test_registry.py" in files  # REGISTRY_PATH de conftest


def test_a_fixture_selects_the_tests_of_its_folder(sel, index):
    files = picked(sel, index, "tests/fixtures/combatlog/synthetic/un-journal.txt")
    assert "tests/unit/test_combatlog.py" in files
    assert "tests/unit/test_gitops.py" not in files


def test_a_script_selects_the_tests_that_name_it(sel, index):
    assert "tests/unit/test_tasks_verify.py" in picked(sel, index, "scripts/check_origins.py")


def test_installed_data_fall_back_to_the_fast_suite(sel, index):
    assert sel.select(["forever/data/manifest.json"], index).files is None


def test_engine_tests_follow_the_declared_engines(sel, index):
    assert set(sel.ENGINE_MODULES) == set(ENGINES)
    for engine in ENGINES:
        files = sel.engine_tests(index, [engine])
        assert files, engine
    assert "tests/unit/test_pvp_sheets.py" in sel.engine_tests(index, ["pvp_dr"])
    assert "tests/unit/test_pvp_sheets.py" not in sel.engine_tests(index, ["mage_leveling"])
    assert sel.engine_tests(index, []) == []


def test_data_tests_exist(sel):
    for path in sel.DATA_TESTS:
        assert (REPO_ROOT / path).is_file(), path


def test_data_only_paths(sel):
    assert sel.data_only(["forever/data/1.60.1.70245/spells.json", "docs/research/data-1.60.1.70246-r1.md"])
    assert not sel.data_only(["forever/data/manifest.json", "forever/update.py"])
    assert not sel.data_only([])
