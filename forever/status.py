"""Rapport d'état : version locale, fraîcheur, intégrité, couverture du registre."""

from __future__ import annotations

from typing import TypedDict

from forever.config import Deps
from forever.freshness import FreshnessResult, freshness_for_version
from forever.manifest import verify
from forever.provenance import Provenance, make_provenance
from forever.store import current_identity, describe_integrity


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
    report = verify(deps.data_dir)
    local_version, sha = current_identity(deps.data_dir)
    fresh = freshness_for_version(deps, local_version, allow_network=allow_network)
    assumptions = list(fresh["assumptions"])
    if not report.manifest_found:
        assumptions.append("manifeste absent : lancer `forever manifest --update`")
    elif not report.ok:
        assumptions.append(f"empreintes invalides ({describe_integrity(report)}) : les consultations sont refusées")
    provenance = make_provenance(
        deps,
        game_version=local_version,
        data_sha=sha,
        freshness=fresh["freshness"],
        certainty="certain",
        assumptions=assumptions,
    )
    return {
        "local_version": local_version,
        "freshness": fresh,
        "integrity": {
            "ok": report.ok,
            "manifest_found": report.manifest_found,
            "mismatched": report.mismatched,
            "missing": report.missing,
            "unexpected": report.unexpected,
        },
        "registry_coverage": provenance["registry_coverage"],
        "provenance": provenance,
    }
