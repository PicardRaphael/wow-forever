"""Sorts : rang appris et coefficient de puissance des sorts."""

from __future__ import annotations

from forever.engine.model import GameData, Points, Rank


def best_rank(gd: GameData, key: str, level: int, pts: Points) -> Rank | None:
    """Plus haut rang appris au niveau donné. Un sort de talent exige le talent ; son rang 1 vient du talent.

    Registre : G4"""
    raise NotImplementedError


def coefficient(gd: GameData, key: str, rank: Rank) -> float:
    """Part de la puissance des sorts ajoutée aux dégâts d'un rang (pénalité des sorts de bas niveau comprise).

    Registre : G4"""
    raise NotImplementedError
