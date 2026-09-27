"""Lecture des journaux de combat du client (`WoWCombatLog-*.txt`, format 22 avancé) — squelette T04 (tests rouges)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import NamedTuple


class LogHeader(NamedTuple):
    version: int
    advanced: bool
    build: str
    project_id: int


class Unit(NamedTuple):
    guid: str
    name: str | None
    flags: int
    raid_flags: int


class Advanced(NamedTuple):
    guid: str
    owner: str
    hp: int
    max_hp: int
    attack_power: int
    spell_power: int
    armor: int
    absorb: int
    unknown_a: int
    unknown_b: int
    power_type: int
    power: int
    max_power: int
    power_cost: int
    x: float
    y: float
    ui_map_id: int
    facing: float
    level: int


class Event(NamedTuple):
    line: int
    time: datetime
    name: str
    source: Unit | None
    dest: Unit | None
    spell: tuple[int, str, int] | None
    advanced: Advanced | None
    suffix: Mapping[str, object]
    raw: tuple[str, ...]


class LogSummary(NamedTuple):
    name: str
    path: Path
    header: LogHeader | None
    start: datetime | None
    end: datetime | None
    lines: int
    events: int
    mine: list[str]
    error: str | None


def read_log(path: Path) -> tuple[LogHeader, Iterator[Event]]:
    raise NotImplementedError


def scan_logs(directory: Path) -> list[LogSummary]:
    raise NotImplementedError
