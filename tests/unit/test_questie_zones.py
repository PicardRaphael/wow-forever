"""Zone ou donjon à mon niveau (T04c, bloc F ; registre I7).

Fixture Questie 11.38.0 (README) : 138 quêtes de Durotar (14), des Tarides (17) et de Wailing Caverns (718) ;
Wailing Caverns : quêtes de niveau 16 à 26, sans identifiant de zone alternatif, zone parente 17 ; The Deadmines :
alternatif 10029 ; quête 3370 « In Nightmares » (les Tarides, niveau 25, niveau requis 15) réservée à l'Alliance
(masque de races 77). Couleurs de quête : seuils et niveau gris de `leveling.quest_band` (données, règle de Classic,
suppose), jamais recopiés ici."""

import pytest
from conftest import FIXTURES

from forever.engine.leveling import gray_level, level_band, quest_color
from forever.pipeline.questie import (
    CLASS_MASKS,
    FACTION_MASKS,
    QuestieQuest,
    quest_available,
    read_questie,
    zones_for_level,
)

QUESTIE = FIXTURES / "questie" / "11.38.0"
ALLIANCE_QUEST = 3370


@pytest.fixture(scope="module")
def db():
    return read_questie(QUESTIE)


def test_quests_are_read(db):
    quests = db.quests()
    assert len(quests) == 138
    q = quests[914]
    assert (q.name, q.required_level, q.quest_level, q.zone_or_sort) == ("Leaders of the Fang", 11, 22, 718)
    assert q.required_races == FACTION_MASKS["horde"] and q.required_classes == 0
    assert quests[ALLIANCE_QUEST].required_races == FACTION_MASKS["alliance"]


def test_dungeons_and_zone_names_are_read(db):
    dungeons = db.dungeons()
    assert dungeons[718].name == "Wailing Caverns" and dungeons[718].alternative_ids == ()
    assert dungeons[718].parent_zone == 17
    assert dungeons[1581].alternative_ids == (10029,)
    names = db.zone_names()
    assert (names[14], names[17], names[718]) == ("Durotar", "The Barrens", "Wailing Caverns")


def test_quest_band_comes_from_the_data(game_data):
    band = game_data.leveling.quest_band
    player = 12
    gray = gray_level(game_data, player)
    assert quest_color(game_data, player, gray) == "gray"
    assert quest_color(game_data, player, gray + 1) == "green"
    assert quest_color(game_data, player, player + band.yellow_min_diff - 1) == "green"
    assert quest_color(game_data, player, player + band.yellow_min_diff) == "yellow"
    assert quest_color(game_data, player, player + band.orange_min_diff - 1) == "yellow"
    assert quest_color(game_data, player, player + band.orange_min_diff) == "orange"
    assert quest_color(game_data, player, player + band.red_min_diff - 1) == "orange"
    assert quest_color(game_data, player, player + band.red_min_diff) == "red"
    assert level_band(game_data, player) == (gray + 1, player + band.red_min_diff - 1)


def test_gray_level_follows_the_rows_of_the_data(game_data):
    rows = game_data.leveling.quest_band.gray_rows
    first_up_to = rows[0][0]
    assert all(gray_level(game_data, lv) == 0 for lv in range(1, first_up_to + 1))
    grays = [gray_level(game_data, lv) for lv in range(1, 61)]
    assert grays == sorted(grays) and all(g < lv for lv, g in zip(range(1, 61), grays, strict=True))


def test_quest_availability_filters():
    horde_only = QuestieQuest(1, "q", 10, 12, FACTION_MASKS["horde"], 0, 17)
    assert quest_available(horde_only, 12, "horde", "mage")
    assert not quest_available(horde_only, 12, "alliance", "mage")
    assert quest_available(horde_only, 12, None, "mage")
    assert not quest_available(horde_only, 9, "horde", "mage")  # niveau requis non atteint
    other_class = horde_only._replace(required_classes=1)  # bit de la première classe (pas le Mage)
    assert not quest_available(other_class, 12, "horde", "mage")
    assert quest_available(other_class._replace(required_classes=CLASS_MASKS["mage"]), 12, "horde", "mage")


def test_zones_for_level_12_horde(db, game_data):
    advice = zones_for_level(db, game_data, 12, faction="horde")
    names = [z["name"] for z in advice["zones"]]
    assert names[0] == "The Barrens"
    durotar = next(z for z in advice["zones"] if z["name"] == "Durotar")
    assert names.index("Durotar") > 0 and durotar["by_color"]["gray"] >= 1
    assert advice["zones"][0]["useful_quests"] > durotar["useful_quests"]
    assert all(z["kind"] == "zone" for z in advice["zones"])
    wc = next(d for d in advice["dungeons"] if d["name"] == "Wailing Caverns")
    assert wc["kind"] == "dungeon" and wc["quest_levels"] == [16, 26] and wc["useful_quests"] >= 1
    barrens = advice["zones"][0]
    assert barrens["npc_levels"] is not None and barrens["npc_levels"][0] <= barrens["npc_levels"][1]
    assert advice["band"] == list(level_band(game_data, 12))
    assert advice["certainty"] == "suppose" and "Questie 11.38.0" in advice["source"]
    assert any("anglais" in n for n in advice["notes"])


def test_other_faction_quests_are_excluded(db, game_data):
    horde = zones_for_level(db, game_data, 15, faction="horde")
    alliance = zones_for_level(db, game_data, 15, faction="alliance")
    barrens_h = next(z for z in horde["zones"] if z["area_id"] == 17)
    barrens_a = next(z for z in alliance["zones"] if z["area_id"] == 17)
    assert ALLIANCE_QUEST not in barrens_h["quests"] and ALLIANCE_QUEST in barrens_a["quests"]


def test_unknown_faction_is_refused(db, game_data):
    with pytest.raises(ValueError, match="faction"):
        zones_for_level(db, game_data, 12, faction="scourge")
