"""PNJ nommés de quête écartés de la courbe des PV par niveau, et candidats proposés (T08d, 2026-10-06).

Règle de l'utilisateur du 2026-10-06 : les PNJ nommés de quête (personnages uniques) et les familles hors norme déjà
vues (ours) sont toujours mesurés un par un, mais écartés de la courbe, qu'ils soient au-dessus ou en dessous, avec
leur raison écrite. L'écartement se fait par une liste écrite, après accord ; à chaque mesure, tout PNJ mesuré qui a
au plus un point d'apparition dans Questie, ou qui en est absent, est seulement **proposé** comme candidat, avec ses
PV comparés à la courbe. Questie de fixture : Dire Mottled Boar (3099) 116 points d'apparition, Sarilus Foulborne
(3986) et Gamon (6466) un point, Burning Blade Toxicologist (12319) aucun. Valeurs de PV synthétiques, sauf le test de
la révision 5, qui lit les données installées."""

import json

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION

from forever.pipeline.monsters import build_monsters
from forever.pipeline.questie import read_questie
from forever.pipeline.refresh import curve_candidates

QUESTIE = FIXTURES / "questie" / "11.38.0"
NAMED = "PNJ nommé de quête (personnage unique)"


def obs(npc_id, level, max_hp, name="PNJ"):
    return {"npc_id": npc_id, "name": name, "level": level, "max_hp": max_hp, "guids": 1, "ui_map_id": 1411, "log": "x"}


def test_spawn_points_are_read_from_questie():
    questie = read_questie(QUESTIE)
    assert questie.spawn_points(3099) == 116
    assert questie.spawn_points(3986) == 1
    assert questie.spawn_points(12319) == 0
    assert questie.spawn_points(999999) is None


def test_a_named_npc_leaves_the_curve_below_as_well_as_above():
    found = [obs(1, 20, 600, "A"), obs(2, 20, 600, "B"), obs(3, 20, 500, "Nommé bas"), obs(4, 20, 900, "Nommé haut")]
    table = build_monsters(found, None, LOCAL_VERSION, curve_exclude={3: NAMED, 4: NAMED})
    twenty = table["hp_by_level"]["20"]
    assert (twenty["value"], twenty["n_npcs"], twenty["certainty"]) == (600, 2, "certain")
    assert table["npcs"]["3"]["levels"]["20"]["max_hp"] == 500 and table["npcs"]["4"]["levels"]["20"]["max_hp"] == 900
    assert {e["npc_id"]: e["reason"] for e in table["curve_excluded"]} == {3: NAMED, 4: NAMED}


def test_unique_or_unknown_npcs_are_proposed_never_excluded():
    questie = read_questie(QUESTIE)
    found = [
        obs(3099, 6, 240, "Dire Mottled Boar"),
        obs(6466, 12, 300, "Gamon"),
        obs(3986, 25, 900, "Sarilus Foulborne"),
        obs(999999, 6, 260, "Inconnu"),
    ]
    table = build_monsters(found, questie, LOCAL_VERSION, curve_exclude={3986: NAMED})
    proposed = {c["npc_id"]: c for c in curve_candidates(table, questie)}
    assert set(proposed) == {6466, 999999}  # 3099 : 116 points ; 3986 : déjà écarté
    assert table["curve_excluded"] == [e for e in table["curve_excluded"] if e["npc_id"] == 3986]  # rien d'écarté
    gamon = proposed[6466]
    assert gamon["spawn_points"] == 1 and gamon["name"] == "Gamon"
    assert gamon["levels"] == [{"level": 12, "max_hp": 300, "curve": 300, "ratio": 1.0}]  # seul PNJ du niveau 12
    unknown = proposed[999999]
    assert unknown["spawn_points"] is None
    six = table["hp_by_level"]["6"]["value"]
    assert unknown["levels"] == [{"level": 6, "max_hp": 260, "curve": six, "ratio": 260 / six}]


def test_without_questie_every_measured_npc_is_unknown_but_none_is_proposed():
    table = build_monsters([obs(1, 20, 600)], None, LOCAL_VERSION)
    assert curve_candidates(table, None) == []


def test_revision_5_excludes_the_eight_named_npcs_with_their_reason():
    monsters = json.loads((DATA_DIR / "1.60.1.70170" / "monsters.json").read_text(encoding="utf-8"))
    named = {e["name"] for e in monsters["curve_excluded"] if e["reason"].startswith(NAMED)}
    assert named == {
        "Ilkrud Magthrull",
        "Vorsha the Lasher",
        "Sarilus Foulborne",
        "Muglash",
        "Talen",
        "Therylune",
        "Gamon",
        "Teo Hammerstorm",
    }
