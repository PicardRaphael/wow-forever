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
