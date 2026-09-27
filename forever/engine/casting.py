"""Temps d'incantation."""

from __future__ import annotations

from forever.engine.model import Buffs, Character, GameData, Points, Rank
from forever.engine.talents import talent_value

# Sorts réduits par les talents (lien talent -> effet ; la réduction vient des rangs du talent).
IMPROVED_FIREBALL_SPELLS = frozenset({"fireball", "frostfire_bolt"})
PERCENT = 100.0  # conversion d'unité : les talents sont exprimés en %


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
    """Recul d'une incantation par coup reçu (`leveling.json.combat_rules.pushback_s`).

    Registre : B6"""
    return gd.rules.pushback_s


def pushback_resist_chance(gd: GameData, pts: Points, *, fire_school: bool) -> float:
    """Chance qu'un coup reçu ne fasse pas reculer l'incantation : Burning Soul, sorts de feu seulement.

    Registre : B6"""
    return talent_value(gd, pts, "burningSoul", 0) / PERCENT if fire_school else 0.0


def pushback_chance(gd: GameData, pts: Points, *, fire_school: bool) -> float:
    """Chance qu'un coup reçu fasse reculer l'incantation.

    Registre : B6"""
    return 1.0 - pushback_resist_chance(gd, pts, fire_school=fire_school)


def spell_cooldown(gd: GameData, key: str, rank: Rank, pts: Points) -> float:
    """Recharge d'un sort : celle du rang, moins Improved Frost Nova (Frost Nova) ou Wake of Fire (Fire Blast).

    Registre : B13"""
    if key == "frost_nova":
        return rank.cooldown_s - talent_value(gd, pts, "improvedFrostNova")
    if key == "fire_blast":
        return rank.cooldown_s - talent_value(gd, pts, "wakeOfFire", 0)
    return rank.cooldown_s
