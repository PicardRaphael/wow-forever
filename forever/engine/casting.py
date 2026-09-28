"""Temps d'incantation."""

from __future__ import annotations

from forever.engine.model import Buffs, Character, GameData, Points, Rank
from forever.engine.talents import talent_value

# Sorts réduits par les talents (lien talent -> effet ; la réduction vient des rangs du talent).
IMPROVED_FIREBALL_SPELLS = frozenset({"fireball", "frostfire_bolt"})
PERCENT = 100.0  # conversion d'unité : les talents sont exprimés en %


def cast_time(gd: GameData, key: str, rank: Rank, pts: Points, ch: Character, buffs: Buffs | None = None) -> float:
    """Temps d'incantation effectif : réductions de talents, part retirée par un buff (`cast_reduction` : Hot Streak
    sur Pyroblast, Missile Barrage sur la canalisation d'Arcane Missiles), hâte, plancher du temps de recharge global.

    Registre : B1, B2, B14, B15, B16"""
    buffs = buffs or {}
    gcd = gd.rules.gcd_s
    cast = rank.cast_time_s
    if key == "frostbolt":
        cast -= talent_value(gd, pts, "improvedFrostbolt")
    if key in IMPROVED_FIREBALL_SPELLS:
        cast -= talent_value(gd, pts, "improvedFireball")
    cast *= 1 - buffs.get("cast_reduction", 0.0)
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


def pushback_rate(gd: GameData, pts: Points, *, swing_s: float, fire_school: bool) -> float:
    """Recul moyen par seconde d'incantation en mêlée (modèle analytique) : coups qui touchent par seconde × recul
    par coup × chance de recul (Burning Soul).

    Registre : B6"""
    land = 1 - gd.mob_model.avoid_vs_mage
    return land / swing_s * pushback_s(gd) * (1 - pushback_resist_chance(gd, pts, fire_school=fire_school))


def melee_cast_time(gd: GameData, cast_s: float, push_per_s: float) -> float:
    """Incantation en mêlée allongée par le recul (modèle analytique), au plus `1 / leveling.analytic.min_cast_fraction`
    fois l'incantation.

    Registre : B6"""
    return cast_s / max(gd.leveling.analytic_min_cast_fraction, 1 - push_per_s)
