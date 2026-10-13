"""Livre des donjons de Forever (DJ1, bloc C) : client, addons et relevés du joueur fusionnés champ par champ.

Squelette (phase rouge) : signatures seulement."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.pipeline.dungeon_sources import SourceDungeons

ORDER = ("client", "naowh_dj", "fojji", "fdj", "forever_guide", "companion", "atlasloot", "zoneinfo")


class DungeonBook(NamedTuple):
    dungeons: dict[str, dict[str, Any]]
    sources: list[dict[str, Any]]
    notes: list[str]
    fingerprint: str
    from_cache: bool


def logged_boss_levels(monsters: Mapping[str, Any] | None) -> dict[int, list[int]]:
    raise NotImplementedError


def merge_dungeons(
    client: Mapping[str, Any] | None,
    sources: Sequence[SourceDungeons],
    *,
    book: Any = None,
    logged_levels: Mapping[int, Sequence[int]] | None = None,
    runs: Sequence[Mapping[str, Any]] = (),
    records: Mapping[str, Any] | None = None,
) -> DungeonBook:
    raise NotImplementedError


def build_dungeons(deps: Deps, *, wow_dir: Path | None = None, rebuild: bool = False) -> DungeonBook:
    raise NotImplementedError


def resolve(book: DungeonBook, text: str) -> str | None:
    raise NotImplementedError


def lookup_dungeons(book: DungeonBook, *, level: int | None = None, faction: str | None = None) -> list[dict[str, Any]]:
    raise NotImplementedError


def dungeon_info(
    book: DungeonBook,
    key: str,
    *,
    class_name: str | None = None,
    level: int | None = None,
    items: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    raise NotImplementedError


def where_item(book: DungeonBook, item: int) -> list[dict[str, Any]]:
    raise NotImplementedError


def render_report(book: DungeonBook) -> str:
    raise NotImplementedError
