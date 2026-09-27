"""Coût en mana."""

from __future__ import annotations

from forever.engine.model import Buffs, Character, GameData, Points, Rank


def mana_cost(gd: GameData, key: str, rank: Rank, pts: Points, ch: Character, buffs: Buffs | None = None) -> float:
    """Coût d'un lancer : coût du rang (ou part du mana de base), réductions de talents, buffs de coût.

    Registre : B11, B17"""
    raise NotImplementedError
