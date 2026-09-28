"""Moteur de mécaniques : fonctions pures qui reçoivent les données de la version (`GameData`) en paramètre.

`MECHANICS` est l'inventaire des mécaniques couvertes par les contrôles de `tests/unit/test_engine_mechanics.py` :
libellé du contrôle -> identifiant du registre (`docs/MECHANICS_REGISTRY.yaml`)."""

from __future__ import annotations

from forever.engine.buffs import arcane_power_buffs, fire_vulnerability_buffs, merge_buffs
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
from forever.engine.spells import (
    RankValues,
    best_rank,
    coefficient,
    dot_coefficient,
    dot_ticks,
    low_level_factor,
    rank_values_at_level,
)
from forever.engine.talents import check_build, legal_additions, points_available, talent_value, tree_split

MECHANICS: dict[str, str] = {
    "toucher/écart de niveau": "A3",
    "plafond de toucher": "A3",
    "Elemental Precision": "A4",
    "Arcane Focus": "A4",
    "critique Int/niveau": "A5",
    "critique d'équipement": "A5",
    "critique épée Humain": "G1",
    "Arcane Instability": "A5",
    "Critical Mass": "A5",
    "Arcane Impact": "A5",
    "Incineration": "A5",
    "Shatter (gelé)": "A5",
    "Winter's Chill": "D4",
    "multiplicateur de critique": "A21",
    "Ice Shards": "A21",
    "Arcane Mind": "A21",
    "DoT qui critiquent": "A17",
    "Ignite": "A18",
    "Piercing Ice": "A20",
    "Fire Power": "A20",
    "coefficients": "G4",
    "pénalité < 20": "G4",
    "Improved Frostbolt": "B16",
    "Improved Fireball": "B16",
    "hâte": "B2",
    "temps de recharge global": "B1",
    "Frost Channeling": "B17",
    "Master of Elements": "B17",
    "Arcane Concentration": "B12",
    "sorts en % du mana de base": "B11",
}

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
    "RankValues",
    "arcane_power_buffs",
    "best_rank",
    "cast_time",
    "character",
    "check_build",
    "coefficient",
    "crit_chance",
    "crit_mult",
    "dmg_mult",
    "dot_coefficient",
    "dot_ticks",
    "expected_cast",
    "fire_vulnerability_buffs",
    "hit_chance",
    "int_per_crit",
    "legal_additions",
    "low_level_factor",
    "mana_cost",
    "merge_buffs",
    "points_available",
    "rank_values_at_level",
    "spell_power",
    "talent_value",
    "tree_split",
]
