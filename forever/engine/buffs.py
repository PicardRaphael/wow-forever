"""Auras temporaires du Mage : Arcane Blast (cumuls, expiration, consommation, bonus de dégâts des autres sorts).

Chiffres du talent `arcaneBlast` (`talents.json`, variables d'infobulle) : dégâts min et max, bonus de dégâts des
autres sorts par cumul (%), hausse du coût d'Arcane Blast par cumul (%), cumuls maximum, durée (s)."""

from __future__ import annotations

from typing import NamedTuple

from forever.engine.model import Buffs, GameData, Points
from forever.engine.talents import talent_value

TALENT = "arcaneBlast"
SPELL = "arcane_blast"
PERCENT = 100.0  # conversion d'unité : les variables du talent sont exprimées en %
# Positions des variables du talent dans talents.json (lien talent -> effet, pas des chiffres de jeu).
DMG_PER_STACK, COST_PER_STACK, MAX_STACKS, DURATION = 2, 3, 4, 5


class ArcaneBlastAura(NamedTuple):
    stacks: int
    expires: float


def arcane_blast_max_stacks(gd: GameData, pts: Points) -> int:
    """Cumuls maximum de l'aura d'Arcane Blast (0 sans le talent).

    Registre : B15"""
    return int(talent_value(gd, pts, TALENT, MAX_STACKS))


def arcane_blast_active(aura: ArcaneBlastAura | None, now: float) -> int:
    """Cumuls actifs à `now` (0 si l'aura est absente ou expirée).

    Registre : B15"""
    return aura.stacks if aura is not None and now < aura.expires else 0


def arcane_blast_after_cast(gd: GameData, pts: Points, aura: ArcaneBlastAura | None, now: float) -> ArcaneBlastAura:
    """Aura après un Arcane Blast lancé à `now` : un cumul de plus (borné au maximum du talent), durée relancée.
    Consommation : tout autre sort de dégâts retire l'aura (l'appelant la remet à None).

    Registre : B15"""
    stacks = min(arcane_blast_max_stacks(gd, pts), arcane_blast_active(aura, now) + 1)
    return ArcaneBlastAura(stacks, now + talent_value(gd, pts, TALENT, DURATION))


def arcane_blast_bonus(gd: GameData, pts: Points, stacks: int, *, for_spell: str) -> Buffs:
    """Bonus de dégâts de l'aura pour `for_spell` (buff `dmg`, fraction) : +x % par cumul sur les autres sorts,
    aucun sur Arcane Blast lui-même (son aura augmente son coût, pas ses dégâts).

    Registre : B15"""
    if for_spell == SPELL or stacks <= 0:
        return {}
    return {"dmg": stacks * talent_value(gd, pts, TALENT, DMG_PER_STACK) / PERCENT}


def arcane_blast_after_spell(
    gd: GameData, pts: Points, aura: ArcaneBlastAura | None, now: float, key: str
) -> ArcaneBlastAura | None:
    """Aura après un sort de dégâts `key` lancé à `now` : Arcane Blast cumule, tout autre sort de dégâts la consomme.

    Registre : B15"""
    return arcane_blast_after_cast(gd, pts, aura, now) if key == SPELL else None


def arcane_power_buffs(gd: GameData, pts: Points) -> Buffs:
    """Buffs de l'aura d'Arcane Power.

    Registre : A20, B15"""
    raise NotImplementedError


def fire_vulnerability_buffs(gd: GameData, stacks: int) -> Buffs:
    """Cumuls de Fire Vulnerability sur la cible.

    Registre : A20"""
    raise NotImplementedError


def merge_buffs(*buffs: Buffs | None) -> Buffs:
    """Réunion de plusieurs buffs.

    Registre : A20"""
    raise NotImplementedError
