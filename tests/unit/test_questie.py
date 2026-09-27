"""Lecteur local de la base Questie (sans réseau) : version du .toc Camelot, PNJ, XP de quête, étiquette communautaire.

Valeurs de l'extrait tests/fixtures/questie/11.38.0/ (voir son README.md)."""

import pytest
from conftest import FIXTURES

from forever.errors import PathNotFoundError
from forever.pipeline.questie import QuestieNpc, read_questie

QUESTIE = FIXTURES / "questie" / "11.38.0"


def test_info_from_camelot_toc():
    db = read_questie(QUESTIE)
    info = db.info
    assert (info.version, info.title, info.interface) == ("11.38.0", "Forever-v27", 16001)
    assert info.npc_count == 24 and info.quest_count is None  # T04b : + 19 PNJ de la seconde fixture


def test_npcs():
    db = read_questie(QUESTIE)
    assert db.npc(3099) == QuestieNpc(3099, "Dire Mottled Boar", 120, 137, 6, 7, 0, 14)
    hare = db.npc(5951)
    assert (hare.name, hare.min_level_health, hare.max_level_health, hare.min_level, hare.max_level) == (
        "Hare",
        8,
        8,
        1,
        1,
    )
    assert db.npc(1) is None
    assert {1531, 3099, 3111, 5945, 5951, 3986, 12320} <= set(db.npcs()) and len(db.npcs()) == 24


def test_hp_at_level_interpolates_between_min_and_max():
    boar = read_questie(QUESTIE).npc(3099)
    assert (boar.hp_at(6), boar.hp_at(7), boar.hp_at(8)) == (120, 137, None)


def test_quest_xp():
    db = read_questie(QUESTIE)
    assert db.quest_xp(788) == (2, 170)
    assert db.quest_xp(1) is None


def test_community_label_and_certainty():
    db = read_questie(QUESTIE)
    assert db.certainty == "suppose"
    assert "communautaire" in db.source and "11.38.0" in db.source and "Classic Era" in db.source


def test_missing_addon(tmp_path):
    with pytest.raises(PathNotFoundError):
        read_questie(tmp_path / "Questie")
