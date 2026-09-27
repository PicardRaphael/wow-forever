"""Mesures tirées des journaux de combat — squelette T04 (tests rouges)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from forever.pipeline.combatlog import Event


class HitTally(NamedTuple):
    counts: dict[tuple[str, int], dict[str, object]]
    assumptions: list[str]


def find_mine(events: Iterable[Event]) -> str | None:
    raise NotImplementedError


def monster_hp(events: Iterable[Event], *, log: str = "") -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    raise NotImplementedError


def spell_costs(events: Iterable[Event], caster: str) -> dict[int, set[int]]:
    raise NotImplementedError


def gcd_intervals(events: Iterable[Event], caster: str, *, max_gap_s: float) -> list[float]:
    raise NotImplementedError


def cast_times(events: Iterable[Event], caster: str) -> dict[int, list[float]]:
    raise NotImplementedError


def crit_ratios(events: Iterable[Event], caster: str) -> list[tuple[int, float]]:
    raise NotImplementedError


def hit_tally(events: Iterable[Event], caster: str, caster_level: int | None) -> HitTally:
    raise NotImplementedError
