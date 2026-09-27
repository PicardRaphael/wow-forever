"""Lecteur local de Questie — squelette T04 (tests rouges)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple


class QuestieNpc(NamedTuple):
    id: int
    name: str
    min_level_health: int
    max_level_health: int
    min_level: int
    max_level: int
    rank: int
    zone_id: int


def read_questie(addon_dir: Path) -> Any:
    raise NotImplementedError
