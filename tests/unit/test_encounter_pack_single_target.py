"""Rotation à une cible sur un paquet (T05, bloc F, correction d'un défaut de l'analytique du bloc E) : une cible après
l'autre, sans multiplier les dégâts par le nombre de cibles ; l'analytique suit le Monte Carlo."""

import pytest

from forever.sim.encounter import encounter_analytic, encounter_mc

FROST = {"improvedFrostbolt": 5, "iceShards": 5}
NO_OOM = {"mana": 1e6}  # réserve de test sans limite


def test_single_target_rotation_kills_the_pack_one_target_at_a_time(game_data):
    pack = encounter_analytic(game_data, "dungeon_pack", 40, FROST, "Orc", "frost", NO_OOM)
    m = encounter_mc(game_data, "dungeon_pack", 40, FROST, "Orc", "frost", 200, seed=1, over=NO_OOM)
    assert pack["dps"] == pytest.approx(m.mean, rel=0.05), (pack["dps"], m.mean)
    aoe = encounter_analytic(game_data, "dungeon_pack", 40, FROST, "Orc", "aoe", NO_OOM)
    assert aoe["dps"] > pack["dps"]


def test_pack_after_running_out_of_mana_counts_the_whole_duration(game_data):
    """Défaut corrigé au bloc I2 : après une fin de mana, l'analytique divisait les dégâts du paquet par l'instant de
    la fin de mana au lieu de la durée du scénario (comme le Monte Carlo) ; réserve de test réduite."""
    low = {"mana": 800.0}  # réserve de test : fin de mana avant la mort du paquet
    a = encounter_analytic(game_data, "dungeon_pack", 40, {}, "Orc", "aoe", low, aoe_filler="arcane_explosion")
    m = encounter_mc(
        game_data, "dungeon_pack", 40, {}, "Orc", "aoe", 200, seed=1, over=low, aoe_filler="arcane_explosion"
    )
    assert a["oom_s"] is not None and a["duration_s"] == game_data.build.scenarios["dungeon_pack"].duration_s
    assert a["dps"] == pytest.approx(a["dmg"] / a["duration_s"], rel=1e-12)
    assert a["dps"] == pytest.approx(m.mean, rel=0.15), (a["dps"], m.mean)
