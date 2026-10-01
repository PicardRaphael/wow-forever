"""Origine déclarée de chaque valeur des données (`forever/data/<version>/origins.json`, T08b, bloc H).

Squelette : implémentation au bloc H vert."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ORIGINS_NAME = "origins.json"
ORIGINS = ("client", "journal", "addon", "manuel", "copie_figee", "parametre")


@dataclass(frozen=True)
class OriginIssue:
    kind: str
    version: str
    file: str
    path: str
    message: str


@dataclass
class OriginsReport:
    versions: list[str] = field(default_factory=list)
    issues: list[OriginIssue] = field(default_factory=list)
    leaves: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class InventoryRow:
    file: str
    path: str
    certainty: str
    reason: str
    source: str
    registry: str
    leaves: int


@dataclass(frozen=True)
class PendingRow:
    file: str
    path: str
    declared: str
    target: str
    reason: str
    until: str


def check_version(data_dir: Path, version: str) -> OriginsReport:
    raise NotImplementedError


def check_all(data_dir: Path) -> OriginsReport:
    raise NotImplementedError


def inventory(data_dir: Path, version: str) -> tuple[list[InventoryRow], list[PendingRow]]:
    raise NotImplementedError


def render_inventory(version: str, rows: Sequence[InventoryRow], pending: Sequence[PendingRow]) -> str:
    raise NotImplementedError


def inventory_payload(version: str, rows: Sequence[InventoryRow], pending: Sequence[PendingRow]) -> dict[str, Any]:
    raise NotImplementedError


def main(argv: Sequence[str], data_dir: Path | None = None) -> int:
    raise NotImplementedError
