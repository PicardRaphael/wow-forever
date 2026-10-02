"""PV des monstres dans le moteur (décision 5 du plan T04b) : `monsters.json` installé (deux journaux réels du
2026-09-27 et Questie 11.38.0 local, Sarilus Foulborne exclu de l'ajustement ; depuis 1.60.1.70170 révision 2, le
journal du 2026-10-02 aussi, PNJ hors norme écartés de la courbe) ; modèle du seed
(`leveling.json.mob_model.hp_anchors`, interpolé) pour la parité. Mêmes observations que les fixtures : mêmes
rapports que tests/unit/test_monsters_correction.py."""

import pytest

from forever.engine.monsters import corrected_questie_hp, mob_hp, questie_ratio

SLOPE, INTERCEPT = 0.023805491386132475, 0.8228887385415422  # 1.60.1.70170 révision 2 (13 niveaux)


def test_installed_correction(game_data):
    corr = game_data.monsters.correction
    assert corr is not None and (corr.level_min, corr.level_max) == (1, 22)
    assert corr.slope == pytest.approx(SLOPE, rel=1e-12) and corr.intercept == pytest.approx(INTERCEPT, rel=1e-12)
    assert corr.levels[12] == pytest.approx(1.1012145748987854, rel=1e-12)


def test_questie_ratio(game_data):
    # Niveau 8 : dans la plage mesurée sans mesure à ce niveau (16 est mesuré depuis la révision 2) : la droite.
    assert questie_ratio(game_data, 8) == (pytest.approx(SLOPE * 8 + INTERCEPT, rel=1e-12), "probable")
    assert questie_ratio(game_data, 30) == (pytest.approx(SLOPE * 30 + INTERCEPT, rel=1e-12), "suppose")


def test_corrected_questie_hp(game_data):
    hp = corrected_questie_hp(game_data, 356, 8)
    assert (hp.value, hp.certainty) == (361, "probable") and "Questie corrigé" in hp.source


def test_mob_hp_measured_first(game_data):
    hp = mob_hp(game_data, 12)
    assert (hp.value, hp.certainty) == (272, "certain")
    hp16 = mob_hp(game_data, 16)
    assert hp16.certainty == "probable" and 385 < hp16.value < 473
    hp23 = mob_hp(game_data, 23)  # au-delà de la plage mesurée (1 à 22 depuis la révision 2)
    assert hp23.certainty == "suppose" and "Questie corrigé" in hp23.source


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
