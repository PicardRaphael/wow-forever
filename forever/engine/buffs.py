"""Auras temporaires du Mage : Arcane Blast (cumuls, expiration, consommation, bonus de dégâts des autres sorts).

Chiffres du talent `arcaneBlast` (`talents.json`, variables d'infobulle) : dégâts min et max, bonus de dégâts des
autres sorts par cumul (%), hausse du coût d'Arcane Blast par cumul (%), cumuls maximum, durée (s)."""

from __future__ import annotations

from typing import NamedTuple

from forever.engine.model import Buffs, GameData, Points

TALENT = "arcaneBlast"
# Positions des variables du talent dans talents.json (lien talent -> effet, pas des chiffres de jeu).
DMG_PER_STACK, COST_PER_STACK, MAX_STACKS, DURATION = 2, 3, 4, 5


class ArcaneBlastAura(NamedTuple):
    stacks: int
    expires: float


def arcane_blast_max_stacks(gd: GameData, pts: Points) -> int:
    """Cumuls maximum de l'aura d'Arcane Blast (0 sans le talent).

    Registre : B15"""
    raise NotImplementedError


def arcane_blast_active(aura: ArcaneBlastAura | None, now: float) -> int:
    """Cumuls actifs à `now` (0 si l'aura est absente ou expirée).

    Registre : B15"""
    raise NotImplementedError


def arcane_blast_after_cast(gd: GameData, pts: Points, aura: ArcaneBlastAura | None, now: float) -> ArcaneBlastAura:
    """Aura après un Arcane Blast lancé à `now` : un cumul de plus (borné), durée relancée.

    Registre : B15"""
    raise NotImplementedError


def arcane_blast_bonus(gd: GameData, pts: Points, stacks: int, *, for_spell: str) -> Buffs:
    """Bonus de dégâts de l'aura pour `for_spell` : aucun sur Arcane Blast lui-même.

    Registre : B15"""
    raise NotImplementedError
