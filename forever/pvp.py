"""Fiches PvP par classe et par affrontement (PV1, bloc D) : service de lecture, aucun calcul de combat (squelette)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.config import Deps
from forever.store import VersionData

LIMIT = (
    "Aucun suivi en direct des recharges adverses : le journal de combat est refusé aux addons sur Forever et les "
    "valeurs de combat y sont secrètes (docs/research/addon-forever.md) ; ces fiches sont fixes, à consulter hors "
    "combat ou affichées en jeu par l'addon (FA1p)."
)


def class_sheet(
    data: VersionData, cls: str, level: int | None = None, talents: Mapping[str, int] | None = None
) -> dict[str, Any]:
    raise NotImplementedError


def matchup(data: VersionData, mine: Mapping[str, Any], opponent: Mapping[str, Any]) -> dict[str, Any]:
    raise NotImplementedError


def pvp_report(
    deps: Deps,
    cls: str,
    *,
    opponent: str | None = None,
    level: int | None = None,
    race: str | None = None,
    talents: Mapping[str, int] | None = None,
    opponent_level: int | None = None,
) -> dict[str, Any]:
    raise NotImplementedError


def compact(report: Mapping[str, Any], *, detail: bool = False, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    raise NotImplementedError
