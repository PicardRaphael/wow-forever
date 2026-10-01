"""Modèle de personnage (registres A5, B9, G1, G2).

Valeurs attendues calculées avec seed/forever-mage/scripts/fm.py le 2026-09-27 (`character`, `int_per_crit`) ;
raciaux : seed/forever-mage/data/1.60.1.70009/racials.json (Humain : esprit +5 %, épée +2 % ; Gnome : mana +5 %)."""

import pytest

from forever.engine import character, int_per_crit


def approx(x):
    return pytest.approx(x, rel=1e-12, abs=1e-15)


def test_character_orc_60(seed_game_data):
    c = character(seed_game_data, 60, "Orc")
    assert (c.level, c.race) == (60, "Orc")
    assert c.intellect == approx(168.84)
    assert c.spirit == approx(147.44)
    assert c.sp == approx(24.0)
    assert c.base_mana == approx(1215.1)
    assert c.mana == approx(3467.7)
    assert c.crit == approx(0.030376470588235296)
    assert c.hp == approx(1660.0)
    assert c.armor == approx(340.0)
    assert c.spirit_regen == approx(24.93)
    assert (c.hit_gear, c.haste) == (0.0, 0.0)
    assert c.overrides == {}


def test_character_gnome_mana(seed_game_data):
    assert character(seed_game_data, 12, "Gnome").mana == approx(753.165)


def test_spell_power_starts_at_level_10(game_data):
    assert character(game_data, 9).sp == 0.0
    assert character(game_data, 10).sp == approx(4.0)


def test_int_per_crit(seed_game_data):
    assert int_per_crit(seed_game_data, 1) == 6.0
    assert int_per_crit(seed_game_data, 30) == approx(32.29661016949153)
    assert int_per_crit(seed_game_data, 60) == 59.5
    assert int_per_crit(seed_game_data, 0) == 6.0
    assert int_per_crit(seed_game_data, 70) == 59.5


def test_spell_crit_override(game_data):
    assert character(game_data, 60, "Orc", {"spell_crit": 0.10}).crit == 0.10


def test_overrides_replace_estimates(seed_game_data):
    c = character(seed_game_data, 60, "Orc", {"intellect": 200, "sp": 500, "hit_gear": 0.02, "haste": 0.1})
    assert c.intellect == 200
    assert c.sp == 500
    assert (c.hit_gear, c.haste) == (0.02, 0.1)
    assert c.mana == approx(1215.1 + 20 + 15 * 180)  # mana de base calculée + Int surchargée
    assert c.overrides == {"intellect": 200, "sp": 500, "hit_gear": 0.02, "haste": 0.1}


def test_human_spirit_bonus(game_data):
    assert character(game_data, 60, "Human").spirit == approx(character(game_data, 60, "Orc").spirit * 1.05)


def test_human_sword_crit(game_data):
    human = character(game_data, 60, "Human").crit
    assert character(game_data, 60, "Human", {"sword": True}).crit == approx(human + 0.02)
    # l'épée ne sert qu'au racial humain
    assert character(game_data, 60, "Orc", {"sword": True}).crit == character(game_data, 60, "Orc").crit
