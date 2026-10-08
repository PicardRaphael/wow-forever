"""Table de correspondance de Talents Forever (FA1, bloc B) : appariement strict (arbre au même indice, sort, rangée,
colonne), contrôles de l'addon à la lecture, recoupement de la version installée et son rapport, commande
`forever talents tf crosscheck`.

Addon synthétique écrit dans `tmp_path` par `tests/talents_forever_data.py` (arbres rebâtis depuis `classes.json` et
`tests/fixtures/talents_forever/layout.json`) ; aucun accès au dossier réel du jeu."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from talents_forever_data import write_addon

from forever.cli import main
from forever.talents_forever import crosscheck_report, load_addon, render_crosscheck

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    write_addon(root, CLASSES)
    return root


@pytest.fixture
def addon(wow, make_deps):
    loaded = load_addon(make_deps(wow_dir=wow))
    assert loaded is not None
    return loaded


def matched(layout):
    return sum(1 for tree in layout.trees for key in tree if key is not None)


def test_header_version_and_fingerprint(addon):
    assert addon.version == "0.37.1"
    assert addon.head == {"build": "1.60.1.70170", "generated": "2026-10-04", "codeVersion": "6"}
    assert addon.supported and addon.checks == ()
    assert len(addon.fingerprint) == 12
    assert addon.game_version == LOCAL_VERSION
    assert set(addon.layouts) == {
        "Warrior",
        "Paladin",
        "Hunter",
        "Rogue",
        "Priest",
        "Shaman",
        "Mage",
        "Warlock",
        "Druid",
    }


def test_mage_all_matched_and_exportable(addon):
    mage = addon.layouts["Mage"]
    assert mage.file == "MAGE" and mage.slug == "mage"
    assert matched(mage) == 54 and mage.unmatched == ()
    assert mage.exportable and mage.blocked is None
    assert mage.trees[2][1] == "improvedFrostbolt"
    assert [len(t) for t in mage.max_ranks] == [len(t) for t in mage.trees]


def test_warrior_matched_despite_renumbered_nodes(addon):
    warrior = addon.layouts["Warrior"]
    assert matched(warrior) == 52 and warrior.exportable
    assert sorted(r["key"] for r in warrior.renumbered) == [
        "furiousPrecision",
        "goreDrinker",
        "ironWill",
        "lingeringRage",
    ]


def test_hunter_all_matched_after_the_in_game_survey(addon):
    hunter = addon.layouts["Hunter"]
    assert matched(hunter) == 50 and hunter.exportable and hunter.unmatched == ()
    assert hunter.prereq_gaps == ()


def test_warlock_all_matched_after_the_in_game_survey(addon):
    warlock = addon.layouts["Warlock"]
    assert matched(warlock) == 52 and warlock.exportable and warlock.unmatched == ()


def test_trees_matched_by_index_tree_names_are_cosmetic(addon):
    for name in ("Priest", "Shaman"):
        layout = addon.layouts[name]
        assert layout.exportable, name
        assert len(layout.tree_name_gaps) == 1, name
    assert addon.layouts["Priest"].tree_names[2] == "Shadow"
    assert {"Paladin", "Rogue", "Druid", "Priest", "Shaman", "Mage", "Warrior", "Hunter", "Warlock"} == {
        n for n, lay in addon.layouts.items() if lay.exportable
    }


def test_other_code_version_is_not_supported(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lambda doc: doc.update(codeVersion="7"))
    loaded = load_addon(make_deps(wow_dir=root))
    assert loaded is not None and not loaded.supported
    assert "format_non_pris_en_charge" in loaded.checks


def test_unsorted_list_blocks_its_class_with_a_named_reason(tmp_path, make_deps):
    def swap(doc):
        talents = doc["classes"]["MAGE"]["trees"][0]["talents"]
        talents[0], talents[1] = talents[1], talents[0]

    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=swap)
    loaded = load_addon(make_deps(wow_dir=root))
    assert loaded is not None
    mage = loaded.layouts["Mage"]
    assert not mage.exportable and "triée" in mage.blocked and "Arcane" in mage.blocked
    assert loaded.layouts["Paladin"].exportable


def test_absent_addon_is_none(tmp_path, make_deps):
    assert load_addon(make_deps(wow_dir=tmp_path / "vide")) is None
    assert load_addon(make_deps()) is None


def test_crosscheck_of_the_installed_version(addon):
    report = crosscheck_report(addon)
    assert report["totals"] == {"renumbered": 4, "unmatched": 0, "prereq": 0, "tree_names": 2}
    assert report["game_version"] == LOCAL_VERSION
    assert report["addon"]["version"] == "0.37.1" and report["addon"]["build"] == "1.60.1.70170"
    hunter = report["classes"]["Hunter"]
    assert hunter["matched"] == 50 and hunter["export"] == "possible"
    assert hunter["prereq"] == []
    assert report["classes"]["Mage"]["export"] == "possible"


def test_crosscheck_render_is_deterministic(addon):
    text = render_crosscheck(crosscheck_report(addon))
    assert text == render_crosscheck(crosscheck_report(addon))
    for words in (
        "0.37.1",
        LOCAL_VERSION,
        "lingeringRage",
        "Shadow Magic",
        "Elemental Combat",
    ):
        assert words in text, words
    assert text.endswith("\n") and "\r" not in text


def test_cli_crosscheck(wow, make_deps, tmp_path, capsys):
    out = tmp_path / "rapport.md"
    assert main(["talents", "tf", "crosscheck", "--out", str(out), "--json"], make_deps(wow_dir=wow)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["totals"]["unmatched"] == 0
    assert data["provenance"]["game_version"] == LOCAL_VERSION
    assert "lingeringRage" in out.read_text(encoding="utf-8")


def test_cli_crosscheck_without_addon(make_deps, tmp_path, capsys):
    code = main(["talents", "tf", "crosscheck"], make_deps(wow_dir=tmp_path / "vide"))
    assert code != 0
    assert "Talents Forever" in capsys.readouterr().err
