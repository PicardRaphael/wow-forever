"""Suites de la relecture de DJ1 : quêtes d'une aile rangées dans leur seule aile (Forever Guide liste les quêtes de
toute l'instance sous chaque aile), quêtes d'une instance à ailes ou d'un donjon non rattaché gardées (régression de
T04d : une quête « Dire Maul » disparaissait des objectifs), butin rouvert compté une fois, camp sans casse, placement
jamais au plafond.

Fixtures synthétiques `tests/fixtures/addons/dungeons/` ; aucun chiffre de jeu ici, aucun réseau."""

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.dungeons import build_dungeons, lookup_dungeons, merge_dungeons
from forever.pipeline.dungeon_sources import read_guide_dungeons, read_naowh_journal
from forever.pipeline.dungeons_client import decode_dungeons, load_dungeon_tables
from forever.quests import build_quests

WOW = FIXTURES / "addons" / "dungeons"
ADDONS = WOW / "Interface" / "AddOns"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
CLIENT = decode_dungeons(load_dungeon_tables(FIXTURES / "wago" / "dungeons", RULES), RULES, LOCAL_VERSION)


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("wings"))


@pytest.fixture(scope="module")
def book(deps):
    return build_dungeons(deps, wow_dir=WOW)


def quest_ids(book, key):
    return {q["id"] for q in book.dungeons[key]["quests"]}


def test_wing_quests_stay_in_their_wing(book):
    assert 90001 in quest_ids(book, "189:graveyard") and 90002 not in quest_ids(book, "189:graveyard")
    assert 90002 in quest_ids(book, "189:library") and 90001 not in quest_ids(book, "189:library")


def test_instance_quests_of_a_winged_instance_are_kept(book):
    for key in ("189:graveyard", "189:library"):
        assert 90003 in {q["id"] for q in book.dungeons[key]["instance_quests"]}
        assert 90003 not in quest_ids(book, key)  # ni comptée dans une aile, ni perdue
    assert any("90003" in n for n in book.notes)


def test_unresolved_dungeon_of_a_quest_is_kept(book):
    key = "name:mystery hollow"
    assert key in book.dungeons and quest_ids(book, key) == {90004}


def test_observed_loot_counts_each_corpse_once(deps):
    quests = build_quests(deps, wow_dir=WOW)
    sources = [read_naowh_journal(ADDONS), read_guide_dungeons(ADDONS)]
    guid = "Creature-0-4170-389-28-11520-0000ABCDEF"
    records = {
        "kills": {2733: {"n": 1}},
        "loot": [{"item": 14149, "npc": 11520, "source": guid}, {"item": 14149, "npc": 11520, "source": guid}],
    }
    merged = merge_dungeons(CLIENT, sources, book=quests, records=records)
    boss = next(b for b in merged.dungeons["389"]["bosses"] if b["name"] == "Taragaman the Hungerer")
    cape = next(x for x in boss["loot"] if x["item"] == 14149)
    assert cape["observed"] == {"drops": 1, "kills": 1}  # même corps rouvert : un seul lâché


def test_faction_ignores_case(book):
    lower = {d["id"] for d in lookup_dungeons(book, faction="horde")}
    assert lower == {d["id"] for d in lookup_dungeons(book, faction="Horde")}
