"""Givre après le correctif du serveur 112753 (70450 r6, décision 290 ; question HF2) :

- Winter's Chill : chaque cumul ajoute aussi au prochain Cone of Cold une part de la puissance des sorts (3e effet du
  talent, `$s3`), lue dans le client (`auras.winters_chill.sp_pct_per_stack`) ; posé par Frostbolt, Frost Blast et
  Ice Lance renforcé par Fingers of Frost seulement (texte du correctif) ;
- Ice Barrier : Frigid Power (+x % de dégâts de Givre pendant la durée du sort), compté dès que le talent est pris
  (lancé avant le combat, relancé à l'expiration : une incantation globale dans les longs combats) ; +y % de plus tant
  que le bouclier tient : compté seulement là où le Mage ne prend aucun coup (scénarios de donjon et de raid, tank
  présent) ; ailleurs (leveling, PvP), angle mort chiffré.

Constantes de Winter's Chill fabriquées ici ; celles d'Ice Barrier lues dans `talents.json` (variables du rang)."""

import math
from dataclasses import replace

import pytest

from forever.engine import character, expected_cast
from forever.engine.damage import dmg_mult, roll_base_damage
from forever.engine.spells import best_rank
from forever.engine.talents import talent_value

L = 60
PER_SP = 0.3  # part de la puissance des sorts par cumul, fabriquée
IB = {"iceBarrier": 1}
FRIGID, FRIGID_MIN, SHIELDED = 1, 2, 3  # positions des variables du rang d'Ice Barrier (talents.json)
ENDLESS = {"mana": 10.0**9}  # réserve fabriquée : le combat dure tout le scénario, sans fin de mana


def cone(gd):
    return replace(gd, constants=replace(gd.constants, crit_per_winters_chill_stack=0.0,
                                         cone_of_cold_per_winters_chill_stack=0.05,
                                         cone_of_cold_sp_per_winters_chill_stack=PER_SP))  # fmt: skip


# --- Winter's Chill : part de la puissance des sorts ---------------------------------------------------------------


def test_decode_reads_the_spell_power_part_from_the_talent_effect():
    from forever.pipeline.decode import source_effect_points

    effects = {0: {"EffectBasePointsF": 5}, 2: {"EffectBasePointsF": 7}}
    assert source_effect_points({"sp_effect": 2}, effects, "EffectBasePointsF") == 7
    assert source_effect_points({}, effects, "EffectBasePointsF") is None  # règle d'avant : rien à lire
    with pytest.raises(Exception, match="effet 4"):
        source_effect_points({"sp_effect": 4}, effects, "EffectBasePointsF")  # effet absent : refus, jamais deviné


def test_client_mechanics_reads_the_spell_power_part(game_data):
    from forever.gamedata import _client_mechanics

    raw = {"auras": {"winters_chill": {"pct_per_stack": 5, "sp_pct_per_stack": 30, "max_stacks": 5,
                                       "duration_ms": 15000, "kind": "cone_of_cold"}}}  # fmt: skip
    c, _ = _client_mechanics(raw, game_data.constants, game_data.leveling)
    assert c.cone_of_cold_sp_per_winters_chill_stack == pytest.approx(0.3)
    del raw["auras"]["winters_chill"]["sp_pct_per_stack"]
    c, _ = _client_mechanics(raw, game_data.constants, game_data.leveling)
    assert c.cone_of_cold_sp_per_winters_chill_stack == 0.0


def test_stacks_add_spell_power_to_cone_of_cold(game_data):
    gd = cone(game_data)
    ch = character(gd, L, "Orc", {"sp": 400})
    plain = expected_cast(gd, "cone_of_cold", L, {}, ch, wc_stacks=0)
    stacked = expected_cast(gd, "cone_of_cold", L, {}, ch, wc_stacks=2)
    per_hit = stacked["direct_per_hit"] / stacked["dmg_mult"] - plain["direct_per_hit"] / plain["dmg_mult"]
    crit_factor = 1 + plain["crit"] * (plain["crit_mult"] - 1)
    assert per_hit == pytest.approx(2 * PER_SP * ch.sp * crit_factor)
    frostbolt = expected_cast(gd, "frostbolt", L, {}, ch, wc_stacks=2)
    assert frostbolt["dmg"] == pytest.approx(expected_cast(gd, "frostbolt", L, {}, ch)["dmg"])  # Cone of Cold seul


def test_monte_carlo_roll_adds_the_same_part(game_data):
    gd = cone(game_data)
    ch = character(gd, L, "Orc", {"sp": 400})
    rank = best_rank(gd, "cone_of_cold", L, {})
    plain = roll_base_damage(gd, "cone_of_cold", rank, ch, 0.5)
    assert roll_base_damage(gd, "cone_of_cold", rank, ch, 0.5, wc_stacks=3) == pytest.approx(plain + 3 * PER_SP * ch.sp)


