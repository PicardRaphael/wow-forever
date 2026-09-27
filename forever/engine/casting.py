"""Temps d'incantation."""

from __future__ import annotations

from forever.engine.model import Buffs, Character, GameData, Points, Rank


def cast_time(gd: GameData, key: str, rank: Rank, pts: Points, ch: Character, buffs: Buffs | None = None) -> float:
    """Temps d'incantation effectif : réductions de talents, hâte, plancher du temps de recharge global.

    Registre : B1, B2, B16"""
    raise NotImplementedError
