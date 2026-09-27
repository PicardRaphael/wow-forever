"""Moteur du leveling (bloc C du plan T04b) : coups et XP des monstres, armure, repos, régénération en combat, recul
d'incantation, recharges, temps de vol, ralentis et gel, dégâts au niveau du personnage.

Les formules sont portées de seed/forever-mage/scripts/sim_leveling.py (lecture seule, importé par importlib) : chaque
fonction est comparée à celle du seed, sur ses propres données ; les chiffres du seed vivent dans
`forever/data/1.60.1.70009/mechanics.json` (clés `leveling.*`)."""

import importlib.util
import math
import sys

import pytest
from conftest import LOCAL_VERSION, REPO_ROOT

from forever.engine import best_rank, character, expected_cast, rank_values_at_level
from forever.engine.casting import pushback_chance, pushback_s, spell_cooldown
from forever.engine.damage import dot_tick_times, ignite_tick_times
from forever.engine.mana import consumables, downtime, in_combat_regen_fraction
from forever.engine.monsters import armor_reduction, mob_hit_damage, mob_hp, mob_xp
from forever.engine.movement import (
    attacker_swing_s,
    chill_duration,
    frostbite_chance,
    frostbite_freeze_s,
    frostbolt_slow,
    mob_speed,
    spell_range,
    travel_time,
)
from forever.engine.spells import RankValues, rank_damage

SEED_SCRIPTS = REPO_ROOT / "seed" / "forever-mage" / "scripts"
TALENTS = [{}, {"arcaneMeditation": 3}, {"arcaneMeditation": 1, "burningSoul": 2}]


