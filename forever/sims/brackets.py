"""Dégâts par tranche de niveaux (SIM2, décision 305) : squelette."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from forever.config import Deps
from forever.pipeline import gitops
from forever.sims.wowsims import Preset

BRACKETS: dict[str, int] = {}
SLOT_NAMES: tuple[str, ...] = ()


def parse_brackets(text: str | None) -> list[tuple[str, int]]:
    raise NotImplementedError


def talents_at(steps: Sequence[Mapping[str, Any]], level: int) -> dict[str, int]:
    raise NotImplementedError


def equipment_from_picks(picks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    raise NotImplementedError


def solo_preset(preset: Preset, *, talents: str, equipment: dict[str, Any]) -> Preset:
    raise NotImplementedError


def encounter_at(encounter: dict[str, Any] | None, level: int) -> dict[str, Any]:
    raise NotImplementedError


def run_brackets(
    deps: Deps,
    *,
    preset: str,
    race: str | None,
    brackets: str | None,
    steps: Sequence[Mapping[str, Any]],
    picks_at: Callable[[int], Sequence[Mapping[str, Any]]] | None,
    iterations: int | None = None,
    runner: gitops.Runner | None = None,
) -> dict[str, Any]:
    raise NotImplementedError
