"""Relecture de FA1 : rang maximal différent entre l'addon et nos données (classe bloquée, talent nommé, jamais un
code que l'addon lirait mal) ; code avec segments Legacy (bonus de points inconnu : légalité non vérifiable, pas
illégal).

Addon synthétique écrit dans `tmp_path` (`tests/talents_forever_data.py`) ; aucun accès au dossier réel du jeu."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from talents_forever_data import load_fixture, write_addon

from forever.talents_forever import crosscheck_report, decode_code, export_build, load_addon

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
CASES = load_fixture("mage_builds.json")["cases"]


def lower_frostbite_max(doc):
    for tree in doc["classes"]["MAGE"]["trees"]:
        for t in tree["talents"]:
            if t["name"] == "Frostbite":
                t["max"] = t["max"] - 1


@pytest.fixture
def deps(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES)
    return make_deps(wow_dir=root)


def test_rank_max_gap_blocks_the_class_and_names_the_talent(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lower_frostbite_max)
    addon = load_addon(make_deps(wow_dir=root))
    mage = addon.layouts["Mage"]
    assert not mage.exportable and "frostbite" in mage.blocked and "rang" in mage.blocked
    case = CASES["leveling-30"]
    block = export_build(addon, "Mage", case["level"], case["talents"], case["order"])
    assert block["status"] == "bloque" and block["code"] is None and "frostbite" in block["reason"]
    assert "frostbite" in crosscheck_report(addon)["classes"]["Mage"]["blocked"]


def test_legacy_segments_make_legality_unverifiable(deps):
    addon = load_addon(deps)
    code = CASES["dungeon-20"]["expected_code"].removesuffix("-6") + "-a-b-c-6"
    back = decode_code(addon, deps, code)
    assert back["legacy"] == ["a", "b", "c"]
    assert back["legal"] is None and back["legality"] == "non vérifiable"
    assert "Legacy" in back["note"]
    assert back["talents"] == CASES["dungeon-20"]["talents"]
