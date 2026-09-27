"""Simulation Monte Carlo du leveling (portée de seed/forever-mage/scripts/sim_leveling.py)."""

from __future__ import annotations

import random
from typing import Any, TypedDict

from forever.engine.model import Character, CharacterOverrides, GameData, Points


class KillResult(TypedDict):
    combat: float
    mana: float
    taken: float
    downtime: float
    total: float
    xp_h: float


def kill_mc(
    gd: GameData,
    level: int,
    pts: Points,
    ch: Character,
    rotation: str = "frost",
    rng: random.Random | None = None,
    **options: Any,
) -> KillResult:
    raise NotImplementedError


def mc(
    gd: GameData,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    n: int = 1500,
    seed: int = 12345,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> KillResult:
    raise NotImplementedError
