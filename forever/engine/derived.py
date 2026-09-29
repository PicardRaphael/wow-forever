"""Valeurs dérivées des talents à cumuls (T06b, décision D4) : squelette."""

from __future__ import annotations

from typing import Any

from forever.engine.model import GameData


def stack_tables(gd: GameData, talent: str, level: int | None = None) -> list[dict[str, Any]]:
    raise NotImplementedError("T06b : valeurs par cumul")
