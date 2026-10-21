"""Invariants sur la version réellement installée (plan « Sources d'abord », étape c ; décision 291) : la suite lit
`VALUES_VERSION` pour ses valeurs attendues ; ces tests-ci lisent les données installées (`REPO_DATA_DIR`, version la
plus récente, celle que la veille vient d'installer) et ne vérifient **aucune valeur de jeu** : intégrité, provenance,
pas de panne, sources relevées, talents retirés absents des recommandations. Ce sont eux qui disent, à chaque nouvelle
version, que les outils répondent encore ; les valeurs qui changent vont au rapport de la veille."""

import json

import pytest
from conftest import REPO_DATA_DIR

from forever.lookup import lookup_spell, lookup_talent
from forever.server_removed import server_removed_talents
from forever.status import status_report

INSTALLED = json.loads((REPO_DATA_DIR / "manifest.json").read_text(encoding="utf-8"))["game_version"]


@pytest.fixture
def deps(make_deps):
    return make_deps(data_dir=REPO_DATA_DIR)


def test_installed_data_is_whole_and_says_its_version(deps):
    rep = status_report(deps, allow_network=False)
    assert rep["integrity"]["ok"] and rep["local_version"] == INSTALLED
    assert rep["provenance"]["game_version"] == INSTALLED
    assert any(s["source"] == "moteur" for s in rep["sources"])


def test_every_talent_and_spell_answers(deps):
    talents = json.loads((REPO_DATA_DIR / INSTALLED / "talents.json").read_text(encoding="utf-8"))
    for tree in talents["trees"]:
        for t in tree["talents"]:
            out = lookup_talent(deps, t["key"])
            assert out["provenance"]["game_version"] == INSTALLED, t["key"]
    spells = json.loads((REPO_DATA_DIR / INSTALLED / "spells.json").read_text(encoding="utf-8"))
    for key in spells["spells"]:
        assert lookup_spell(deps, key)["provenance"]["game_version"] == INSTALLED, key


def test_removed_talents_are_absent_from_the_installed_trees(deps):
    talents = json.loads((REPO_DATA_DIR / INSTALLED / "talents.json").read_text(encoding="utf-8"))
    keys = {t["key"] for tree in talents["trees"] for t in tree["talents"]}
    assert not keys & {r["key"] for r in server_removed_talents(REPO_DATA_DIR)}


@pytest.mark.slow
def test_a_leveling_build_is_computed_on_the_installed_version(deps):
    from forever.build import build_report

    rep = build_report(deps, "leveling", 20, preset="rapide", sensitivity=False)
    assert rep["provenance"]["game_version"] == INSTALLED and rep["talents"]
    gone = {r["key"] for r in server_removed_talents(REPO_DATA_DIR)}
    assert not set(rep["talents"]) & gone


def test_every_talent_description_variable_has_a_value():
    """Aucune description de talent installée n'affiche une variable `{i}` sans valeur dans ses rangs (« {0} »)."""
    import re

    talents = json.loads((REPO_DATA_DIR / INSTALLED / "talents.json").read_text(encoding="utf-8"))
    for tree in talents["trees"]:
        for t in tree["talents"]:
            used = [int(i) for i in re.findall(r"\{(\d+)\}", t.get("desc") or "")]
            values = t.get("tooltip_values") or t["ranks"]
            assert not used or max(used) < min(len(r) for r in values), (t["key"], t["desc"])
