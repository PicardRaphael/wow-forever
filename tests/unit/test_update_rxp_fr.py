"""FR1 : la veille (`forever update`, étape `addons`) régénère les guides français quand le marqueur FR1 manque ou
que la source anglaise a changé, ne fait rien sinon, n'écrit rien en `--dry-run`, et laisse une fiche « Mis à jour »
que `forever update undo <id>` défait.

Valeurs : mini-addon inventé pour le test (`tests/fixtures/rxp_fr/`)."""

import shutil
from pathlib import Path

from forever.rxp_fr.build import MARKER
from forever.update import UpdateOptions, run_update, undo
from forever.update_installed import list_installed

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr"
REL = Path("Interface/AddOns/RXPGuides/lang/Guides-frFR/forever/Test-Isle.lua")
EN_REL = Path("Interface/AddOns/RXPGuides/Guides/Forever/Test-Isle.lua")
ONLY = UpdateOptions(only=frozenset({"addons"}), network=False)


def _setup(make_deps, tmp_path):
    wow = tmp_path / "wow"
    shutil.copytree(FIX / "AddOns", wow / "Interface" / "AddOns")
    shutil.copytree(FIX / "wago", tmp_path / "cache" / "wago" / "1.0.0.1")
    return make_deps(wow_dir=wow), wow


def _step(report):
    (found,) = [s for s in report["steps"] if s["name"] == "addons"]
    return found


def test_the_pass_generates_when_the_marker_is_missing_then_does_nothing(make_deps, tmp_path):
    deps, wow = _setup(make_deps, tmp_path)
    first = run_update(deps, ONLY)
    assert MARKER in (wow / REL).read_bytes().decode("utf-8")
    assert "guides RestedXP en français" in _step(first)["detail"]
    (record,) = [r for r in list_installed(deps.cache_dir) if r.get("kind") == "rxp_fr"]
    assert record["state"] == "installée" and record["undo"].startswith("forever update undo ")
    second = run_update(deps, ONLY)
    assert "guides RestedXP en français" not in _step(second)["detail"]
    assert len([r for r in list_installed(deps.cache_dir) if r.get("kind") == "rxp_fr"]) == 1


def test_a_changed_english_source_is_regenerated(make_deps, tmp_path):
    deps, wow = _setup(make_deps, tmp_path)
    run_update(deps, ONLY)
    en = wow / EN_REL
    en.write_bytes(en.read_bytes().replace(b"Train |T135846:0|t[Frost Spark]", b"Learn |T135846:0|t[Frost Spark]"))
    again = run_update(deps, ONLY)
    assert "guides RestedXP en français" in _step(again)["detail"]
    assert len([r for r in list_installed(deps.cache_dir) if r.get("kind") == "rxp_fr"]) == 2


def test_dry_run_writes_nothing(make_deps, tmp_path):
    deps, wow = _setup(make_deps, tmp_path)
    before = (wow / REL).read_bytes()
    run_update(deps, UpdateOptions(only=frozenset({"addons"}), network=False, dry_run=True))
    assert (wow / REL).read_bytes() == before


def test_undo_puts_back_the_previous_file(make_deps, tmp_path):
    deps, wow = _setup(make_deps, tmp_path)
    before = (wow / REL).read_bytes()
    run_update(deps, ONLY)
    (record,) = [r for r in list_installed(deps.cache_dir) if r.get("kind") == "rxp_fr"]
    out = undo(deps, record["id"])
    assert out["state"] == "annulée"
    assert (wow / REL).read_bytes() == before
