"""Mesure des accélérations de la conversation « jeu » (P06b, bloc G, décision 235)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Variant:
    name: str
    thinking_off: bool
    persistent: bool


VARIANTS: dict[str, Variant] = {}


def variant_env(env: Mapping[str, str], variant: Variant) -> dict[str, str]:
    raise NotImplementedError


def quality_failures(result: Any, plan: Any, baseline_link: str | None) -> list[str]:
    raise NotImplementedError


def keep(baseline: Sequence[float], candidate: Sequence[float], failures: int) -> bool:
    raise NotImplementedError
