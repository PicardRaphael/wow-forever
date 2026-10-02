"""PNJ hors norme écartés de la courbe des PV par niveau et de la correction Questie (2026-10-02).

Demande de l'utilisateur du 2026-10-02, à la mesure du premier journal de 1.60.1.70170 : des PNJ normaux mesurés
au-dessus des autres PNJ de leur niveau (ours, deux PNJ d'un même niveau) restent mesurés un par un dans `npcs`, mais
n'entrent ni dans `hp_by_level` ni dans l'ajustement de la correction Questie, avec leur raison écrite dans
`monsters.json` ; un passage suivant de `forever measures refresh` les reprend. Valeurs synthétiques."""

from conftest import FIXTURES, LOCAL_VERSION

from forever.pipeline.monsters import build_monsters
from forever.pipeline.questie import read_questie
from forever.pipeline.refresh import curve_exclusions

QUESTIE = FIXTURES / "questie" / "11.38.0"
REASON = "PNJ hors norme (essai)"


def obs(npc_id, level, max_hp, name="PNJ"):
    return {"npc_id": npc_id, "name": name, "level": level, "max_hp": max_hp, "guids": 1, "ui_map_id": 1411, "log": "x"}


def test_excluded_npc_stays_measured_but_leaves_the_level_curve():
    found = [obs(1, 20, 600, "A"), obs(2, 20, 600, "B"), obs(3, 20, 700, "Ours"), obs(3, 21, 760, "Ours")]
    table = build_monsters(found, None, LOCAL_VERSION, curve_exclude={3: REASON})
    assert table["npcs"]["3"]["levels"]["20"]["max_hp"] == 700  # toujours mesuré
    twenty = table["hp_by_level"]["20"]
    assert (twenty["value"], twenty["n_npcs"], twenty["certainty"]) == (600, 2, "certain")
    assert "21" not in table["hp_by_level"]  # le seul PNJ du niveau 21 est écarté
    assert table["curve_excluded"] == [{"npc_id": 3, "name": "Ours", "levels": [20, 21], "reason": REASON}]


def test_without_exclusion_the_curve_is_unchanged():
    found = [obs(1, 20, 600), obs(2, 20, 600), obs(3, 20, 700)]
    table = build_monsters(found, None, LOCAL_VERSION)
    assert table["hp_by_level"]["20"]["n_npcs"] == 3
    assert table["curve_excluded"] == []


def test_excluded_npc_leaves_the_questie_correction_too():
    questie = read_questie(QUESTIE)
    found = [obs(5951, 1, 8, "Hare"), obs(3099, 6, 240, "Dire Mottled Boar"), obs(3099, 7, 274, "Dire Mottled Boar")]
    plain = build_monsters(found, questie, LOCAL_VERSION)
    assert plain["questie_correction"]["levels"]["6"]["n_pairs"] == 1
    table = build_monsters(found, questie, LOCAL_VERSION, curve_exclude={3099: REASON})
    assert "6" not in table["questie_correction"]["levels"] and "1" in table["questie_correction"]["levels"]
    assert {e["npc_id"] for e in table["questie_correction"]["excluded"]} == {3099}


def test_installed_exclusions_are_carried_and_new_ones_need_a_reason():
    installed = {"curve_excluded": [{"npc_id": 3, "name": "Ours", "levels": [20], "reason": "déjà écarté"}]}
    assert curve_exclusions(installed, None, None) == {3: "déjà écarté"}
    assert curve_exclusions(installed, [4], "nouvelle raison") == {3: "déjà écarté", 4: "nouvelle raison"}
    assert curve_exclusions({}, None, None) == {}
    try:
        curve_exclusions({}, [4], None)
    except ValueError as exc:
        assert "raison" in str(exc)
    else:
        raise AssertionError("une exclusion sans raison doit être refusée")
