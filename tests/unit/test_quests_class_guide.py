"""Quêtes de classe de Forever Guide (plan « Sources d'abord », reste de l'étape b ; décisions 272 et 288) :
`ForeverGuide/ClassData.lua` (`ns.CLASS_Q`, une quête par ligne : nom, niveaux, masque de classes `c`, masque de
races `ra`, PNJ de départ `s` et de rendu `e`, quête suivante `nx` ; `ns.CLASS_NPC` : PNJ au format de `ns.SI_NPC`,
nom anglais en 2e colonne, carte, x, y) lu par la source `forever_guide`. Le champ `pre` n'est pas repris : liste sans
distinction « toutes » ou « une parmi » (les autres sources donnent les prérequis). La route reçoit ces quêtes comme
quêtes de classe (champ `classes`).

Fixture : dossier du client réduit de `tests/fixtures/addons/quests/`, plus un `ClassData.lua` fabriqué (structure de
Forever Guide 1.37.0) ; quêtes, PNJ et positions inventés."""

import shutil

import pytest
from conftest import FIXTURES, isolated_deps

from forever.pipeline.quest_sources import read_forever_guide, source_files
from forever.quests import build_quests, value

CLASS_DATA = """-- Données fabriquées (structure de Forever Guide).
local _, ns = ...

ns.CLASS_Q = {
[990001]={n="Fixture Calling",r="x",lv=10,rl=10,c=128,ra=178,s=990101,e=990102,nx=990002,pre={990009,990008},o="x"},
[990002]={n="Fixture Calling Two",r="x",lv=12,rl=10,c=128,ra=77,s=990102,e=990103,sp=900000},
[990003]={n="Fixture Relic",r="x",lv=20,rl=18,c=1,so=4000,e=990103},
}

ns.CLASS_NPC = {
[990101]="x\tFixture Trainer\t5\t5\t0\t1411\t44.5\t66.0\t\t1\tH",
[990102]="x\tFixture Sage\t30\t30\t0\t1438\t12.5\t34.0\t\t1\tA",
}
"""
SEARCH_DATA = """local _, ns = ...
ns.SI_NPC = {
[990103]="x\tFixture Keeper\t40\t40\t0\t1453\t70.0\t20.0\t\t1\tA",
}
"""


@pytest.fixture(scope="module")
def wow(tmp_path_factory):
    root = tmp_path_factory.mktemp("wow") / "wow"
    shutil.copytree(FIXTURES / "addons" / "quests", root)
    guide = root / "Interface" / "AddOns" / "ForeverGuide"
    (guide / "ClassData.lua").write_text(CLASS_DATA, encoding="utf-8")
    (guide / "ItemSearchData.lua").write_text(SEARCH_DATA, encoding="utf-8")
    return root


def test_class_quests_are_read_with_their_npcs(wow):
    source = read_forever_guide(wow / "Interface" / "AddOns")
    q = source.quests[990001]
    assert (q["name"], q["level"], q["min_level"], q["classes"], q["races"]) == ("Fixture Calling", 10, 10, 128, 178)
    assert q["faction"] == "horde" and q["next"] == 990002
    assert q["giver"] == {"name": "Fixture Trainer", "map": 1411, "x": 44.5, "y": 66.0, "npc": 990101}
    assert q["turn_in"]["name"] == "Fixture Sage"
    assert "prereq_all" not in q and "prereq_any" not in q  # `pre` : sens ambigu, jamais repris
    assert source.quests[990002]["turn_in"]["name"] == "Fixture Keeper"  # PNJ de ns.SI_NPC
    relic = source.quests[990003]
    assert "giver" not in relic and relic["classes"] == 1  # commencée par un objet : pas de donneur
    assert any(p.name == "ClassData.lua" for p in source.info.files)


def test_class_data_is_in_the_cache_fingerprint(wow):
    names = {p.name for p in source_files(wow / "Interface" / "AddOns", None)}
    assert {"ClassData.lua", "ItemSearchData.lua"} <= names


def test_merged_book_marks_them_as_class_quests(wow, tmp_path):
    book = build_quests(isolated_deps(tmp_path), wow_dir=wow)
    q = book.quests[990002]
    assert value(q, "classes") == 128 and q["fields"]["classes"]["source"] == "forever_guide"
    assert value(q, "giver")["name"] == "Fixture Sage"
