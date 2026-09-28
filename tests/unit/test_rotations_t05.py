"""Rotations de T05 (bloc C) : Arcane Power (aura et recharge du client, politique « au pull dès que prête »), Hot
Streak (Pyroblast dans la rotation de feu, cumuls avant de le lancer choisis par le build), Missile Barrage (décharge
Arcane Missiles de la rotation arcane), portée de Flame Throwing et d'Arcane Geometry.

Valeurs citées : `talents.json` (Arcane Power : 15 s, +30 % de dégâts, +30 % de coût ; Hot Streak : 25 % par cumul,
3 cumuls, durée 20 s au build 70009 (`duration_s`, notes de Blizzard du 24/09/2026) ; Missile Barrage : 40 % sur
Arcane Blast, 20 % sur Fireball, Frostbolt, Frostfire Bolt, canalisation 50 % plus courte, coût réduit de 100 % ;
Flame Throwing et Arcane Geometry : +3 / +6 m) ; recharge d'Arcane Power 180 000 ms (`SpellCooldowns`, fixture
wago 70009) ; Pyroblast rang 1 : 6 s d'incantation (`spells.json`). Critique relevé sur la fiche (valeur de test) pour
rendre les critiques fréquents."""

import itertools
import random

import pytest

from forever.engine.buffs import (
    arcane_power_pull,
    arcane_power_share,
    arcane_power_window,
    hot_streak_buffs,
    hot_streak_rules,
    missile_barrage_buffs,
    missile_barrage_chance,
)
from forever.engine.cast import expected_cast
from forever.engine.casting import cast_time
from forever.engine.character import character
from forever.engine.movement import spell_range
from forever.engine.spells import best_rank
from forever.engine.talents import check_build
from forever.sim.leveling_analytic import arcane_cycle, kill_analytic
from forever.sim.leveling_mc import kill_mc, mc

ARC40 = {
    "arcaneFocus": 5,
    "improvedChanneling": 1,
    "arcaneConcentration": 5,
    "arcaneSubtlety": 2,
    "arcaneImpact": 3,
    "arcaneBlast": 1,
    "arcaneGeometry": 1,
    "arcaneMeditation": 3,
    "missileBarrage": 1,
    "presenceOfMind": 1,
    "arcaneMind": 4,
    "arcaneInstability": 3,
    "arcanePower": 1,
}
ARC40_NO_AP = {**ARC40, "arcanePower": 0}
ARC40_NO_MB = {**ARC40, "missileBarrage": 0}
FIRE25 = {"improvedFireball": 5, "wakeOfFire": 2, "ignite": 5, "flameThrowing": 2, "pyroblast": 1, "hotStreak": 1}
FIRE25_NO_HS = {**FIRE25, "hotStreak": 0}
HIGH_CRIT = {"spell_crit": 0.5}
HS_SPELLS = ("fireball", "frostfire_bolt", "fire_blast", "scorch")
SEED_MODE = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}


def test_builds_are_legal(game_data):
    assert check_build(game_data, ARC40, 40) == []
    assert check_build(game_data, FIRE25, 25) == []


# --- Arcane Power ----------------------------------------------------------------------------------------------


def test_arcane_power_window_reads_talent_and_client(game_data):
    assert arcane_power_window(game_data, ARC40) == (15.0, 180.0)
    assert arcane_power_window(game_data, ARC40_NO_AP) is None


def test_session_clock_brings_the_aura_back_every_ceil_cooldown_over_cycle_fights():
    window = (15.0, 180.0)
    for cycle, every in ((50.0, 4), (61.0, 3), (200.0, 1)):
        clock, ready_at, flags = 0.0, 0.0, []
        for _ in range(12):
            ready, ready_at = arcane_power_pull(clock, ready_at, window)
            flags.append(ready)
            clock += cycle
        assert flags == [i % every == 0 for i in range(12)], cycle
    assert arcane_power_pull(0.0, 0.0, None) == (False, 0.0)


def test_analytic_share_of_fights_with_the_aura():
    assert arcane_power_share(50.0, 180.0) == pytest.approx(50.0 / 180.0)
    assert arcane_power_share(200.0, 180.0) == 1.0


