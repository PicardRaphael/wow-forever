"""Passage d'un donjon et niveau de placement (DJ1, bloc E), fonctions pures.

Registre : I16 (durée et monstres d'un passage), I17 (niveau de placement d'un donjon dans une route)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, NamedTuple


class RunModel(NamedTuple):
    minutes: float
    kills: float
    source: str  # measured | addon | formula
    certainty: str
    samples: int


class Pass(NamedTuple):
    xp: float
    seconds: float

    @property
    def xp_h(self) -> float:
        raise NotImplementedError


class Placement(NamedTuple):
    level: int
    share_h: float
    window: list[int]


def run_defaults(values: Mapping[str, Any]) -> dict[str, float]:
    raise NotImplementedError


def formula_run(params: Mapping[str, float], mob_level: float) -> tuple[float, float]:
    raise NotImplementedError


def run_model(
    params: Mapping[str, float],
    mob_level: float,
    *,
    measured: Sequence[float] = (),
    measured_kills: Sequence[float] = (),
    addon_kills: float | None = None,
) -> RunModel:
    raise NotImplementedError


def first_pass(
    *, run: RunModel, kill_xp: float, quests_xp: float, quests: int, travel_s: float, quest_overhead_s: float
) -> Pass:
    raise NotImplementedError


def repeat_pass(*, run: RunModel, kill_xp: float) -> Pass:
    raise NotImplementedError


def placement_level(
    levels: Sequence[int],
    first_pass_xp_h: Callable[[int], float | None],
    level_xp: Callable[[int], float],
    best_zone_xp_h: Callable[[int], float | None],
) -> Placement | None:
    raise NotImplementedError
