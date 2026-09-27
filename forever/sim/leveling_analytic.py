"""Modèle analytique du leveling (portée de seed/forever-mage/scripts/sim_leveling.py, `kill_analytic`)."""

from __future__ import annotations

from typing import Any

from forever.engine.model import CharacterOverrides, GameData, Points
from forever.sim.leveling_mc import KillResult


def kill_analytic(
    gd: GameData,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    over: CharacterOverrides | None = None,
    **options: Any,
) -> KillResult:
    raise NotImplementedError