def _kill(gd, pts, ready, rng=None, log=None, **opts):
    ch = character(gd, 40, "Orc")
    return kill_mc(
        gd,
        40,
        pts,
        ch,
        "arcane",
        rng or random.Random(5),
        log,
        ab_dump="arcane_missiles",
        arcane_power_ready=ready,
        **opts,
    )


def test_arcane_power_raises_cost_and_damage_inside_the_window_only(game_data):
    on, off = [], []
    _kill(game_data, ARC40, True, log=on)
    _kill(game_data, ARC40, False, log=off)
    inside = [(a, b) for a, b in zip(on, off, strict=False) if a.t < 15.0]
    after = [(a, b) for a, b in zip(on, off, strict=False) if 15.0 <= a.t < 25.0]
    assert len(inside) >= 4 and len(after) >= 2
    for a, b in inside + after:
        assert (a.t, a.key, a.stacks, a.crit) == (b.t, b.key, b.stacks, b.crit)
    for a, b in inside:
        assert a.cost == pytest.approx(b.cost * 1.30, rel=1e-12)
        assert a.dmg == pytest.approx(b.dmg * 1.30, rel=1e-12)  # multiplié, cumuls d'Arcane Blast compris
    assert any(a.stacks > 0 and a.key != "arcane_blast" and a.dmg > 0 for a, _ in inside)
    for a, b in after:
        assert a.cost == b.cost and a.dmg == b.dmg


class CountingRandom(random.Random):
    """Générateur qui note, à chaque tirage, le nombre de lancers déjà journalisés."""

    def __init__(self, seed, log):
        super().__init__(seed)
        self.marks, self.log = [], log

    def random(self):
        self.marks.append(len(self.log))
        return super().random()


def test_arcane_power_draws_no_random_number(game_data):
    on, off = [], []
    r_on, r_off = CountingRandom(5, on), CountingRandom(5, off)
    _kill(game_data, ARC40, True, rng=r_on, log=on)
    _kill(game_data, ARC40, False, rng=r_off, log=off)
    first = len([c for c in off if c.t < 25.0])
    assert [m for m in r_on.marks if m < first] == [m for m in r_off.marks if m < first]


def test_arcane_power_option(game_data):
    base = mc(game_data, 40, ARC40_NO_AP, "Orc", "arcane", 40, seed=2, ab_dump="arcane_missiles")
    assert base == mc(
        game_data, 40, ARC40_NO_AP, "Orc", "arcane", 40, seed=2, ab_dump="arcane_missiles", arcane_power="off"
    )
    auto = mc(game_data, 40, ARC40, "Orc", "arcane", 40, seed=2, ab_dump="arcane_missiles")
    assert auto != mc(game_data, 40, ARC40, "Orc", "arcane", 40, seed=2, ab_dump="arcane_missiles", arcane_power="off")
    with pytest.raises(ValueError, match="arcane_power"):
        mc(game_data, 40, ARC40, "Orc", "arcane", 5, arcane_power="on")


def test_arcane_power_in_the_analytic_model(game_data):
    auto = kill_analytic(game_data, 40, ARC40, "Orc", "arcane", ab_dump="arcane_missiles")
    off = kill_analytic(game_data, 40, ARC40, "Orc", "arcane", ab_dump="arcane_missiles", arcane_power="off")
    assert auto["combat"] < off["combat"]
    plain = kill_analytic(game_data, 40, ARC40_NO_AP, "Orc", "arcane", ab_dump="arcane_missiles")
    assert plain == kill_analytic(
        game_data, 40, ARC40_NO_AP, "Orc", "arcane", ab_dump="arcane_missiles", arcane_power="off"
    )


def test_seed_mode_never_uses_arcane_power(game_data):
    pts = {"improvedFrostbolt": 5, "arcanePower": 1}
    base = mc(game_data, 30, pts, "Orc", "frost", 30, seed=4, **SEED_MODE)
    assert base == mc(game_data, 30, pts, "Orc", "frost", 30, seed=4, arcane_power="off", **SEED_MODE)
    assert kill_analytic(game_data, 30, pts, "Orc", "frost", **SEED_MODE) == kill_analytic(
        game_data, 30, pts, "Orc", "frost", arcane_power="off", **SEED_MODE
    )


