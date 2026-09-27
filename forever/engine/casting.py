"""Temps d'incantation."""

from __future__ import annotations

from forever.engine.model import Buffs, Character, GameData, Points, Rank
from forever.engine.talents import talent_value

# Sorts réduits par les talents (lien talent -> effet ; la réduction vient des rangs du talent).
IMPROVED_FIREBALL_SPELLS = frozenset({"fireball", "frostfire_bolt"})


def cast_time(gd: GameData, key: str, rank: Rank, pts: Points, ch: Character, buffs: Buffs | None = None) -> float:
    """Temps d'incantation effectif : réductions de talents, hâte, plancher du temps de recharge global.

    Registre : B1, B2, B16"""
    buffs = buffs or {}
    gcd = gd.rules.gcd_s
    cast = rank.cast_time_s
    if key == "frostbolt":
        cast -= talent_value(gd, pts, "improvedFrostbolt")
    if key in IMPROVED_FIREBALL_SPELLS:
        cast -= talent_value(gd, pts, "improvedFireball")
    if cast <= 0 or gd.spells[key].channel:
        return max(gcd, cast)
    cast /= 1 + ch.haste + buffs.get("haste", 0.0)
    return max(gcd, cast)


def pushback_s(gd: GameData) -> float:
    """Registre : B6"""
    raise NotImplementedError


def pushback_chance(gd: GameData, pts: Points, *, fire_school: bool) -> float:
    """Registre : B6"""
    raise NotImplementedError


def spell_cooldown(gd: GameData, key: str, rank: Rank, pts: Points) -> float:
    """Registre : B13"""
    raise NotImplementedError
