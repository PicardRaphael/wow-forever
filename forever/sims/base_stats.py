"""Statistiques de base au niveau du personnage pour wowsims corrigé (SIM2 bloc 4, décision 305) : squelette."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps


def client_scaling(deps: Deps, class_name: str, level: int) -> dict[str, float]:
    raise NotImplementedError


def base_stats_doc(
    class_token: str, scaling: Mapping[str, float], anchors: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    raise NotImplementedError


def anchor_note(anchors: Sequence[Mapping[str, Any]], level: int) -> str:
    raise NotImplementedError
