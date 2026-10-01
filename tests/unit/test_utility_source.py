"""Utilitaires du Mage selon le mode (T08b, bloc B, D2) : en mode forever, niveaux, recharges, durées, coupure de
Counterspell et coûts en pourcentage du mana de base lus dans `classes.json` (décodé du client) quand il les porte ;
en mode seed, copies du seed (`_seed_spells.json`). Valeurs attendues lues dans les données installées."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

PERCENT = 100.0  # conversion d'unité : coût en pourcentage (classes.json) -> fraction (spells.json)
MAGE = read_json(DATA_DIR / LOCAL_VERSION / "classes.json")["classes"]["Mage"]["spells"]
SEED = read_json(DATA_DIR / LOCAL_VERSION / "_seed_spells.json")


def first(key: str) -> dict:
    return MAGE[key]["ranks"][0]


def test_forever_mode_reads_classes_json(game_data):
    u = game_data.utility
    assert u.blink_level == first("blink")["level"]
    assert u.blink_cooldown_s == first("blink")["cooldown_s"]
    assert u.counterspell_level == first("counterspell")["level"]
    assert u.counterspell_cooldown_s == first("counterspell")["cooldown_s"]
    assert u.counterspell_lockout_s == MAGE["counterspell"]["pvp"]["interrupt"]["lockout_s"]
    assert u.evocation_level == first("evocation")["level"]
    assert u.evocation_duration_s == first("evocation")["duration_s"]
    assert [lv for lv, _ in u.ice_barrier] == [r["level"] for r in MAGE["iceBarrier"]["ranks"]]


def test_forever_mode_keeps_seed_values_the_client_does_not_carry(game_data):
    seed = SEED["utility"]
    assert [a for _, a in game_data.utility.ice_barrier] == [r[1] for r in seed["ice_barrier"]["ranks"]]
    assert game_data.utility.evocation_regen_mult == seed["evocation"]["regen_mult"]


def test_forever_mode_mana_pct_base_from_classes_json(game_data):
    assert game_data.spells["arcane_blast"].mana_pct_base == pytest.approx(
        first("arcaneBlast")["cost"]["pct"] / PERCENT
    )


def test_seed_mode_keeps_seed_copies(seed_game_data):
    u, seed = seed_game_data.utility, SEED["utility"]
    assert u.blink_level == seed["blink"]["level"]
    assert u.counterspell_level == seed["counterspell"]["level"]
    assert u.evocation_level == seed["evocation"]["level"]
    assert [lv for lv, _ in u.ice_barrier] == [r[0] for r in seed["ice_barrier"]["ranks"]]
    assert seed_game_data.spells["arcane_blast"].mana_pct_base == SEED["spells"]["arcane_blast"]["mana_pct_base"]


def test_utility_source_is_named(game_data, seed_game_data):
    assert game_data.utility_source == "classes.json"
    assert seed_game_data.utility_source == "_seed_spells.json"
