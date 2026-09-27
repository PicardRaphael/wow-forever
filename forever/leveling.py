"""Simulation de leveling pour la CLI et le serveur MCP : validation, Monte Carlo et analytique, provenance."""

from __future__ import annotations

from typing import Any, TypedDict

from forever.config import Deps
from forever.provenance import Provenance
from forever.sim.leveling_mc import KillResult


class MobHpInfo(TypedDict):
    level: int
    value: float
    certainty: str
    source: str


class LevelingReport(TypedDict):
    level: int
    race: str
    rotation: str
    talents: dict[str, int]
    n: int
    seed: int
    options: dict[str, Any]
    monte_carlo: KillResult
    analytic: KillResult
    analytic_gap: float
    mob_hp: MobHpInfo
    provenance: Provenance


def parse_talents(text: str | None) -> dict[str, int]:
    raise NotImplementedError


def simulate_leveling(deps: Deps, level: int, **kwargs: Any) -> LevelingReport:
    raise NotImplementedError
