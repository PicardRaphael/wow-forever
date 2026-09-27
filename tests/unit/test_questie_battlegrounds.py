"""Champs de bataille écartés des donjons (T04c, relecture du bloc F ; registre I7).

`dungeons.lua` de Questie liste aussi les champs de bataille (Warsong Gulch 3277 dans la fixture) ; Questie les range
dans la catégorie « Battlegrounds » de `lookupZones.lua` (`continentLookup`, `zoneCategoryLookup`)."""

from conftest import FIXTURES

from forever.pipeline.questie import read_questie

QUESTIE = FIXTURES / "questie" / "11.38.0"
WARSONG_GULCH = 3277


def test_battlegrounds_are_read_from_the_zone_categories():
    db = read_questie(QUESTIE)
    assert WARSONG_GULCH in db.battlegrounds()
    assert 718 not in db.battlegrounds()


def test_dungeons_exclude_battlegrounds():
    dungeons = read_questie(QUESTIE).dungeons()
    assert WARSONG_GULCH not in dungeons
    assert set(dungeons) == {718, 1581, 2437}
