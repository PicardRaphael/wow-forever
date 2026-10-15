"""CJ1, bloc 4 (décisions 272 et 276) : lecture locale des addons d'équipement, agrégats seulement, rien dans le dépôt.
Statistiques des objets de Forever Guide (`GearData.lua`), listes BiS de Naowh Forever (et lieux de butin) et de
Forever Companion, échelles de Forever Companion, choix de leveling de GearQuest Forever ; un addon absent rend une
lecture vide, jamais une erreur.

Valeurs : addons fabriqués `tests/fixtures/addons/gear/` (structure seulement, identifiants inventés)."""

from conftest import FIXTURES

from forever.pipeline.gear_sources import (
    GearPick,
    read_companion_bis,
    read_companion_scales,
    read_gearquest_picks,
    read_guide_gear,
    read_naowh_bis,
)

ADDONS = FIXTURES / "addons" / "gear"


def test_guide_gear_stats():
    items = read_guide_gear(ADDONS)
    hood = items[900001]
    assert hood.stats == {"int": 10.0, "spi": 5.0, "sp": 6.0}
    assert (hood.inv_type, hood.req_level, hood.quality) == (1, 20, 3)
    assert items[900003].stats["crit"] == 1.0 and len(items) == 6


def test_naowh_bis_lists_and_sources():
    lists, sources = read_naowh_bis(ADDONS)
    fire = lists["fire-mage"]
    assert fire.class_token == "MAGE" and fire.name == "Fire Mage"
    assert fire.slots[11] == (900004, 900003) and fire.slots[13] == (900005,)
    assert sources[900001].startswith("Boss Fixture")


def test_companion_bis_lists():
    lists = read_companion_bis(ADDONS)
    fire = lists[("Mage", "Fire")]
    assert fire["head"] == (900001, 900002) and fire["finger"] == (900003, 900007)


def test_companion_scales():
    scales = read_companion_scales(ADDONS)
    (mage,) = scales["MAGE"]
    assert mage.label == "Fixture DPS" and mage.weights["SpellPower"] == 2.0 and mage.tab == 2


def test_gearquest_picks():
    picks = read_gearquest_picks(ADDONS, "MAGE")
    assert picks[0] == GearPick(900001, "Head", 18, 22, 1, "fire", "Alliance", 3.5)
    assert len(picks) == 3 and read_gearquest_picks(ADDONS, "WARRIOR") == []


def test_missing_addons_read_empty(tmp_path):
    assert read_guide_gear(tmp_path) == {}
    assert read_naowh_bis(tmp_path) == ({}, {})
    assert read_companion_bis(tmp_path) == {} and read_companion_scales(tmp_path) == {}
    assert read_gearquest_picks(tmp_path, "MAGE") == []