@pytest.fixture(scope="module")
def seed_sim():
    """Module sim_leveling du seed ; son `import fm` résout le fm du seed (dossier ajouté le temps du chargement)."""
    sys.path.insert(0, str(SEED_SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("seed_sim_leveling", SEED_SCRIPTS / "sim_leveling.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SEED_SCRIPTS))
    module.fm.data(LOCAL_VERSION)
    return module


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def test_leveling_constants_come_from_mechanics_json(game_data):
    lv = game_data.leveling
    assert (lv.mob_hit_per_level, lv.mob_hit_per_level_squared) == (0.8, 0.02)
    assert (lv.armor_base, lv.armor_per_attacker_level) == (400, 85)
    assert (lv.xp_base, lv.xp_per_level) == (45, 5)
    assert (lv.frostbite_freeze_s, lv.dot_tick_s, lv.ignite_ticks, lv.ignite_tick_s) == (5.0, 2.0, 2, 2.0)
    assert (lv.frost_nova_retreat_yd, lv.rest_hp_regen_fraction) == (10.0, 0.02)
    assert (lv.projectile_speed_default, lv.projectile_speed_instant) == (28, 1e9)
    assert (lv.analytic_min_cast_fraction, lv.analytic_freeze_cap, lv.analytic_winters_chill_casts) == (0.2, 0.95, 3)
    assert (lv.default_level_diff, lv.default_nova_break, lv.default_run_between_s) == (0, 1.0, 6.0)
    assert game_data.rules.pushback_s == 0.5  # leveling.json combat_rules


def test_monster_formulas_match_the_seed(game_data, seed_sim):
    for level in range(1, 61):
        assert close(mob_hit_damage(game_data, level), seed_sim.mob_hit_raw(level)), level
        assert close(mob_xp(game_data, level), seed_sim.mob_xp(level)), level
        assert close(mob_hp(game_data, level, "seed").value, seed_sim.mob_hp(level)), level
        for armor in (0, 137.5, 600):
            assert close(armor_reduction(game_data, armor, level), seed_sim.armor_dr(armor, level)), (armor, level)


def test_rest_and_regen_match_the_seed(game_data, seed_sim):
    for level in range(1, 61):
        assert all(map(close, consumables(game_data, level), seed_sim.consumables(level))), level
        for pts in TALENTS:
            got = in_combat_regen_fraction(game_data, pts, level, rules="seed")
            assert close(got, seed_sim.in_combat_regen_frac(pts, level)), (pts, level)


def test_mage_armor_regen_from_its_first_rank(game_data):
    assert in_combat_regen_fraction(game_data, {}, 33) == 0.0
    assert (
        in_combat_regen_fraction(game_data, {}, 34) == 0.5
    )  # Mage Armor du client : rang 1 au niveau 34, aura 134 à 50 %


def test_forever_regen_adds_arcane_meditation_and_worn_mage_armor(game_data):
    """T04c, B7 (règle Classic, suppose) : Arcane Meditation (talents.json 17 / 33 / 50 %) + Mage Armor portée
    (aura 134 à 50 %, client), bornée à 1 ; sous le niveau d'apprentissage de Mage Armor (34), le talent seul."""
    assert in_combat_regen_fraction(game_data, {}, 40) == 0.5
    assert in_combat_regen_fraction(game_data, {"arcaneMeditation": 1}, 40) == pytest.approx(0.67, rel=1e-12)
    assert in_combat_regen_fraction(game_data, {"arcaneMeditation": 3}, 40) == 1.0
    assert in_combat_regen_fraction(game_data, {"arcaneMeditation": 3}, 33) == 0.5
    frost = in_combat_regen_fraction(game_data, {"arcaneMeditation": 1}, 40, armor="frost")
    assert frost == pytest.approx(0.17, rel=1e-12)  # Ice Armor portée : pas de régénération en incantation
    seed = in_combat_regen_fraction(game_data, {"arcaneMeditation": 1}, 40, rules="seed")
    assert seed == 0.5  # seed : maximum des deux


def test_downtime_is_the_longer_of_drinking_and_eating(game_data):
    ch = character(game_data, 12)
    water, food = consumables(game_data, 12)
    mana_rest = 300 / (water + ch.spirit_regen)
    hp_rest = 150 / (food + 0.02 * ch.hp)  # leveling.rest_hp_regen_fraction
    assert close(downtime(game_data, ch, 12, 300, 150), max(mana_rest, hp_rest))
    assert downtime(game_data, ch, 12, 0, 0) == 0


def test_travel_time(game_data):
    assert close(travel_time(game_data, "frostbolt", 30), 30 / 28)  # projectile_speed de spells.json
    assert close(travel_time(game_data, "fire_blast", 20), 20 / 1e9)  # sans vitesse : instantané (seed)
    assert close(travel_time(game_data, "fire_blast", 20, analytic=True), 20 / 28)  # défaut de l'analytique
    assert travel_time(game_data, "frost_nova", 0) == 0


def test_slow_freeze_and_range(game_data):
    frostbolt = game_data.spells["frostbolt"]
    assert close(frostbolt_slow(game_data, {}), 0.4)
    assert close(frostbolt_slow(game_data, {"permafrost": 3}), 0.5)  # +10 % de ralenti
    assert close(chill_duration(game_data, frostbolt.ranks[1], {"permafrost": 3}), 6 * 1.33)
    assert close(mob_speed(game_data, 0.4), 7.0 * 0.6)  # mob_model.run_speed
    assert close(frostbite_chance(game_data, {"frostbite": 3}), 0.15) and frostbite_freeze_s(game_data) == 5.0
    assert close(spell_range(game_data, "frostbolt", {"arcticReach": 2}), 36)
    assert spell_range(game_data, "fireball", {"arcticReach": 2}) == 35  # Arctic Reach : Frostbolt seulement (seed)
    assert close(attacker_swing_s(game_data, frost_armor=True), 2.0 * 1.25)
    assert attacker_swing_s(game_data, frost_armor=False) == 2.0


def test_pushback(game_data):
    assert pushback_s(game_data) == 0.5
    assert pushback_chance(game_data, {}, fire_school=True) == 1.0
    assert close(pushback_chance(game_data, {"burningSoul": 3}, fire_school=True), 0.3)
    assert pushback_chance(game_data, {"burningSoul": 3}, fire_school=False) == 1.0


def test_spell_cooldowns(game_data):
    nova = game_data.spells["frost_nova"].ranks[0]
    blast = game_data.spells["fire_blast"].ranks[0]
    assert spell_cooldown(game_data, "frost_nova", nova, {"improvedFrostNova": 2}) == 25 - 4
    assert spell_cooldown(game_data, "fire_blast", blast, {"wakeOfFire": 2}) == 8 - 2
    assert spell_cooldown(game_data, "frostbolt", game_data.spells["frostbolt"].ranks[0], {}) == 0


def test_dot_and_ignite_ticks(game_data):
    assert dot_tick_times(game_data, 8) == [2.0, 4.0, 6.0, 8.0]
    assert dot_tick_times(game_data, 1) == [2.0]  # au moins un tic (seed)
    assert ignite_tick_times(game_data) == [2.0, 4.0]


def test_rank_damage_at_the_character_level(game_data):
    rank2 = game_data.spells["frostbolt"].ranks[1]
    assert rank_damage(game_data, "frostbolt", rank2, 12, "rank") == RankValues(34, 38, 0)
    assert rank_damage(game_data, "frostbolt", rank2, 12, "character") == rank_values_at_level(
        game_data, "frostbolt", 2, 12
    )
    with pytest.raises(ValueError, match="spell_level"):
        rank_damage(game_data, "frostbolt", rank2, 12, "table")  # type: ignore[arg-type]


def test_expected_cast_at_the_character_level(game_data):
    """Frostbolt rang 2 (appris au niveau 8, plafond MaxLevel 12) au niveau 10 : dégâts du rang au niveau 10."""
    ch = character(game_data, 10)
    rank = expected_cast(game_data, "frostbolt", 10, {}, ch)
    level = expected_cast(game_data, "frostbolt", 10, {}, ch, spell_level="character")
    assert rank is not None and level is not None and rank["rank"].position == level["rank"].position == 2
    low, high, _ = rank_values_at_level(game_data, "frostbolt", 2, 10)
    assert (low, high) != (34, 38)
    per_point = rank["dmg_mult"] * (1 + rank["crit"] * (rank["crit_mult"] - 1))
    assert close(level["direct_per_hit"] - rank["direct_per_hit"], ((low + high) / 2 - (34 + 38) / 2) * per_point)
    top = game_data.scaling["frostbolt"][1].max_level
    assert top == 12 and best_rank(game_data, "frostbolt", top, {}).position == 2
    ch_top = character(game_data, top)
    assert expected_cast(game_data, "frostbolt", top, {}, ch_top, spell_level="character") == expected_cast(
        game_data, "frostbolt", top, {}, ch_top
    )
