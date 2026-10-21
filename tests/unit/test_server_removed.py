"""Talents retirés par un correctif du serveur lu sans session de jeu (décision 290, premier cas : Piercing Ice,
correctif 112753 lu dans un cache vérifié de Raidbots, 1.60.1.70450 r6) : `lookup` dit « probablement retiré » avec
sa source au lieu de « talent inconnu », et aucune recommandation ne le propose (builds populaires écartés avec leur
raison ; nos builds, le PvP et les exports n'ont plus le talent dans leurs données).

Données de la version installée (r6) et copies fabriquées dans `tmp_path`."""

import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.errors import ForeverError
from forever.lookup import lookup_talent
from forever.server_removed import exclude_removed_builds, server_removed_talents


def test_piercing_ice_is_listed_with_its_source(make_deps):
    removed = server_removed_talents(make_deps().data_dir)
    ice = next(r for r in removed if r["key"] == "piercingIce")
    assert ice["name"] == "Piercing Ice" and ice["class"] == "Mage"
    assert ice["certainty"] == "probable" and "Raidbots" in ice["source"]


def test_lookup_says_probably_removed(make_deps):
    with pytest.raises(ForeverError) as err:
        lookup_talent(make_deps(), "Piercing Ice")
    assert err.value.code == "removed_talent"
    assert "probablement retiré" in err.value.message and "Raidbots" in err.value.message


def test_nothing_removed_without_server_entries(tmp_path, make_deps):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    path = data / LOCAL_VERSION / "confirmed_changes.json"
    doc = read_json(path)
    doc["changes"] = [c for c in doc["changes"] if c.get("nature") != "correctif_serveur"]
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert server_removed_talents(data) == []


def test_popular_builds_with_a_removed_talent_are_set_aside():
    removed = [{"key": "piercingIce", "name": "Piercing Ice", "class": "Mage", "source": "s", "certainty": "probable"}]
    top = [
        {"rank": 1, "unverifiable": [], "legality": "légal"},
        {"rank": 2, "unverifiable": ["Piercing Ice", "Frost Channeling"], "legality": "non vérifiable"},
        {"rank": 3, "unverifiable": ["Frost Channeling"], "legality": "non vérifiable"},
    ]
    kept, aside = exclude_removed_builds(top, "Mage", removed)
    assert [b["rank"] for b in kept] == [1, 3]
    assert aside == [{"rank": 2, "removed": ["Piercing Ice"]}]
    assert exclude_removed_builds(top, "Priest", removed) == (top, [])
