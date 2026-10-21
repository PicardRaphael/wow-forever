"""Type de serveur, version minimale avant la sortie (plan des simulateurs, décision 294 ; demande du 2026-10-21) :

- champ par personnage déclaré par le joueur (`server_type` : `pvp` ou `normal`), jamais déduit ;
- camp de chaque carte de zone lu dans le client de Forever (`AreaTable.FactionGroupMask` de la zone de la carte,
  bits de `decode_rules.json travel.area_faction_masks`) : `alliance`, `horde`, `contested` (aucun camp), `both` ;
- sur un serveur JcJ, la feuille de route signale ses arrêts en zone disputée ou en territoire ennemi ; sur un serveur
  normal (ou type inconnu), rien n'est signalé.

Tables et arrêts fabriqués ici (structure du client et des plans de route) ; aucun chiffre de jeu."""

import pytest

from forever.errors import InvalidArgumentError
from forever.pipeline.travel_client import decode_travel
from forever.route import pvp_zone_warnings

RULES = {"travel": {"faction_flags": {"alliance": 1, "horde": 2}, "teleport_flag": 1,
                    "area_faction_masks": {"alliance": 2, "horde": 4}}}  # fmt: skip


def assignment(ui_map, area):
    return {"UiMapID": ui_map, "OrderIndex": 0, "MapID": 0, "AreaID": area, "Region_0": 0.0, "Region_1": 0.0,
            "Region_3": 1.0, "Region_4": 1.0}  # fmt: skip


def test_territory_of_each_map_comes_from_the_client():
    tables = {
        "TaxiNodes": [], "TaxiPath": [], "TaxiPathNode": [],
        "UiMapAssignment": [assignment(9001, 1), assignment(9002, 2), assignment(9003, 3), assignment(9004, 4)],
        "AreaTable": [{"ID": 1, "FactionGroupMask": 2}, {"ID": 2, "FactionGroupMask": 4},
                      {"ID": 3, "FactionGroupMask": 0}, {"ID": 4, "FactionGroupMask": 6}],
    }  # fmt: skip
    maps = {m["ui_map"]: m["territory"] for m in decode_travel(tables, RULES, "1.0")["maps"]}
    assert maps == {9001: "alliance", 9002: "horde", 9003: "contested", 9004: "both"}


def test_without_area_table_no_territory_is_invented():
    tables = {"TaxiNodes": [], "TaxiPath": [], "TaxiPathNode": [], "UiMapAssignment": [assignment(9001, 1)]}
    assert "territory" not in decode_travel(tables, RULES, "1.0")["maps"][0]


def test_server_type_is_declared_per_character(make_deps, tmp_path):
    from forever.profile import character_values, load_profile, resolve_path, set_character

    deps = make_deps(cache_dir=tmp_path)
    set_character(deps, "Jen", cls="Mage", race="Gnome", faction="alliance", server_type="pvp")
    raw = load_profile(resolve_path(deps))["characters"]["Jen"]
    assert character_values(raw)["server_type"] == "pvp"
    with pytest.raises(InvalidArgumentError):
        set_character(deps, "Jen", server_type="jcj-rp")


STOPS = [
    {"kind": "accept", "name": "Quête A", "zone": "Zone Alliance", "map": 9001},
    {"kind": "accept", "name": "Quête B", "zone": "Zone Disputée", "map": 9003},
    {"kind": "turnin", "name": "Quête C", "zone": "Zone Horde", "map": 9002},
    {"kind": "accept", "name": "Quête D", "zone": "Zone Disputée", "map": 9003},
]
TERRITORY = {9001: "alliance", 9002: "horde", 9003: "contested"}


def test_pvp_server_flags_contested_and_enemy_zones_once_each():
    warnings = pvp_zone_warnings(STOPS, TERRITORY, faction="alliance", server_type="pvp")
    text = " ".join(warnings)
    assert len(warnings) == 2 and "Zone Disputée" in text and "Zone Horde" in text and "Zone Alliance" not in text
    assert "serveur JcJ" in text


def test_normal_or_unknown_server_flags_nothing():
    assert pvp_zone_warnings(STOPS, TERRITORY, faction="alliance", server_type="normal") == []
    assert pvp_zone_warnings(STOPS, TERRITORY, faction="alliance", server_type=None) == []
