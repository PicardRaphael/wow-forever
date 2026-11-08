"""Analyse complète gardée par spécialisation et tranche (SIM2 bloc 15) : squelette."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from forever.config import Deps


def analysis_path(deps: Deps, preset: str, race: str) -> Path:
    raise NotImplementedError


def analyse_spec(deps: Deps, *, preset: str, race: str, brackets: str | None = None,
                 run: Callable[..., dict[str, Any]] | None = None, gear: Callable[..., dict[str, Any]] | None = None,
                 steps: Callable[[], tuple[list[dict[str, Any]], str]] | None = None) -> dict[str, Any]:  # fmt: skip
    raise NotImplementedError


def read_analysis(deps: Deps, preset: str, race: str) -> dict[str, Any] | None:
    raise NotImplementedError
