"""Multiplicateurs de dégâts ajoutés en T04e et cumul des bonus en pourcentage (registres A20, B15).

Sources : Improved Cone of Cold : talents.json `improvedConeOfCold` (12 / 23 / 35 %, courbe Trait 83066 du client,
tests/fixtures/wago/1.60.1.70009/enUS/CurvePoint.csv ; décision 77 ; ignoré par le seed) ; Arcane Power : talents.json
`arcanePower` (15 s, +30 % de dégâts, +30 % de coût) ; Fire Vulnerability : spell_scaling.json `auras` (client : 3 %
par cumul, 5 cumuls) ; Cone of Cold r5 : spells.json (328-358), coefficient du client 0.12899999321 (SpellEffect.csv).
Concordance : exemple V13 de docs/research/videos/BVSgeHp3sWU.md (589,4)."""

import csv

import pytest
from conftest import WAGO_70009

from forever.engine import character, dmg_mult, expected_cast, mana_cost
from forever.engine.buffs import arcane_power_buffs, fire_vulnerability_buffs, merge_buffs

PERCENT = 100.0


def approx(x):
    return pytest.approx(x, rel=1e-12, abs=1e-15)


@pytest.fixture
def ch534(game_data):
    return character(game_data, 60, "Orc", {"sp": 534, "spell_crit": 0.0})


def test_improved_cone_of_cold(game_data, ch534):
    """Cone of Cold r5 à 534, Piercing Ice 3/3 et Improved Cone of Cold 3/3 : (343 + 0,129 × 534) × 1,06 × 1,35."""
    pts = {"piercingIce": 3, "improvedConeOfCold": 3}
    e = expected_cast(game_data, "cone_of_cold", 60, pts, ch534)
    assert e["crit"] == 0.0
    assert e["direct_per_hit"] == approx((343 + 0.12899999321 * 534) * 1.06 * 1.35)
    assert e["direct_per_hit"] == approx(589.4088608113944)


def test_improved_cone_of_cold_ranks_come_from_client_curve(game_data):
    """Rangs 1 à 3 : 12 / 23 / 35 % en mode forever, courbe Trait 83066 du client (CurvePoint.csv), qui remplace la
    valeur brute 15 de SpellEffect 11190 (Classic : 15 / 25 / 35) ; rien sur les autres sorts."""
    with (WAGO_70009 / "enUS" / "CurvePoint.csv").open(encoding="utf-8", newline="") as f:
        rows = sorted((int(r["OrderIndex"]), float(r["Pos_1"])) for r in csv.DictReader(f) if r["CurveID"] == "83066")
    curve = tuple(v for _, v in rows)
    assert curve == (12, 23, 35)
    assert tuple(r[0] for r in game_data.talents["improvedConeOfCold"].ranks) == curve
    for n, pct in enumerate(curve, start=1):
        m = dmg_mult(game_data, "frost", {"improvedConeOfCold": n}, key="cone_of_cold")
        assert m == approx(1 + pct / PERCENT)
    assert dmg_mult(game_data, "frost", {"improvedConeOfCold": 1}, key="cone_of_cold") == approx(1.12)
    assert dmg_mult(game_data, "frost", {"improvedConeOfCold": 3}, key="frostbolt") == 1.0
    assert dmg_mult(game_data, "frost", {"improvedConeOfCold": 3}) == 1.0


def test_improved_cone_of_cold_is_ignored_in_seed_mode(game_data, ch534):
    pts = {"improvedConeOfCold": 3}
    assert dmg_mult(game_data, "frost", pts, key="cone_of_cold", rules="seed") == 1.0
    with_talent = expected_cast(game_data, "cone_of_cold", 60, pts, ch534, rules="seed")
    without = expected_cast(game_data, "cone_of_cold", 60, {}, ch534, rules="seed")
    assert with_talent["direct_per_hit"] == without["direct_per_hit"]


