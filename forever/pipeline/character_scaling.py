"""Ratios du personnage décodés du client (`character_scaling.json`, T08b, bloc A).

Squelette : implémentation au bloc A2 vert."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.pipeline.tables import Row

CHARACTER_FILE = "character_scaling.json"
CHARACTER_FILES = (CHARACTER_FILE,)

GameTable = list[dict[str, float]]


def character_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    raise NotImplementedError


def load_character_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    raise NotImplementedError


def read_gametable(path: Path) -> GameTable:
    raise NotImplementedError


def load_gametables(gt_dir: Path, rules: Mapping[str, Any]) -> dict[str, GameTable | None]:
    raise NotImplementedError


def decode_character_scaling(
    tables: Mapping[str, Sequence[Row]],
    rules: Mapping[str, Any],
    gametables: Mapping[str, GameTable | None],
    version: str,
) -> dict[str, Any]:
    raise NotImplementedError


def character_errors(doc: Any, classes: Sequence[str]) -> list[str]:
    raise NotImplementedError
