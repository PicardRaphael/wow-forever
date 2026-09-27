"""Critique des sorts : chance et multiplicateur."""

from __future__ import annotations

from forever.engine.model import Buffs, Character, GameData, Points


def crit_chance(
    gd: GameData,
    key: str,
    school: str,
    pts: Points,
    ch: Character,
    *,
    frozen: bool = False,
    wc_stacks: int = 0,
    buffs: Buffs | None = None,
) -> float:
    """Chance de critique d'un sort (personnage, talents, cible gelée, Winter's Chill, buffs), bornée à [0, 1].

    Registre : A5, D4"""
    raise NotImplementedError


def crit_mult(gd: GameData, school: str, pts: Points) -> float:
    """Multiplicateur des dégâts d'un coup critique, talents d'école compris.

    Registre : A21"""
    raise NotImplementedError
