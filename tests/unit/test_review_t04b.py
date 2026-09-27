"""Corrections de relecture de T04b (relecteur et auditeur des mécaniques)."""

import dataclasses
import json
import random

import pytest
from conftest import MINE_GUID

from forever.cli import main
from forever.engine import character
from forever.engine.casting import melee_cast_time, pushback_rate
from forever.engine.damage import dot_tick_damage, ignite_damage, roll_base_damage
from forever.engine.mana import master_of_elements_refund
from forever.engine.monsters import mob_expected_hit, mob_hit_taken, mob_land_chance, mob_swing_damage
from forever.pipeline.monsters import fit_questie_correction
from forever.pipeline.questie import read_journey
from forever.sim.leveling_mc import kill_mc

SEED_MODE = {"mob_source": "seed", "spell_level": "rank"}


def run_json(capsys, argv, deps):
    code = main([*argv, "--json"], deps)
    return code, json.loads(capsys.readouterr().out)


def test_negative_talent_rank_is_refused(capsys, make_deps):
    argv = ["sim", "leveling", "--level", "12", "--talents", "improvedFrostbolt=5,elementalPrecision=-2"]
    code, out = run_json(capsys, argv, make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument" and "négatif" in out["error"]["message"]


def test_monster_level_is_bounded(capsys, make_deps):
    argv = ["sim", "leveling", "--level", "5", "--level-diff", "-20", "--mob-source", "seed"]
    code, out = run_json(capsys, argv, make_deps())
    assert code == 2 and "monstre" in out["error"]["message"]


def test_unknown_race_is_refused(capsys, make_deps):
    code, out = run_json(capsys, ["sim", "leveling", "--level", "12", "--race", "Elfe", "--n", "5"], make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument" and "Elfe" in out["error"]["message"]


def test_journey_reader_never_loops_on_a_bare_key(tmp_path):
    sv = tmp_path / "Questie.lua"
    sv.write_bytes(b'QuestieConfig = {\n["char"] = {\n["A - B"] = {\nfoo = {\n},\n},\n},\n}\n')
    assert read_journey(sv, MINE_GUID) == []


def test_flat_ratios_give_no_knee():
    npcs = {
        "1": {"name": "a", "rank": 0, "levels": {"10": {"max_hp": 110, "questie_hp": 100}}},
        "2": {"name": "b", "rank": 0, "levels": {"12": {"max_hp": 110, "questie_hp": 100}}},
    }
    corr = fit_questie_correction(npcs)
    assert corr is not None and corr["fit"]["slope"] == 0 and corr["fit"]["knee_level"] is None


def test_dot_ticks_do_not_crit_when_the_rule_says_so(game_data):
    """Fireball rang 1 (DoT) : sans critique des DoT, les tics valent tous le même montant, et le tirage ne change pas
    le résultat quand la règle permet le critique (parité)."""
    rules = dataclasses.replace(game_data.rules, dot_can_crit=False)
    gd = dataclasses.replace(game_data, rules=rules)
    ch = character(gd, 6)
    a = kill_mc(gd, 6, {}, ch, "fire", random.Random(2), **SEED_MODE)
    b = kill_mc(game_data, 6, {}, character(game_data, 6), "fire", random.Random(2), **SEED_MODE)
    assert a != b  # les tics critiques du DoT de Fireball disparaissent


def test_engine_helpers(game_data):
    lv, mm = game_data.leveling, game_data.mob_model
    frostbolt = game_data.spells["frostbolt"].ranks[0]
    ch = character(game_data, 10)
    assert roll_base_damage(game_data, "frostbolt", frostbolt, ch, 1.0) - roll_base_damage(
        game_data, "frostbolt", frostbolt, ch, 0.0
    ) == pytest.approx(frostbolt.damage_max - frostbolt.damage_min)
    lance = game_data.spells["ice_lance"].ranks[0]
    assert roll_base_damage(game_data, "ice_lance", lance, ch, 0.5, frozen=True) == pytest.approx(
        4.0 * roll_base_damage(game_data, "ice_lance", lance, ch, 0.5)
    )  # spells.json : frozen_mult 4
    assert mob_swing_damage(game_data, 12, 100) == pytest.approx(
        (lv.mob_hit_per_level * 12 + lv.mob_hit_per_level_squared * 144)
        * (1 - 100 / (100 + lv.armor_base + lv.armor_per_attacker_level * 12))
    )
    assert mob_land_chance(game_data) == pytest.approx(1 - mm.avoid_vs_mage)
    assert (
        mob_hit_taken(game_data, 10.0, crit=True) == 10.0 * mm.crit_mult
        and mob_hit_taken(game_data, 10.0, crit=False) == 10.0
    )
    assert mob_expected_hit(game_data, 10.0) == pytest.approx(10.0 * (1 + mm.crit * (mm.crit_mult - 1)))
    assert dot_tick_damage(game_data, 12, 1.1, 4) == pytest.approx(12 * 1.1 / 4)
    assert ignite_damage(game_data, {"ignite": 5}, 100.0) == pytest.approx(40.0)  # 40 % au rang 5 (talents.json)
    assert master_of_elements_refund(game_data, {"masterOfElements": 3}, frostbolt, 99.0) == pytest.approx(0.3 * 25)
    rate = pushback_rate(game_data, {"burningSoul": 3}, swing_s=2.5, fire_school=True)
    assert rate == pytest.approx((1 - mm.avoid_vs_mage) / 2.5 * game_data.rules.pushback_s * 0.3)
    assert melee_cast_time(game_data, 2.0, 0.1) == pytest.approx(2.0 / 0.9)
    assert melee_cast_time(game_data, 2.0, 0.99) == pytest.approx(2.0 / lv.analytic_min_cast_fraction)
