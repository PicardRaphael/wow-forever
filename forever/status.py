"""Rapport d'état : version locale, fraîcheur, intégrité, couverture du registre."""

from __future__ import annotations

from typing import TypedDict

from forever.config import Deps
from forever.freshness import FreshnessResult
from forever.provenance import Provenance


class IntegrityInfo(TypedDict):
    ok: bool
    manifest_found: bool
    mismatched: list[str]
    missing: list[str]
    unexpected: list[str]


class StatusReport(TypedDict):
    local_version: str
    freshness: FreshnessResult
    integrity: IntegrityInfo
    registry_coverage: str
    provenance: Provenance


def status_report(deps: Deps, *, allow_network: bool = True) -> StatusReport:
    raise NotImplementedError
