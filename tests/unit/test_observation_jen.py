"""Preuve en jeu des ratios du client (T08b, accord de l'utilisateur du 2026-10-01) : Jen, Mage orc niveau 19,
Intelligence relevée sur la fiche. Les ratios du client prédisent la mana maximale exacte et la critique des sorts
rendue par le jeu (`GetSpellCritChance`, ForeverLogger). La comparaison aux estimations de fm.py passait par
l'ablation du rejeu des builds, retirée avec la recherche de build (RB1, décision 299). Valeurs :
`tests/fixtures/observations/jen_niveau_19.json`."""

import pytest
from conftest import FIXTURES, read_json

from forever.engine import character
from forever.gamedata import build_game_data
from forever.store import load_version

OBS = read_json(FIXTURES / "observations" / "jen_niveau_19.json")
PERCENT = 100.0  # conversion d'unité : fraction -> pourcentage


@pytest.fixture
def prediction(make_deps_at_pre_70450_version):
    # Relevé fait avant 1.60.1.70450, dont le racial Savage ajoute 1 % de critique à l'Orc (conftest).
    version = load_version(make_deps_at_pre_70450_version())
    over = {"intellect": float(OBS["intellect"]), "crit_gear": OBS["gear_crit_pct"] / PERCENT}
    return character(build_game_data(version), OBS["level"], OBS["race"], over)


def test_client_ratios_predict_the_observed_mana(prediction):
    assert round(prediction.mana) == OBS["mana_max"]


def test_client_ratios_predict_the_observed_spell_crit(prediction):
    assert prediction.crit * PERCENT == pytest.approx(OBS["spell_crit_logger_pct"], abs=0.01)
