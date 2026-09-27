"""Arcane Blast (T04c, bloc D ; registre B11, B15, I1) : aura cumulable, coût croissant, rotation arcane.

Talent `arcaneBlast` (talents.json, FC-70009) : [50, 58, 10, 175, 4, 8] = dégâts min et max, +10 % de dégâts des
autres sorts par cumul, +175 % de coût d'Arcane Blast par cumul, 4 cumuls, 8 s ; coût de base : `mana_pct_base` de
spells.json × mana de base. Coût à n cumuls : base × (1 + 1,75 n), soit × 1 ; 2,75 ; 4,5 ; 6,25 ; 8 (probable) ;
cycle de N Arcane Blast : base × Σ (1 + 1,75 i), i < N (N = 4 : × 14,5 ; N = 2 : × 3,75).
Builds légaux (10 points d'arcane avant le palier 3) : B20 (11 points), B24 (15), B30 (21)."""

import json
import random
from itertools import pairwise

import pytest

import forever.sim.leveling_analytic as analytic
from forever.cli import main
from forever.engine.buffs import (
    ArcaneBlastAura,
    arcane_blast_active,
    arcane_blast_after_cast,
    arcane_blast_bonus,
    arcane_blast_max_stacks,
)
from forever.engine.character import character
from forever.engine.mana import arcane_blast_cost, mana_cost
from forever.engine.spells import best_rank
from forever.sim.leveling_analytic import arcane_cycle, kill_analytic
from forever.sim.leveling_mc import kill_mc, mc

B20 = {"arcaneFocus": 5, "arcaneSubtlety": 2, "magicAbsorption": 2, "arcaneResilience": 1, "arcaneBlast": 1}
B24 = {**B20, "improvedFrostbolt": 4}
B30 = {**B24, "improvedFrostbolt": 5, "arcaneGeometry": 2, "arcaneImpact": 3}
B24_CC = {"arcaneFocus": 5, "arcaneConcentration": 5, "arcaneBlast": 1, "improvedFrostbolt": 4}
COST_FACTORS = [1.0, 2.75, 4.5, 6.25, 8.0]


def _base_cost(gd, level, pts):
    ch = character(gd, level)
    return arcane_blast_cost(gd, best_rank(gd, "arcane_blast", level, pts), pts, ch, 0)


def run_json(capsys, argv, deps):
    code = main([*argv, "--json"], deps)
    return code, json.loads(capsys.readouterr().out)


# --- Moteur ---------------------------------------------------------------------------------------


def test_cost_grows_with_the_stacks(game_data):
    ch = character(game_data, 20)
    rank = best_rank(game_data, "arcane_blast", 20, B20)
    base = arcane_blast_cost(game_data, rank, B20, ch, 0)
    assert base == pytest.approx(game_data.spells["arcane_blast"].mana_pct_base * ch.base_mana, rel=1e-12)
    assert base == pytest.approx(mana_cost(game_data, "arcane_blast", rank, B20, ch), rel=1e-12)
    got = [arcane_blast_cost(game_data, rank, B20, ch, n) / base for n in range(5)]
    assert got == pytest.approx(COST_FACTORS, rel=1e-12)


def test_max_stacks_come_from_the_talent(game_data):
    assert arcane_blast_max_stacks(game_data, B20) == 4
    assert arcane_blast_max_stacks(game_data, {}) == 0


def test_stacks_are_capped_and_expire(game_data):
    aura = None
    for t in range(5):  # cinq Arcane Blast à 0, 1, 2, 3 et 4 s
        aura = arcane_blast_after_cast(game_data, B20, aura, float(t))
    assert aura == ArcaneBlastAura(4, 12.0)
    assert arcane_blast_active(aura, 11.9) == 4
    assert arcane_blast_active(aura, 12.0) == 0
    assert arcane_blast_active(None, 0.0) == 0
    assert arcane_blast_after_cast(game_data, B20, aura, 13.0) == ArcaneBlastAura(1, 21.0)


def test_bonus_applies_to_other_spells_only(game_data):
    assert arcane_blast_bonus(game_data, B20, 3, for_spell="frostbolt")["dmg"] == pytest.approx(0.3, rel=1e-12)
    assert arcane_blast_bonus(game_data, B20, 3, for_spell="arcane_blast") == {}
    assert arcane_blast_bonus(game_data, B20, 0, for_spell="frostbolt") == {}


# --- Analytique : cycle ---------------------------------------------------------------------------


@pytest.mark.parametrize(("stacks", "factor"), [(4, 14.5), (2, 3.75), (0, 0.0)])
def test_analytic_cycle_pays_the_growing_cost(game_data, stacks, factor):
    ch = character(game_data, 24)
    cycle = arcane_cycle(game_data, 24, B24, ch, ab_stacks=stacks)
    assert cycle["ab_casts"] == stacks
    assert cycle["ab_mana"] == pytest.approx(_base_cost(game_data, 24, B24) * factor, rel=1e-12)


def test_analytic_mana_and_rest_grow_with_the_stacks(game_data):
    runs = [kill_analytic(game_data, 24, B24, rotation="arcane", ab_stacks=n) for n in range(5)]
    mana = [r["mana"] for r in runs]
    down = [r["downtime"] for r in runs]
    assert mana == sorted(mana) and len(set(mana)) == 5
    assert down == sorted(down) and len(set(down)) == 5


