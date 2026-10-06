"""Correction Questie -> Forever par Theil-Sen pondéré (décision de l'utilisateur du 2026-10-06, T08d, MON6).

Pente = médiane pondérée des pentes entre chaque paire de niveaux au rapport médian supérieur à 1, poids n_i × n_j
(nombre de PNJ des deux niveaux) ; ordonnée = médiane des écarts « rapport − pente × niveau ». Valeurs synthétiques,
calculées à la main : niveaux 10, 12 et 14 à 1,1, 1,2 et 1,3 (trois PNJ chacun), niveau 16 à 2,0 (un seul PNJ, point
isolé). Pentes : 0,05 entre les trois premiers niveaux (poids 9 chacune, 27 en tout) ; 0,15, 0,2 et 0,35 vers le
niveau 16 (poids 3 chacune, 9 en tout) ; la médiane pondérée (moitié du poids total : 18) vaut 0,05. Écarts : 0,6,
0,6, 0,6 et 1,2, médiane 0,6 ; genou (1 − 0,6) / 0,05 = 8. Les moindres carrés non pondérés donnaient 0,14 :
le point isolé y décidait de la pente."""

import pytest

from forever.pipeline.monsters import fit_questie_correction


def npc(level, ratio, i):
    return {"name": f"PNJ {i}", "rank": 0, "levels": {str(level): {"max_hp": round(100 * ratio), "questie_hp": 100}}}


def npcs(spec):
    out, i = {}, 0
    for level, ratio, count in spec:
        for _ in range(count):
            i += 1
            out[str(i)] = npc(level, ratio, i)
    return out


SPEC = [(10, 1.1, 3), (12, 1.2, 3), (14, 1.3, 3), (16, 2.0, 1)]


def test_an_isolated_level_no_longer_decides_the_slope():
    fit = fit_questie_correction(npcs(SPEC))["fit"]
    assert fit["slope"] == pytest.approx(0.05, rel=1e-9)
    assert fit["intercept"] == pytest.approx(0.6, rel=1e-9)
    assert fit["knee_level"] == pytest.approx(8.0, rel=1e-9)
    assert fit["points"] == 4


def test_the_method_is_named_in_the_table():
    corr = fit_questie_correction(npcs(SPEC))
    assert "Theil-Sen pondéré" in corr["method"]


def test_removing_the_isolated_level_barely_moves_the_slope():
    with_point = fit_questie_correction(npcs(SPEC))["fit"]["slope"]
    without = fit_questie_correction(npcs(SPEC[:3]))["fit"]["slope"]
    assert with_point == pytest.approx(without, rel=1e-9)


def test_weights_follow_the_number_of_npcs():
    # niveau 16 porté à 9 PNJ : ses trois pentes pèsent 27 chacune (81 sur 108) ; cumul 27 à 0,05, 54 à 0,15 :
    # la médiane pondérée (première pente où le cumul atteint la moitié, 54) passe à 0,15
    heavy = [(10, 1.1, 3), (12, 1.2, 3), (14, 1.3, 3), (16, 2.0, 9)]
    assert fit_questie_correction(npcs(heavy))["fit"]["slope"] == pytest.approx(0.15, rel=1e-9)
