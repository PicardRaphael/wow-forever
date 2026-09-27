"""Déplacements du combat de leveling : temps de vol, course du monstre, ralentis, gel, portée."""

from __future__ import annotations

from forever.engine.model import GameData, Points, Rank


def travel_time(gd: GameData, key: str, distance_yd: float, *, analytic: bool = False) -> float:
    """Registre : C1"""
    raise NotImplementedError


def frostbolt_slow(gd: GameData, pts: Points) -> float:
    """Registre : C5"""
    raise NotImplementedError


def chill_duration(gd: GameData, rank: Rank, pts: Points) -> float:
    """Registre : C5"""
    raise NotImplementedError


def mob_speed(gd: GameData, slow: float) -> float:
    """Registre : C5"""
    raise NotImplementedError


def frostbite_chance(gd: GameData, pts: Points) -> float:
    """Registre : C5"""
    raise NotImplementedError


def frostbite_freeze_s(gd: GameData) -> float:
    """Registre : C5"""
    raise NotImplementedError


def spell_range(gd: GameData, key: str, pts: Points) -> float:
    """Registre : C2"""
    raise NotImplementedError


def attacker_swing_s(gd: GameData, *, frost_armor: bool) -> float:
    """Registre : C5"""
    raise NotImplementedError
