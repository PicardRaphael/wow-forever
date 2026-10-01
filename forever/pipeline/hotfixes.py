"""Correctifs du serveur lus dans `Logs/Hotfix.log` (T08b, bloc E). Squelette : implémentation au bloc E vert."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

JOURNAL_NAME = "hotfixes.json"
HOTFIX_LOG = ("Logs", "Hotfix.log")


class HotfixLine(NamedTuple):
    at: str
    push: str
    table: str
    rec_id: int
    result: str


def parse_hotfix_log(text: str, year: int) -> list[HotfixLine]:
    raise NotImplementedError


def log_year(path: Path) -> int:
    raise NotImplementedError


def tracked_tables(rules: Mapping[str, Any]) -> set[str]:
    raise NotImplementedError


def load_journal(cache_dir: Path) -> list[dict[str, Any]]:
    raise NotImplementedError


def update_journal(
    cache_dir: Path, lines: Iterable[HotfixLine], tracked: set[str], client_build: str | None, seen_at: datetime
) -> list[dict[str, Any]]:
    raise NotImplementedError


def summarize(entries: Sequence[Mapping[str, Any]], since: str | None = None) -> dict[str, Any]:
    raise NotImplementedError


def touched_entities(entries: Sequence[Mapping[str, Any]], csv_dir: Path, version_dir: Path) -> list[dict[str, Any]]:
    raise NotImplementedError
