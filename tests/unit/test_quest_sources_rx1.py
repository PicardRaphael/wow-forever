"""Lecteurs de quêtes corrigés en RX1 (bloc A) : quêtes que Factoruide connaissait et pas nous alors qu'un fichier
local les cite (livres de Naowh Discovery, chaînes de Forever Guide, chaînes du Dungeon Journal de Naowh, chaînes de
ForeverDungeonJournal, quêtes faites et quêtes sans titre des SavedVariables de Questie).

Fixture : `tests/fixtures/addons/quests_rx1/` (structure des fichiers installés le 2026-10-14, identifiants, noms et
positions inventés, README). Les valeurs attendues sont celles écrites dans les fixtures ; aucun réseau."""

import json

import pytest
from conftest import FIXTURES, isolated_deps

from forever.pipeline.quest_sources import (
    read_completo,
    read_fdj,
    read_forever_guide,
    read_naowh_dj,
    read_questie_forever,
    source_files,
)
from forever.quests import build_quests, value

WOW = FIXTURES / "addons" / "quests_rx1"
ADDONS = WOW / "Interface" / "AddOns"
WTF = WOW / "WTF"


def test_discovery_books_are_read():
    quests = read_completo(ADDONS).source.quests
    assert quests[990010]["name"] == "Fixture Errand"  # QuestList inchangé
    book = quests[990022]
    assert book["name"] == "Fixture Almanac, Vol. 1" and book["faction"] == "horde"
    assert book["start_item"] == 990910
    assert book["giver"] == {"map": 1001, "x": 12.5, "y": 34.5, "name": "Fixture Hut"}
    assert book["turn_in"] == {"map": 1001, "x": 10.0, "y": 20.0, "name": "Fixture Librarian"}
    assert quests[990023]["faction"] == "both" and "giver" not in quests[990023]  # livre non placé
    assert quests[990024]["faction"] == "alliance" and "turn_in" not in quests[990024]  # rendu au maître : non placé
    assert quests[990020]["name"] == "Fixture Reader" and "level" not in quests[990020]
    assert quests[990021]["level"] == 30


def test_guide_chain_data_is_read():
    quests = read_forever_guide(ADDONS).quests
    start = quests[990030]
    assert (start["name"], start["min_level"], start["faction"]) == ("Fixture Note", 14, "alliance")
    assert start["giver"] == {"map": 1001, "x": 46.0, "y": 74.0}
    horde = quests[990033]  # départ Horde, absent de ChainExtraQuests : camp et position seulement
    assert horde["faction"] == "horde" and horde["giver"] == {"map": 1002, "x": 37.0, "y": 50.0}
    assert "name" not in horde and "min_level" not in horde
    assert quests[990031]["prereq_any"] == [990030, 990033]  # étape suivante : après l'un des deux départs
    assert quests[990032]["prereq_any"] == [990031] and quests[990032]["min_level"] == 16
    assert quests[990032]["giver"] == {"map": 1003, "x": 87.3, "y": 49.6}
    assert quests[990035]["prereq_any"] == [990034] and 990034 in quests  # chaîne sans texte : existence et ordre
    assert quests[990034]["chain"] == {"name": "Fixture Key", "step": 0, "after": []}


def test_naowh_quest_chains_are_read():
    quests = read_naowh_dj(ADDONS).quests
    first = quests[990040]
    assert (first["name"], first["min_level"]) == ("Fixture Call", 10)
    assert first["giver"] == {"map": 1001, "x": 35.2, "y": 8.0, "name": "Fixture Shaman"}
    assert "prereq_any" not in first
    assert quests[990041]["prereq_any"] == [990040]
    assert quests[990043]["prereq_any"] == [990042] and quests[990043]["min_level"] == 14
    assert quests[990043]["giver"] == {"name": "Fixture Shaman"}  # texte sans carte : nom seulement
    assert quests[990046]["prereq_any"] == [990044, 990045] and quests[990046]["name"] == "Fixture Blade"
    assert 990044 in quests and "prereq_any" not in quests[990044]


def test_fdj_quest_chains_are_read():
    quests = read_fdj(ADDONS).quests
    assert quests[990052]["prereq_all"] == [990050, 990051]
    rumors = quests[990050]
    assert (rumors["name"], rumors["level"], rumors["min_level"]) == ("Fixture Rumors", 31, 24)
    giver = rumors["giver"]
    assert (giver["map"], giver["name"]) == (1003, "Fixture Giver")
    assert giver["x"] == pytest.approx(74.0) and giver["y"] == pytest.approx(36.0)
    lead = quests[990051]  # position dans le détail (`map`), constante de l'addon ignorée
    assert (lead["name"], lead["level"], lead["min_level"]) == ("Fixture Lead", 32, 25)
    assert lead["giver"]["map"] == 1002 and lead["giver"]["x"] == pytest.approx(53.0)


def test_questie_saved_variables_keep_completed_and_bare_quests():
    read = read_questie_forever(WTF)
    quests = read.quests
    assert quests[990060] == {"completed": True}
    assert quests[990061] == {"completed": True}  # faite par deux personnages : une seule entrée
    assert quests[990062] == {"completed": True}
    assert quests[990063] == {"seen": True}  # entrée sans titre ni niveau : gardée
    assert quests[990064] == {"name": "Fixture Learned", "level": 7, "map": 1001}
    dumped = json.dumps([quests, read.notes])
    assert "Perso" not in dumped and "Autre" not in dumped  # aucun nom de personnage


def test_new_files_are_in_the_fingerprint():
    names = {p.name for p in source_files(ADDONS, WTF)}
    assert {"Books.lua", "ChainData.lua", "QuestChains.lua", "QuestMaps.lua", "Questie.lua"} <= names
    chains = [p for p in source_files(ADDONS, WTF) if p.name == "QuestChains.lua"]
    assert len(chains) == 2  # Dungeon Journal de Naowh et ForeverDungeonJournal


def test_new_quests_reach_the_book(tmp_path):
    book = build_quests(isolated_deps(tmp_path), wow_dir=WOW)
    for quest_id in (990020, 990022, 990030, 990033, 990040, 990044, 990050, 990052, 990060, 990063):
        assert quest_id in book.quests, quest_id
        assert book.quests[quest_id]["status"] == "nouvelle"  # Questie Classic absent de la fixture
    assert book.quests[990022]["fields"]["giver"]["source"] == "completo"
    assert value(book.quests[990060], "completed") is True
    assert book.quests[990060]["fields"]["completed"]["source"] == "questie_forever"