# --- Hot Streak ------------------------------------------------------------------------------------------------


def test_hot_streak_rules(game_data):
    assert hot_streak_rules(game_data, FIRE25) == (20.0, 0.25, 3)
    assert hot_streak_rules(game_data, FIRE25_NO_HS) is None
    assert hot_streak_buffs(game_data, FIRE25, 3) == {"cast_reduction": 0.75}
    assert hot_streak_buffs(game_data, FIRE25, 0) == {}


def test_hot_streak_shortens_pyroblast(game_data):
    ch = character(game_data, 25, "Orc")
    r = best_rank(game_data, "pyroblast", 25, FIRE25)
    assert r.cast_time_s == 6.0
    assert cast_time(game_data, "pyroblast", r, FIRE25, ch, hot_streak_buffs(game_data, FIRE25, 1)) == 4.5
    assert cast_time(game_data, "pyroblast", r, FIRE25, ch, hot_streak_buffs(game_data, FIRE25, 3)) == 1.5


@pytest.mark.parametrize(
    ("rotation", "pts", "opts"),
    [
        ("frost", {**FIRE25, "improvedFrostbolt": 0}, {"hs_stacks": 2}),
        ("fire", FIRE25_NO_HS, {"hs_stacks": 2}),
        ("fire", FIRE25, {"hs_stacks": 0}),
        ("fire", FIRE25, {"hs_stacks": 4}),
        ("fire", FIRE25, {"hs_stacks": 2, **SEED_MODE}),
    ],
)
def test_hs_stacks_is_refused_where_it_has_no_meaning(game_data, rotation, pts, opts):
    refused = r"hs_stacks (sans effet|sans le talent|\d+ hors de)"  # pas « option inconnue »
    with pytest.raises(ValueError, match=refused):
        kill_analytic(game_data, 25, pts, "Orc", rotation, **opts)
    with pytest.raises(ValueError, match=refused):
        mc(game_data, 25, pts, "Orc", rotation, 3, **opts)


def _fire_log(gd, pts, seed, **opts):
    log = []
    kill_mc(gd, 25, pts, character(gd, 25, "Orc", HIGH_CRIT), "fire", random.Random(seed), log, **opts)
    return log


def test_pyroblast_enters_the_fire_rotation_after_enough_crits(game_data):
    for n in (1, 2, 3):
        pyros = 0
        for seed in range(6):
            log = _fire_log(game_data, FIRE25, seed, hs_stacks=n)
            crits = 0
            for c in log:
                if c.key == "pyroblast":
                    assert crits >= n, (n, seed, log)
                    crits, pyros = 0, pyros + 1
                elif c.key in HS_SPELLS and c.crit:
                    crits += 1
        assert pyros > 0, n
    for seed in range(6):
        assert all(c.key != "pyroblast" for c in _fire_log(game_data, FIRE25_NO_HS, seed))


def test_fewer_stacks_cast_more_pyroblasts(game_data):
    def count(n):
        return sum(c.key == "pyroblast" for s in range(10) for c in _fire_log(game_data, FIRE25, s, hs_stacks=n))

    assert count(1) > count(3)


def test_hot_streak_in_the_analytic_model(game_data):
    hs = kill_analytic(game_data, 25, FIRE25, "Orc", "fire", HIGH_CRIT)
    assert hs == kill_analytic(game_data, 25, FIRE25, "Orc", "fire", HIGH_CRIT, hs_stacks=3)
    assert hs != kill_analytic(game_data, 25, FIRE25, "Orc", "fire", HIGH_CRIT, hs_stacks=1)
    assert hs != kill_analytic(game_data, 25, FIRE25_NO_HS, "Orc", "fire", HIGH_CRIT)


# --- Missile Barrage -------------------------------------------------------------------------------------------


