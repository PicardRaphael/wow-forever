"""Valeurs exactes du moteur pour le personnage de référence du seed (registres A3, A17, A21, B1, B11, B16, C2, G4, H1).

Personnage : niveau 60, Orc, 500 de puissance des sorts, 10 % de critique (seed/forever-mage/tests/run_all.py).
Valeurs attendues calculées avec seed/forever-mage/scripts/fm.py le 2026-09-27 ; rangs et portées :
seed/forever-mage/data/1.60.1.70009/spells.json."""

import pytest

from forever.engine import Rank, best_rank, cast_time, character, coefficient, expected_cast, hit_chance


def approx(x):
    return pytest.approx(x, rel=1e-12, abs=1e-15)


@pytest.fixture
def ch(game_data):
    return character(game_data, 60, "Orc", {"sp": 500, "spell_crit": 0.10})


def test_frostbolt_values(game_data, ch):
    e = expected_cast(game_data, "frostbolt", 60, {}, ch)
    assert e["key"] == "frostbolt" and e["school"] == "frost"
    assert e["rank"] == Rank(11, 60, 457, 493, 0, 0, 3.0, 290, 0)
    assert e["hit"] == approx(0.96)
    assert e["crit"] == approx(0.1)
    assert e["crit_mult"] == 1.5
    assert e["dmg_mult"] == 1.0
    assert e["direct_per_hit"] == approx(926.25)
    assert e["dmg"] == approx(889.2)
    assert (e["dot"], e["ignite"]) == (0.0, 0.0)
    assert e["mana"] == approx(290.0)
    assert e["cast_s"] == 3.0
    assert e["range_yd"] == 30
    assert e["cooldown_s"] == 0


def test_fireball_values(game_data, ch):
    e = expected_cast(game_data, "fireball", 60, {}, ch)
    assert e["dot"] == approx(63.0)  # DoT de 60 qui critique : 60 × (1 + 0,1 × 0,5)
    assert e["direct_per_hit"] == approx(1032.15)
    assert e["dmg"] == approx(1051.344)
    assert e["range_yd"] == 35


def test_arcane_blast_mana_pct(game_data, ch):
    e = expected_cast(game_data, "arcane_blast", 60, {"arcaneBlast": 1}, ch)
    assert e["mana"] == approx(182.265)
    assert e["mana"] == approx(0.15 * ch.base_mana)


def test_talent_rank_mana_estimate(game_data, ch):
    """Rang 1 de Pyroblast sans coût publié : 0,75 × coût du premier rang publié (150), estimation du seed."""
    e = expected_cast(game_data, "pyroblast", 20, {"pyroblast": 1}, ch)
    assert e["rank"].position == 1
    assert e["rank"].mana is None
    assert e["mana"] == approx(112.5)


def test_hit_by_level_diff(game_data, ch):
    assert hit_chance(game_data, "frost", 0, {}, ch) == approx(0.96)
    # T04b, décision 4 : cible plus basse, 4 % (écart 0) + écart × 1 %, plancher 1 % (règle Classic, suppose)
    assert hit_chance(game_data, "frost", -1, {}, ch) == approx(0.97)
    assert hit_chance(game_data, "frost", -2, {}, ch) == approx(0.98)
    assert hit_chance(game_data, "frost", -3, {}, ch) == approx(0.99)
    assert hit_chance(game_data, "frost", -8, {}, ch) == approx(0.99)
    assert hit_chance(game_data, "frost", 3, {}, ch) == approx(0.83)
    assert hit_chance(game_data, "frost", 7, {}, ch) == approx(0.61)  # au-delà de la table : dernière ligne


def test_coefficient_values(game_data):
    ranks = game_data.spells["frostbolt"].ranks
    assert coefficient(game_data, "frostbolt", ranks[1]) == approx(0.26871428571428574)
    assert coefficient(game_data, "frostbolt", ranks[10]) == approx(0.8142857142857142)


def test_improved_frostbolt_gcd_floor(game_data, ch):
    rank2 = game_data.spells["frostbolt"].ranks[1]
    assert cast_time(game_data, "frostbolt", rank2, {"improvedFrostbolt": 3}, ch) == 1.5


def test_range_values(game_data, ch):
    ranges = {key: expected_cast(game_data, key, 60, {}, ch)["range_yd"] for key in ("frostbolt", "fireball")}
    ranges["fire_blast"] = expected_cast(game_data, "fire_blast", 60, {}, ch)["range_yd"]
    assert ranges == {"frostbolt": 30, "fireball": 35, "fire_blast": 20}
    # frost_nova n'a pas de portée publiée : repli spell.default_range_yd (suppose)
    assert game_data.spells["frost_nova"].range_yd is None
    assert expected_cast(game_data, "frost_nova", 60, {}, ch)["range_yd"] == 30


def test_talent_spell_requires_talent(game_data, ch):
    assert best_rank(game_data, "ice_lance", 60, {}) is None
    assert expected_cast(game_data, "ice_lance", 60, {}, ch) is None
    r = best_rank(game_data, "ice_lance", 20, {"iceLance": 1})
    assert r is not None and r.position == 1


def test_ice_lance_frozen_multiplier(game_data, ch):
    """Ice Lance contre cible gelée : dégâts de base × frozen_mult du sort (4.0 dans spells.json), ignoré si demandé."""
    pts = {"iceLance": 1}
    free = expected_cast(game_data, "ice_lance", 60, pts, ch)
    frozen = expected_cast(game_data, "ice_lance", 60, pts, ch, frozen=True)
    ignored = expected_cast(game_data, "ice_lance", 60, pts, ch, frozen=True, frozen_mult=False)
    assert frozen["direct_per_hit"] == approx(4.0 * free["direct_per_hit"])
    assert ignored["direct_per_hit"] == approx(free["direct_per_hit"])