def test_ignoring_the_escalation_changes_the_result(game_data, monkeypatch):
    real = kill_analytic(game_data, 24, B24, rotation="arcane")
    flat = analytic.arcane_blast_cost
    monkeypatch.setattr(analytic, "arcane_blast_cost", lambda gd, rank, pts, ch, stacks: flat(gd, rank, pts, ch, 0))
    assert kill_analytic(game_data, 24, B24, rotation="arcane")["mana"] < real["mana"]


# --- Monte Carlo ----------------------------------------------------------------------------------


def _fight_log(gd, level, pts, seed, fights=5, **options):
    ch = character(gd, level)
    rng = random.Random(seed)
    out = []
    for _ in range(fights):
        log = []
        res = kill_mc(gd, level, pts, ch, "arcane", rng, log=log, **options)
        out.append((res, log))
    return out


def test_monte_carlo_pays_each_cast_at_its_stack_cost(game_data):
    """Sans Clearcasting (pas d'Arcane Concentration), sans régénération en combat (Frost Armor au niveau 24) et sans
    Master of Elements : la mana du combat est la somme des coûts relevés lancer par lancer."""
    ch = character(game_data, 24)
    rank = best_rank(game_data, "arcane_blast", 24, B24)
    for res, log in _fight_log(game_data, 24, B24, seed=3):
        assert res["mana"] == pytest.approx(sum(c.cost for c in log), rel=1e-12)
        assert log[0].key == "arcane_blast" and log[0].stacks == 0
        for c in log:
            if c.key == "arcane_blast":
                assert c.cost == pytest.approx(arcane_blast_cost(game_data, rank, B24, ch, c.stacks), rel=1e-12)
            else:
                assert c.key == "frostbolt" and c.stacks == 4
        ab = [c.stacks for c in log if c.key == "arcane_blast"]
        assert all(b in (a + 1, 0) for a, b in pairwise(ab))


def test_clearcasting_makes_the_cast_free_and_keeps_the_stack(game_data):
    ch = character(game_data, 24)
    rank = best_rank(game_data, "arcane_blast", 24, B24_CC)
    logs = [log for _, log in _fight_log(game_data, 24, B24_CC, seed=5, fights=20)]
    ab = [c for log in logs for c in log if c.key == "arcane_blast"]
    assert any(c.cost == 0 for c in ab)
    for c in ab:
        assert c.cost == 0 or c.cost == pytest.approx(arcane_blast_cost(game_data, rank, B24_CC, ch, c.stacks))
    free_then_next = [(a, b) for log in logs for a, b in pairwise(log) if a.key == "arcane_blast" and a.cost == 0]
    assert free_then_next and all(b.stacks == a.stacks + 1 for a, b in free_then_next)  # le cumul est pris


def test_zero_stacks_is_the_dump_rotation(game_data):
    for _, log in _fight_log(game_data, 24, B24, seed=4, ab_stacks=0):
        assert {c.key for c in log} == {"frostbolt"} and all(c.stacks == 0 for c in log)


def test_monte_carlo_is_reproducible(game_data):
    a = mc(game_data, 24, B24, "Orc", "arcane", 100, seed=2)
    assert a == mc(game_data, 24, B24, "Orc", "arcane", 100, seed=2)
    assert a != mc(game_data, 24, B24, "Orc", "arcane", 100, seed=2, ab_stacks=2)


@pytest.mark.parametrize(("level", "pts"), [(24, B24), (30, B30)])
def test_analytic_close_to_monte_carlo(game_data, level, pts):
    m = mc(game_data, level, pts, "Orc", "arcane", 600)["total"]
    a = kill_analytic(game_data, level, pts, rotation="arcane")["total"]
    assert abs(a / m - 1) < 0.15, (level, round(m, 1), round(a, 1))


# --- Refus ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "pts", "options", "match"),
    [
        (19, B20, {}, "arcane_blast"),
        (24, {"improvedFrostbolt": 5}, {}, "arcane_blast"),
        (24, B24, {"rules": "seed"}, "seed"),
        (24, B24, {"ab_stacks": 5}, "ab_stacks"),
        (24, B24, {"ab_stacks": -1}, "ab_stacks"),
        (24, B24, {"ab_dump": "scorch"}, "ab_dump"),
    ],
)
def test_invalid_arcane_rotations_are_refused(game_data, level, pts, options, match):
    with pytest.raises(ValueError, match=match):
        mc(game_data, level, pts, "Orc", "arcane", 5, **options)
    with pytest.raises(ValueError, match=match):
        kill_analytic(game_data, level, pts, rotation="arcane", **options)


def test_arcane_options_need_the_arcane_rotation(game_data):
    with pytest.raises(ValueError, match="ab_stacks"):
        kill_analytic(game_data, 24, B24, rotation="frost", ab_stacks=2)
    with pytest.raises(ValueError, match="ab_dump"):
        kill_analytic(game_data, 24, B24, rotation="frost", ab_dump="fireball")


def test_cli_arcane_rotation(capsys, make_deps):
    talents = ",".join(f"{k}={v}" for k, v in B24.items())
    argv = ["sim", "leveling", "--level", "24", "--n", "10", "--rotation", "arcane", "--talents", talents]
    code, out = run_json(capsys, [*argv, "--ab-stacks", "2", "--ab-dump", "fireball"], make_deps())
    assert code == 0 and out["options"]["ab_stacks"] == 2 and out["options"]["ab_dump"] == "fireball"
    code, out = run_json(capsys, [*argv, "--ab-stacks", "7"], make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument"


def test_cli_arcane_rotation_without_the_talent_is_refused(capsys, make_deps):
    argv = ["sim", "leveling", "--level", "24", "--n", "10", "--rotation", "arcane"]
    code, out = run_json(capsys, argv, make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument"
