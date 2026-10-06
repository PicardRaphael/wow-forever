"""PNJ élites, rares et boss écartés automatiquement de la courbe d'après Questie, raison écrite (T08d, bloc J).

Réponse de l'utilisateur du 2026-10-06 : les nouveaux PNJ des journaux de 1.60.1.70170 entrent dans une révision
suivante, avec écartement automatique de la courbe des PV par niveau des PNJ élites, rares et boss d'après Questie
(`rank`, référence `creature_template` de cmangos citée par `npcDB.lua`), raison écrite dans `curve_excluded`. Un PNJ
inconnu de Questie reste dans la courbe. Questie de fixture : Owl Companion (5945) au rang 1, Lost Soul (1531) au
rang 4, Dire Mottled Boar (3099) au rang 0. Valeurs de PV synthétiques."""

from conftest import FIXTURES, LOCAL_VERSION

from forever.pipeline.monsters import build_monsters
from forever.pipeline.questie import RANK_LABELS, read_questie

QUESTIE = FIXTURES / "questie" / "11.38.0"


def obs(npc_id, level, max_hp, name="PNJ"):
    return {"npc_id": npc_id, "name": name, "level": level, "max_hp": max_hp, "guids": 1, "ui_map_id": 1411, "log": "x"}


FOUND = [
    obs(5945, 5, 300, "Owl Companion"),
    obs(1531, 6, 400, "Lost Soul"),
    obs(3099, 6, 240, "Dire Mottled Boar"),
]


def excluded(table):
    return {e["npc_id"]: e for e in table["curve_excluded"]}


def test_rank_labels_follow_the_cmangos_reference():
    assert RANK_LABELS == {1: "élite", 2: "élite rare", 3: "boss", 4: "rare"}


def test_elite_and_rare_npcs_are_excluded_with_a_written_reason():
    table = build_monsters(FOUND, read_questie(QUESTIE), LOCAL_VERSION)
    found = excluded(table)
    assert set(found) == {5945, 1531}
    assert "élite" in found[5945]["reason"] and "Questie" in found[5945]["reason"]
    assert "rare" in found[1531]["reason"] and "Questie" in found[1531]["reason"]
    assert found[5945]["levels"] == [5] and found[1531]["levels"] == [6]
    assert table["npcs"]["5945"]["levels"]["5"]["max_hp"] == 300  # toujours mesuré
    six = table["hp_by_level"]["6"]
    assert (six["value"], six["n_npcs"]) == (240, 1)  # seul le PNJ normal entre dans la courbe


def test_a_reason_given_by_the_user_is_never_replaced():
    table = build_monsters(FOUND, read_questie(QUESTIE), LOCAL_VERSION, curve_exclude={5945: "raison de l'utilisateur"})
    assert excluded(table)[5945]["reason"] == "raison de l'utilisateur"
    assert "Questie" in excluded(table)[1531]["reason"]


def test_an_npc_unknown_to_questie_stays_in_the_curve():
    table = build_monsters([obs(999999, 6, 500, "Inconnu"), *FOUND], read_questie(QUESTIE), LOCAL_VERSION)
    assert 999999 not in excluded(table)
    assert table["hp_by_level"]["6"]["n_npcs"] == 2


def test_without_questie_nothing_is_excluded_automatically():
    table = build_monsters(FOUND, None, LOCAL_VERSION)
    assert table["curve_excluded"] == []
