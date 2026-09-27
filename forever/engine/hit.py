"""Toucher des sorts."""

from __future__ import annotations

from forever.engine.model import Character, GameData, Points


def hit_chance(gd: GameData, school: str, level_diff: int, pts: Points, ch: Character) -> float:
    """Chance de toucher selon l'écart de niveau avec la cible, les talents et le toucher d'équipement.

    Registre : A3, A4, H1"""
    raise NotImplementedError
