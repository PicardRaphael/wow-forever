"""Veille locale du poste (`forever watch`, T08b, bloc G). Squelette."""

from __future__ import annotations

from typing import Any

from forever.config import Deps


def watch(deps: Deps, *, report: bool = False) -> dict[str, Any]:
    raise NotImplementedError


def watch_line(deps: Deps) -> str | None:
    raise NotImplementedError
