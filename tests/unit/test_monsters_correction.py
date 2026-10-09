"""Correction PV Questie -> Forever (décision 5 du plan T04b), sur les deux fixtures de journal et l'extrait Questie.

Rapport par niveau : médiane des rapports PV mesuré / PV Questie des PNJ normaux mesurés ; droite des moindres carrés
sur les médianes supérieures à 1 (Theil-Sen pondéré depuis la décision 190) ; rapport d'un niveau non mesuré = max(1, droite). Certitude `probable` entre le
plus bas et le plus haut niveau mesuré, `suppose` au-delà. Sarilus Foulborne (3986, PNJ de quête, rapport 1,62) est
exclu de l'ajustement et listé. Valeurs relevées par `repr()` sur les fixtures."""

import pytest
from conftest import COMBATLOG, FIXTURES, LOCAL_VERSION, REAL_LOG

from forever.engine.model import QuestieCorrection
from forever.engine.monsters import correction_ratio
from forever.pipeline.combatlog import read_log
from forever.pipeline.measure import monster_hp
from forever.pipeline.monsters import build_monsters, fit_questie_correction
from forever.pipeline.questie import read_questie

QUESTIE = FIXTURES / "questie" / "11.38.0"
SECOND_LOG = COMBATLOG / "WoWCombatLog-092726_150346.anon.txt.gz"
SARILUS = 3986
RATIOS = {
    1: 1.0,
    6: 1.0,
    7: 1.0,
    10: 1.0505050505050506,
    11: 1.0765765765765767,
    12: 1.1012145748987854,
    13: 1.1245421245421245,
    14: 1.15,
    15: 1.173780487804878,
    17: 1.2253886010362693,
}
PAIRS = {1: 1, 6: 1, 7: 1, 10: 3, 11: 7, 12: 7, 13: 6, 14: 3, 15: 1, 17: 1}
SLOPE, INTERCEPT, KNEE = 0.0246379983222087, 0.8050680234890781, 7.911843079200558


def observations(*paths):
    """Observations des fixtures sans les indicateurs de combat (décision 222) : ces tests portent sur la correction
    Questie seule ; la règle de la courbe (PNJ combattus par le joueur et non amis) a ses tests dans test_monsters.py."""
    out = []
    for path in paths:
        found, _ = monster_hp(list(read_log(path)[1]), log=path.name)
        out += [{k: v for k, v in o.items() if k not in ("fought", "reaction")} for o in found]
    return out


@pytest.fixture(scope="module")
def table():
    return build_monsters(
        observations(REAL_LOG, SECOND_LOG), read_questie(QUESTIE), LOCAL_VERSION, fit_exclude=[SARILUS]
    )


def test_schema_2(table):
    assert table["schema_version"] == 2


def test_ratio_per_measured_level(table):
    levels = table["questie_correction"]["levels"]
    assert {int(k): v["ratio"] for k, v in levels.items()} == pytest.approx(RATIOS, rel=1e-12)
    assert {int(k): v["n_pairs"] for k, v in levels.items()} == PAIRS


def test_least_squares_line_on_ratios_above_one(table):
    corr = table["questie_correction"]
    assert corr["fit"]["slope"] == pytest.approx(SLOPE, rel=1e-12)
    assert corr["fit"]["intercept"] == pytest.approx(INTERCEPT, rel=1e-12)
    assert corr["fit"]["knee_level"] == pytest.approx(KNEE, rel=1e-12)  # niveau où la droite vaut 1
    assert corr["range"] == [1, 17]


def test_excluded_npc_is_listed_with_its_ratio(table):
    (excluded,) = table["questie_correction"]["excluded"]
    assert (excluded["npc_id"], excluded["name"], excluded["level"]) == (SARILUS, "Sarilus Foulborne", 25)
    assert excluded["ratio"] == pytest.approx(927 / 573, rel=1e-12)
    kept = fit_questie_correction(table["npcs"])
    assert kept is not None and kept["fit"]["slope"] == pytest.approx(SLOPE, rel=1e-12) and kept["excluded"] == []


def test_unmeasured_level_inside_the_range_is_corrected(table):
    hp16 = table["hp_by_level"]["16"]
    assert hp16["questie_hp"] == 356 and hp16["ratio"] == pytest.approx(SLOPE * 16 + INTERCEPT, rel=1e-12)
    assert (hp16["value"], hp16["certainty"]) == (427, "probable")
    assert table["hp_by_level"]["15"]["value"] < hp16["value"] < table["hp_by_level"]["17"]["value"]
    assert "Questie corrigé" in hp16["source"]


def test_measured_levels_are_never_modified(table):
    got = {level: table["hp_by_level"][str(level)]["value"] for level in (1, 6, 7, 10, 11, 12, 13, 14, 15, 17, 25)}
    assert got == {1: 8, 6: 120, 7: 137, 10: 208, 11: 239, 12: 272, 13: 307, 14: 345, 15: 385, 17: 473, 25: 927}
    assert all("ratio" not in table["hp_by_level"][str(level)] for level in got)


def test_correction_ratio_certainty_inside_and_beyond_the_range():
    corr = QuestieCorrection(levels=RATIOS, slope=SLOPE, intercept=INTERCEPT, level_min=1, level_max=17)
    assert correction_ratio(corr, 12) == (pytest.approx(RATIOS[12], rel=1e-12), "probable")  # médiane mesurée
    assert correction_ratio(corr, 16) == (pytest.approx(SLOPE * 16 + INTERCEPT, rel=1e-12), "probable")
    assert correction_ratio(corr, 4) == (1.0, "probable")  # sous le genou
    assert correction_ratio(corr, 30) == (pytest.approx(SLOPE * 30 + INTERCEPT, rel=1e-12), "suppose")
    assert correction_ratio(None, 30) == (1.0, "suppose")  # pas de correction : Questie tel quel


def test_without_ratio_above_one_there_is_no_line():
    table = build_monsters(observations(REAL_LOG), read_questie(QUESTIE), LOCAL_VERSION)
    corr = table["questie_correction"]
    assert corr["fit"] is None and corr["range"] == [1, 7]
    assert table["hp_by_level"]["11"]["ratio"] == 1.0 and table["hp_by_level"]["11"]["certainty"] == "suppose"


def test_without_questie_there_is_no_correction():
    table = build_monsters(observations(REAL_LOG), None, LOCAL_VERSION)
    assert table["questie_correction"] is None


def test_inversions_are_listed_never_smoothed():
    npc = {"npc_id": 9999, "name": "PNJ", "level": 10, "max_hp": 500, "guids": 1, "ui_map_id": 1413, "log": "x"}
    table = build_monsters([npc], read_questie(QUESTIE), LOCAL_VERSION)
    (inversion,) = [i for i in table["inversions"] if i["level"] == 11]
    assert (inversion["previous_level"], inversion["previous"]) == (10, 500)
    assert inversion["value"] == table["hp_by_level"]["11"]["value"] < 500
