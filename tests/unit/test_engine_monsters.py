"""PV des monstres dans le moteur (décision 5 du plan T04b) : `monsters.json` installé (journaux réels et Questie 11.38.0
local, PNJ exclus de l'ajustement ou de la courbe) ; modèle du seed (`leveling.json.mob_model.hp_anchors`, interpolé)
pour la parité. Depuis le 2026-10-02, les valeurs attendues sont lues dans `monsters.json` installé (droite, plage,
niveaux mesurés) : une nouvelle mesure des journaux ne touche plus ces tests, qui vérifient la règle du moteur.
Les rapports eux-mêmes sont vérifiés sur fixtures par tests/unit/test_monsters_correction.py."""

import math

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.monsters import corrected_questie_hp, mob_hp, questie_ratio

MONSTERS = read_json(DATA_DIR / LOCAL_VERSION / "monsters.json")
CORRECTION = MONSTERS["questie_correction"]
SLOPE, INTERCEPT = CORRECTION["fit"]["slope"], CORRECTION["fit"]["intercept"]
LOW, HIGH = CORRECTION["range"]
MEASURED_RATIOS = {int(k): v["ratio"] for k, v in CORRECTION["levels"].items()}
# Niveau de la plage sans rapport mesuré (la droite s'y applique), et niveau au-delà de la plage (suppose).
UNMEASURED = next((lv for lv in range(LOW, HIGH + 1) if lv not in MEASURED_RATIOS), None)
BEYOND = HIGH + 1
HP = {int(k): v for k, v in MONSTERS["hp_by_level"].items()}
JOURNAL = sorted(lv for lv, v in HP.items() if v["source"].startswith("journaux"))


def test_installed_correction(game_data):
    corr = game_data.monsters.correction
    assert corr is not None and (corr.level_min, corr.level_max) == (LOW, HIGH)
    assert corr.slope == pytest.approx(SLOPE, rel=1e-12) and corr.intercept == pytest.approx(INTERCEPT, rel=1e-12)
    for level, ratio in MEASURED_RATIOS.items():
        assert corr.levels[level] == pytest.approx(ratio, rel=1e-12), level


def test_questie_ratio(game_data):
    measured = max(MEASURED_RATIOS)
    assert questie_ratio(game_data, measured) == (pytest.approx(MEASURED_RATIOS[measured], rel=1e-12), "probable")
    if UNMEASURED is not None:
        expected = max(1.0, SLOPE * UNMEASURED + INTERCEPT)
        assert questie_ratio(game_data, UNMEASURED) == (pytest.approx(expected, rel=1e-12), "probable")
    assert questie_ratio(game_data, BEYOND) == (pytest.approx(SLOPE * BEYOND + INTERCEPT, rel=1e-12), "suppose")


def test_corrected_questie_hp(game_data):
    level = UNMEASURED if UNMEASURED is not None else BEYOND
    ratio = max(1.0, SLOPE * level + INTERCEPT)
    hp = corrected_questie_hp(game_data, 356, level)
    assert hp.value == math.floor(356 * ratio + 0.5)  # arrondi au demi supérieur, comme les PV entiers du jeu
    assert hp.certainty == ("probable" if level <= HIGH else "suppose") and "Questie corrigé" in hp.source


def test_mob_hp_measured_first(game_data):
    assert JOURNAL, "aucun niveau mesuré dans monsters.json installé"
    for level in JOURNAL:
        hp = mob_hp(game_data, level)
        assert (hp.value, hp.certainty) == (HP[level]["value"], HP[level]["certainty"]), level
    beyond = next(lv for lv in sorted(HP) if lv > HIGH and lv not in JOURNAL)
    hp = mob_hp(game_data, beyond)
    assert hp.certainty == "suppose" and "Questie corrigé" in hp.source


def test_mob_hp_seed_model(game_data):
    assert mob_hp(game_data, 12, "seed").value == 247
    assert mob_hp(game_data, 16, "seed").value == pytest.approx(328 + (484 - 328) * 1 / 5, rel=1e-12)
    assert mob_hp(game_data, 70, "seed").value == 3400  # au-delà des ancres : dernière ancre (seed)
    assert mob_hp(game_data, 12, "seed").certainty == "suppose"


def test_mob_hp_unknown_source_or_level(game_data):
    with pytest.raises(ValueError, match="mob_source"):
        mob_hp(game_data, 12, "questie")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="niveau 99"):
        mob_hp(game_data, 99)
