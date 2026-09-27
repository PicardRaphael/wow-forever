"""Multiplicateurs de dégâts et puissance des sorts."""

from __future__ import annotations

from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Buffs, Character, GameData, Points
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents de dégâts sont exprimés en %


def dmg_mult(gd: GameData, school: str, pts: Points, buffs: Buffs | None = None) -> float:
    """Multiplicateur de dégâts : talents globaux et d'école, puis buffs.

    Registre : A20"""
    buffs = buffs or {}
    m = 1 + talent_value(gd, pts, "arcaneInstability") / PERCENT
    if school in SCHOOL_FROST:
        m *= 1 + talent_value(gd, pts, "piercingIce") / PERCENT
    if school in SCHOOL_FIRE:
        m *= 1 + talent_value(gd, pts, "firePower") / PERCENT
    m *= 1 + buffs.get("dmg", 0.0)
    return m


def spell_power(ch: Character, buffs: Buffs | None = None) -> float:
    """Puissance des sorts du personnage, buffs en pourcentage puis fixes.

    Registre : G4"""
    buffs = buffs or {}
    return ch.sp * (1 + buffs.get("sp_pct", 0.0)) + buffs.get("sp_flat", 0.0)