def test_only_the_patched_spells_apply_winters_chill(game_data):
    from forever.engine.crit import applies_winters_chill

    gd = cone(game_data)
    assert applies_winters_chill(gd, "frostbolt") and applies_winters_chill(gd, "frost_blast")
    assert applies_winters_chill(gd, "ice_lance", empowered=True)
    assert not applies_winters_chill(gd, "ice_lance") and not applies_winters_chill(gd, "blizzard")
    assert not applies_winters_chill(gd, "frost_nova")


def test_derived_tables_give_the_spell_power_part(game_data):
    from forever.engine.derived import stack_tables

    tables = {t["effect"]: t for t in stack_tables(cone(game_data), "wintersChill")}
    assert tables["cone_of_cold_spell_power"]["per_stack"] == pytest.approx(PER_SP)
    assert "cone_of_cold_damage" in tables


# --- Ice Barrier : Frigid Power ------------------------------------------------------------------------------------


def frigid(gd):
    return talent_value(gd, IB, "iceBarrier", FRIGID) / 100, talent_value(gd, IB, "iceBarrier", SHIELDED) / 100


def test_frigid_power_raises_frost_damage_when_the_talent_is_taken(game_data):
    base, shielded = frigid(game_data)
    assert base > 0 and shielded > 0  # variables du rang lues dans talents.json (70450 r6)
    assert dmg_mult(game_data, "frost", IB) == pytest.approx(dmg_mult(game_data, "frost", {}) * (1 + base))
    assert dmg_mult(game_data, "fire", IB) == pytest.approx(dmg_mult(game_data, "fire", {}))
    with_shield = dmg_mult(game_data, "frost", IB, {"ice_barrier_shield": 1.0})
    assert with_shield == pytest.approx(dmg_mult(game_data, "frost", {}) * (1 + base) * (1 + shielded))
    assert dmg_mult(game_data, "frost", {}, {"ice_barrier_shield": 1.0}) == pytest.approx(
        dmg_mult(game_data, "frost", {})
    )  # sans le talent, pas de bouclier


def test_shield_counts_only_where_the_mage_is_not_hit(game_data):
    from forever.engine.buffs import ice_barrier_shield_buffs

    assert ice_barrier_shield_buffs(game_data, IB) == {"ice_barrier_shield": 1.0}
    assert ice_barrier_shield_buffs(game_data, {}) == {}


def test_raid_fight_recasts_ice_barrier_when_frigid_power_ends(game_data):
    from forever.sim.encounter import encounter_fight

    sc = game_data.build.scenarios["raid_boss"]
    log: list = []
    encounter_fight(game_data, "raid_boss", L, IB, rng=__import__("random").Random(1), log=log, over=ENDLESS)
    frigid_s = talent_value(game_data, IB, "iceBarrier", FRIGID_MIN) * 60
    recasts = [c for c in log if c.key == "ice_barrier"]
    assert len(recasts) == math.ceil(sc.duration_s / frigid_s) - 1
    assert all(c.end - c.start == pytest.approx(game_data.rules.gcd_s) for c in recasts)
    log.clear()
    encounter_fight(game_data, "raid_boss", L, {}, rng=__import__("random").Random(1), log=log, over=ENDLESS)
    assert not [c for c in log if c.key == "ice_barrier"]


def test_shield_is_a_blind_spot_in_leveling_and_pvp(game_data):
    from forever.engine.blind_spots import estimate_frigid_shield

    _, shielded = frigid(game_data)
    assert estimate_frigid_shield(game_data, L, IB, "Orc") == pytest.approx(shielded)
    assert estimate_frigid_shield(game_data, L, {}, "Orc") is None


def test_installed_spell_power_part_matches_the_client_tooltip(game_data):
    """Recoupement (70450 r7) : la part décodée de l'effet du talent égale la valeur `$s3` de son infobulle."""
    import json

    from conftest import DATA_DIR, VALUES_VERSION

    talents = json.loads((DATA_DIR / VALUES_VERSION / "talents.json").read_text(encoding="utf-8"))
    wc = next(t for tree in talents["trees"] for t in tree["talents"] if t["key"] == "wintersChill")
    assert "$s3% of your spell damage" in wc["source"]["client_desc"]
    sp_tooltip = wc["tooltip_values"][-1][2]  # variables : chance, part de Cone of Cold, $s3, cumuls
    assert game_data.constants.cone_of_cold_sp_per_winters_chill_stack == pytest.approx(sp_tooltip / 100)
