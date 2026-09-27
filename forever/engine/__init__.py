"""Moteur de mécaniques : fonctions pures qui reçoivent les données de la version (`GameData`) en paramètre.

`MECHANICS` est l'inventaire des mécaniques couvertes par les contrôles de `tests/unit/test_engine_mechanics.py` :
libellé du contrôle -> identifiant du registre (`docs/MECHANICS_REGISTRY.yaml`)."""

from __future__ import annotations

from forever.engine.cast import expected_cast
from forever.engine.casting import cast_time
from forever.engine.character import character, int_per_crit
from forever.engine.crit import crit_chance, crit_mult
from forever.engine.damage import dmg_mult, spell_power
from forever.engine.hit import hit_chance
from forever.engine.mana import mana_cost
from forever.engine.model import (
    SCHOOL_FIRE,
    SCHOOL_FROST,
    Buffs,
    CastEstimate,
    Character,
    CharacterOverrides,
    GameData,
    Points,
    Rank,
)
from forever.engine.spells import best_rank, coefficient
from forever.engine.talents import check_build, legal_additions, points_available, talent_value, tree_split

MECHANICS: dict[str, str] = {}

__all__ = [
    "MECHANICS",
    "SCHOOL_FIRE",
    "SCHOOL_FROST",
    "Buffs",
    "CastEstimate",
    "Character",
    "CharacterOverrides",
    "GameData",
    "Points",
    "Rank",
    "best_rank",
    "cast_time",
    "character",
    "check_build",
    "coefficient",
    "crit_chance",
    "crit_mult",
    "dmg_mult",
    "expected_cast",
    "hit_chance",
    "int_per_crit",
    "legal_additions",
    "mana_cost",
    "points_available",
    "spell_power",
    "talent_value",
    "tree_split",
]
