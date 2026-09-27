"""Graphique de leveling (PNG) : temps par monstre et XP par heure, niveau par niveau."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypedDict

from forever.engine.model import GameData, Points


class ChartResult(TypedDict):
    path: str
    levels: list[dict[str, Any]]
    omitted: list[dict[str, Any]]


def leveling_chart(
    gd: GameData,
    levels: Iterable[int],
    pts: Points,
    *,
    race: str = "Orc",
    rotation: str = "frost",
    n: int = 300,
    seed: int = 12345,
    options: dict[str, Any] | None = None,
    out: Path,
) -> ChartResult:
    raise NotImplementedError
