"""Fraîcheur des données locales par rapport à la dernière version publiée.

Seul `check_freshness(..., allow_network=True)` appelle le réseau (via `forever.pipeline.builds`) ;
les autres appels relisent le cache `<cache_dir>/status.json`."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, TypedDict

from forever.config import Deps
from forever.pipeline.builds import Build

Freshness = Literal["fresh", "stale", "unknown", "silent"]
CACHE_NAME = "status.json"


class FreshnessResult(TypedDict):
    freshness: Freshness
    checked_at: str | None
    age_hours: float | None
    latest_version: str | None
    latest_created_at: str | None
    source: Literal["network", "cache", "none"]
    assumptions: list[str]


def classify(local_version: str, latest: Build | None, now: datetime, silent_after: timedelta) -> Freshness:
    """Statut d'une observation ; `latest` à None : aucune version publiée avec le préfixe du produit."""
    raise NotImplementedError


def check_freshness(
    deps: Deps, local_version: str, *, product: str, prefix: str, allow_network: bool
) -> FreshnessResult:
    raise NotImplementedError


def freshness_for_version(deps: Deps, version: str, *, allow_network: bool) -> FreshnessResult:
    """Lit produit et préfixe dans `sources.json` de la version, puis appelle `check_freshness`."""
    raise NotImplementedError