def test_missile_barrage_rules(game_data):
    assert missile_barrage_chance(game_data, ARC40, "arcane_blast") == 0.40
    for key in ("fireball", "frostbolt", "frostfire_bolt"):
        assert missile_barrage_chance(game_data, ARC40, key) == 0.20
    assert missile_barrage_chance(game_data, ARC40, "arcane_missiles") == 0.0
    assert missile_barrage_chance(game_data, ARC40_NO_MB, "arcane_blast") == 0.0
    assert missile_barrage_buffs(game_data, ARC40) == {"cast_reduction": 0.5, "cost": -1.0}
    assert missile_barrage_buffs(game_data, ARC40_NO_MB) == {}


def _missile_durations(gd, pts):
    ch = character(gd, 40, "Orc")
    full = cast_time(gd, "arcane_missiles", best_rank(gd, "arcane_missiles", 40, pts), pts, ch)
    out = []
    for seed in range(5):
        log = []
        _kill(gd, pts, False, rng=random.Random(seed), log=log)
        out += [(round(b.t - a.t, 9), b.cost) for a, b in itertools.pairwise(log) if b.key == "arcane_missiles"]
    return full, out


def test_missile_barrage_halves_the_dump_and_makes_it_free(game_data):
    full, durations = _missile_durations(game_data, ARC40)
    assert {d for d, _ in durations} <= {full, full / 2}
    assert any(d == full / 2 for d, _ in durations)
    assert all(cost == 0 for d, cost in durations if d == full / 2)
    full0, durations0 = _missile_durations(game_data, ARC40_NO_MB)
    assert all(d == full0 for d, _ in durations0)


def test_missile_barrage_in_the_arcane_cycle(game_data):
    ch = character(game_data, 40, "Orc")
    with_mb = arcane_cycle(game_data, 40, ARC40, ch, ab_dump="arcane_missiles")
    without = arcane_cycle(game_data, 40, ARC40_NO_MB, ch, ab_dump="arcane_missiles")
    ab = expected_cast(game_data, "arcane_blast", 40, ARC40, ch, spell_level="character")
    am = expected_cast(game_data, "arcane_missiles", 40, ARC40, ch, spell_level="character")
    n = with_mb["ab_casts"]
    p = 1 - (1 - 0.40 * ab["hit"]) ** n
    assert with_mb["time_s"] == pytest.approx(without["time_s"] - p * 0.5 * am["cast_s"], rel=1e-12)
    assert with_mb["mana"] == pytest.approx(without["mana"] - p * am["mana"], rel=1e-12)
    assert with_mb["dmg"] == pytest.approx(without["dmg"], rel=1e-12)


# --- Portée : Flame Throwing, Arcane Geometry ------------------------------------------------------------------


def test_flame_throwing_and_arcane_geometry_extend_the_range(game_data):
    ft, ag = {"flameThrowing": 2}, {"arcaneGeometry": 2}
    assert spell_range(game_data, "fireball", ft) == 35 + 6
    assert spell_range(game_data, "fire_blast", ft) == 20 + 6
    assert spell_range(game_data, "frostfire_bolt", ft) == 35 + 6
    assert spell_range(game_data, "arcane_missiles", ag) == 30 + 6
    assert spell_range(game_data, "frostbolt", {**ft, **ag}) == spell_range(game_data, "frostbolt", {})
    assert spell_range(game_data, "fireball", ft, rules="seed") == 35
    assert spell_range(game_data, "arcane_missiles", ag, rules="seed") == 30


def test_range_talents_change_the_forever_simulation_only(game_data):
    plain = {"improvedFireball": 5}
    ft = {**plain, "flameThrowing": 2}
    assert kill_analytic(game_data, 20, ft, "Orc", "fire") != kill_analytic(game_data, 20, plain, "Orc", "fire")
    assert kill_analytic(game_data, 20, ft, "Orc", "fire", **SEED_MODE) == kill_analytic(
        game_data, 20, plain, "Orc", "fire", **SEED_MODE
    )
    assert mc(game_data, 20, ft, "Orc", "fire", 30, seed=1, **SEED_MODE) == mc(
        game_data, 20, plain, "Orc", "fire", 30, seed=1, **SEED_MODE
    )
