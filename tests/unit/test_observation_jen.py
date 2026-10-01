"""Preuve en jeu des ratios du client (T08b, accord de l'utilisateur du 2026-10-01) : Jen, Mage orc niveau 19,
Intelligence relevée sur la fiche. La révision 4 (ratios du client) prédit la mana maximale exacte et la critique des
sorts rendue par le jeu (`GetSpellCritChance`, ForeverLogger) ; la révision 3 (estimations de fm.py) s'en écarte
davantage. Valeurs : `tests/fixtures/observations/jen_niveau_19.json`."""

import pytest
from conftest import FIXTURES, read_json

from forever.engine import character
from forever.gamedata import ablated, build_game_data
from forever.store import load_version

OBS = read_json(FIXTURES / "observations" / "jen_niveau_19.json")
PERCENT = 100.0  # conversion d'unité : fraction -> pourcentage


@pytest.fixture
def predictions(make_deps):
    version = load_version(make_deps())
    over = {"intellect": float(OBS["intellect"]), "crit_gear": OBS["gear_crit_pct"] / PERCENT}
    r4 = character(build_game_data(version), OBS["level"], OBS["race"], over)
    with ablated({"int_per_crit", "base_mana"}):
        r3 = character(build_game_data(version), OBS["level"], OBS["race"], over)
    return r3, r4


def test_client_ratios_predict_the_observed_mana(predictions):
    r3, r4 = predictions
    assert round(r4.mana) == OBS["mana_max"]
    assert abs(r4.mana - OBS["mana_max"]) < abs(r3.mana - OBS["mana_max"])


def test_client_ratios_predict_the_observed_spell_crit(predictions):
    r3, r4 = predictions
    assert r4.crit * PERCENT == pytest.approx(OBS["spell_crit_logger_pct"], abs=0.01)
    for observed in (OBS["spell_crit_logger_pct"], OBS["crit_sheet_pct"]):
        assert abs(r4.crit * PERCENT - observed) < abs(r3.crit * PERCENT - observed)
