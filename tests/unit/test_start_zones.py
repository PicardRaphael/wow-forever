"""Zones de départ des races (réponse de l'utilisateur du 2026-10-16, question 2 du plan de CJ1 rétablie ; décision
283) : une table lue dans les données (`mechanics.json`, `route.start_zones`), jamais devinée par la première quête du
parcours. Les routes (zone de départ d'abord, départ supposé sans position) et l'équipement (zones de départ des autres
races, jamais proposées hors de ma route) s'appuient sur elle.

Valeurs attendues : la table de l'utilisateur (citée ici, comparée aux données du dépôt) ; zones et quêtes fabriquées
pour les fonctions de route. Aucun chiffre de jeu ici."""

from types import SimpleNamespace

import pytest

from forever.gamedata import MECHANICS_FILE
from forever.gear import other_start_zones
from forever.route import race_start_zone, start_giver_in_zone, start_zone_map
from forever.store import load_version

# Table de l'utilisateur (2026-10-16) : race -> (sous-zone, zone)
TABLE = {
    "Human": ("Northshire", "Elwynn Forest"),
    "Dwarf": ("Coldridge Valley", "Dun Morogh"),
    "Gnome": ("Coldridge Valley", "Dun Morogh"),
    "Night Elf": ("Shadowglen", "Teldrassil"),
    "Orc": ("Valley of Trials", "Durotar"),
    "Troll": ("Valley of Trials", "Durotar"),
    "Undead": ("Deathknell", "Tirisfal Glades"),
    "Tauren": ("Camp Narache", "Mulgore"),
    "High Order Skyborne": (None, "Zephras Isle"),
    "Windshaper Skyborne": (None, "Zephras Isle"),
}


@pytest.fixture
def values(make_deps):
    return load_version(make_deps()).read_json(MECHANICS_FILE)["values"]


def test_every_race_of_the_data_has_a_start_zone(values, make_deps):
    races = load_version(make_deps()).read_json("races.json")["races"]
    assert set(races) == set(TABLE)
    for race in races:
        assert race_start_zone(values, race) is not None, race


@pytest.mark.parametrize("race", sorted(TABLE))
def test_start_zone_of_each_race(values, race):
    subzone, zone = TABLE[race]
    assert race_start_zone(values, race) == {"zone": zone, "subzone": subzone}


@pytest.mark.parametrize("race", sorted(TABLE))
def test_route_start_zone_and_supposed_start(values, race):
    zone = TABLE[race][1]
    names = {9000 + i: name for i, name in enumerate(sorted({z for _, z in TABLE.values()}))}
    ui_map = start_zone_map(values, race, names)
    assert names[ui_map] == zone
    elsewhere = next(m for m, n in names.items() if n != zone)
    quests = {
        1: SimpleNamespace(zone=elsewhere, giver="far", level=1, min_level=1),
        2: SimpleNamespace(zone=ui_map, giver="home", level=1, min_level=1),
    }
    assert start_giver_in_zone(quests, ui_map, level=1) == "home"  # jamais le donneur d'une autre zone


@pytest.mark.parametrize("race", sorted(TABLE))
def test_gear_never_offers_another_race_start_zone(values, race):
    mine = TABLE[race][1]
    others = other_start_zones(values, race)
    assert mine not in others
    assert others == {z for r, (_, z) in TABLE.items() if z != mine}
