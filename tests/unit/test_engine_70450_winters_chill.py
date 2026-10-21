"""1.60.1.70450, bloc B : Winter's Chill renforce Cone of Cold (aura 271 du client, `cone_of_cold_per_winters_chill_stack`)
au lieu du critique : chaque cumul sur la cible augmente les dégâts du prochain Cone of Cold, qui les consomme ; plus
aucun critique pour Frostbolt ni Ice Lance. Avant 70450 (critique), rien ne change.

Constantes fabriquées ici ; aucun chiffre de jeu."""

from dataclasses import replace

import pytest

from forever.engine import character, expected_cast

L = 40
PER_STACK = 0.4  # gain par cumul fabriqué


def cone(gd):
    return replace(gd, constants=replace(gd.constants, crit_per_winters_chill_stack=0.0,
                                         cone_of_cold_per_winters_chill_stack=PER_STACK))  # fmt: skip


def test_stacks_raise_cone_of_cold(game_data):
    gd = cone(game_data)
    ch = character(gd, L, "Orc")
    plain = expected_cast(gd, "cone_of_cold", L, {}, ch)
    stacked = expected_cast(gd, "cone_of_cold", L, {}, ch, wc_stacks=2)
    assert stacked["dmg_mult"] == pytest.approx(plain["dmg_mult"] * (1 + 2 * PER_STACK))


def test_no_more_crit_from_the_stacks(game_data):
    gd = cone(game_data)
    ch = character(gd, L, "Orc")
    assert expected_cast(gd, "frostbolt", L, {}, ch, wc_stacks=5)["crit"] == pytest.approx(
        expected_cast(gd, "frostbolt", L, {}, ch)["crit"]
    )


def test_before_70450_cone_of_cold_unchanged(game_data_at_pre_70450_version):
    game_data = game_data_at_pre_70450_version  # aura de critique : version d'avant la refonte (conftest)
    ch = character(game_data, L, "Orc")
    assert expected_cast(game_data, "cone_of_cold", L, {}, ch, wc_stacks=2)["dmg_mult"] == pytest.approx(
        expected_cast(game_data, "cone_of_cold", L, {}, ch)["dmg_mult"]
    )


def test_derived_tables_give_the_cone_of_cold_bonus(game_data, game_data_at_pre_70450_version):
    """Tables par cumul de Winter's Chill : bonus de Cone of Cold par cumul en 70450 (constante lue dans le client),
    critique avant."""
    from forever.engine.derived import stack_tables

    new = stack_tables(game_data, "wintersChill")
    assert {t["effect"] for t in new} == {"cone_of_cold_damage", "cone_of_cold_spell_power"}  # r7 : part de puissance
    new = [t for t in new if t["effect"] == "cone_of_cold_damage"]
    per = game_data.constants.cone_of_cold_per_winters_chill_stack
    assert all(
        t["per_stack"] == pytest.approx(per) and t["at_max"] == pytest.approx(per * t["max_stacks"]) for t in new
    )
    assert {t["effect"] for t in stack_tables(game_data_at_pre_70450_version, "wintersChill")} == {"crit"}