def test_arcane_power_buffs(game_data, ch534):
    """+30 % de dégâts en source distincte, +30 % de coût ; aucun effet sans le talent (valeurs de talents.json)."""
    _, dmg_pct, cost_pct = game_data.talents["arcanePower"].ranks[0]
    assert (dmg_pct, cost_pct) == (30, 30)
    assert arcane_power_buffs(game_data, {}) == {}
    ap = arcane_power_buffs(game_data, {"arcanePower": 1})
    assert ap == {"dmg_sources": (dmg_pct / PERCENT,), "cost": cost_pct / PERCENT}
    r = game_data.spells["arcane_missiles"].ranks[-1]
    assert mana_cost(game_data, "arcane_missiles", r, {}, ch534, ap) == approx(1.3 * r.mana)
    plain = expected_cast(game_data, "arcane_missiles", 60, {}, ch534)
    powered = expected_cast(game_data, "arcane_missiles", 60, {}, ch534, buffs=ap)
    assert powered["dmg_mult"] == approx(1.3 * plain["dmg_mult"])
    assert powered["direct_per_hit"] == approx(1.3 * plain["direct_per_hit"])
    assert powered["mana"] == approx(1.3 * plain["mana"])


def test_fire_vulnerability(game_data):
    """5 cumuls : × 1,15 sur les sorts de feu (Givre-feu compris, suppose), rien sur le givre ni l'arcane ; 6 cumuls
    demandés -> 5 (maximum du client)."""
    fv = game_data.fire_vulnerability
    assert fire_vulnerability_buffs(game_data, 0) == {}
    assert fire_vulnerability_buffs(game_data, 3) == {"fire_vulnerability": 3}
    assert fire_vulnerability_buffs(game_data, 6) == {"fire_vulnerability": fv.max_stacks}
    five = fire_vulnerability_buffs(game_data, 5)
    assert dmg_mult(game_data, "fire", {}, five, key="fireball") == approx(1 + 5 * fv.pct_per_stack / PERCENT)
    assert dmg_mult(game_data, "fire", {}, five, key="fireball") == approx(1.15)
    assert dmg_mult(game_data, "frostfire", {}, five, key="frostfire_bolt") == approx(1.15)
    assert dmg_mult(game_data, "frost", {}, five, key="frostbolt") == 1.0
    assert dmg_mult(game_data, "arcane", {}, five, key="arcane_missiles") == 1.0


def test_damage_bonuses_stack_multiplicatively_in_forever(game_data):
    """Arcane Instability 3/3, bonus `dmg` 0,40 (4 cumuls d'Arcane Blast) et Arcane Power (0,30) : produit en forever
    (1,03 × 1,40 × 1,30), somme des bonus en seed (1,03 × 1,70)."""
    pts = {"arcaneInstability": 3}
    buffs = {"dmg": 0.40, "dmg_sources": (0.30,)}
    forever = dmg_mult(game_data, "arcane", pts, buffs, key="arcane_missiles")
    seed = dmg_mult(game_data, "arcane", pts, buffs, key="arcane_missiles", rules="seed")
    assert forever == approx(1.03 * 1.40 * 1.30)
    assert forever == approx(1.8746)
    assert seed == approx(1.03 * (1 + 0.40 + 0.30))
    assert seed == approx(1.751)
    fire = {"dmg": 0.10, "fire_vulnerability": 5}
    assert dmg_mult(game_data, "fire", {}, fire, key="fireball") == approx(1.10 * 1.15)
    assert dmg_mult(game_data, "fire", {}, fire, key="fireball", rules="seed") == approx(1 + 0.10 + 0.15)


def test_merge_buffs(game_data):
    ap = arcane_power_buffs(game_data, {"arcanePower": 1})
    merged = merge_buffs({"dmg": 0.1, "crit": 0.05}, ap, None, {"dmg": 0.2}, {"fire_vulnerability": 2})
    assert merged["dmg"] == approx(0.3)
    assert merged["crit"] == 0.05
    assert merged["cost"] == 0.3
    assert merged["dmg_sources"] == (0.3,)
    assert merged["fire_vulnerability"] == 2
    assert merge_buffs({"fire_vulnerability": 2}, {"fire_vulnerability": 4})["fire_vulnerability"] == 4
    assert merge_buffs() == {}
