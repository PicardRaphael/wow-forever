"""Fraîcheur des données locales par rapport à la dernière version publiée.

Seul `check_freshness(..., allow_network=True)` appelle le réseau (via `forever.pipeline.builds`) ;
les autres appels relisent le cache `<cache_dir>/status.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, TypedDict

from forever.config import CACHE_TTL, SILENT_AFTER, Deps
from forever.pipeline.builds import Build, BuildsUnavailable, fetch_builds, latest_build, parse_builds, version_key
from forever.store import read_sources
from forever.timefmt import format_age, format_utc, parse_utc

Freshness = Literal["fresh", "stale", "unknown", "silent"]
CACHE_NAME = "status.json"
CACHE_SCHEMA_VERSION = 1


class FreshnessResult(TypedDict):
    freshness: Freshness
    checked_at: str | None
    age_hours: float | None
    latest_version: str | None
    latest_created_at: str | None
    source: Literal["network", "cache", "none"]
    assumptions: list[str]


@dataclass(frozen=True)
class Observation:
    """Dernière observation réussie de wago : moment de la lecture et version la plus récente (None : aucune)."""

    fetched_at: datetime
    latest: Build | None


def classify(local_version: str, latest: Build | None, now: datetime, silent_after: timedelta) -> Freshness:
    """Statut d'une observation ; `latest` à None : aucune version publiée avec le préfixe du produit."""
    if latest is None:
        return "silent"
    if version_key(latest.version) > version_key(local_version):
        return "stale"
    if now - latest.created_at > silent_after:
        return "silent"
    return "fresh"


def _read_cache(cache_dir: Path, product: str) -> Observation | None:
    try:
        data = json.loads((cache_dir / CACHE_NAME).read_text(encoding="utf-8"))
        if data.get("schema_version") != CACHE_SCHEMA_VERSION or data.get("product") != product:
            return None
        latest = data.get("latest")
        build = Build(latest["version"], parse_utc(latest["created_at"])) if latest else None
        return Observation(parse_utc(data["fetched_at"]), build)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None  # cache absent ou illisible : comme s'il n'existait pas


def _write_cache(cache_dir: Path, product: str, local_version: str, obs: Observation, freshness: Freshness) -> None:
    latest = {"version": obs.latest.version, "created_at": format_utc(obs.latest.created_at)} if obs.latest else None
    data = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "freshness": freshness,
        "computed_at": format_utc(obs.fetched_at),
        "local_version": local_version,
        "fetched_at": format_utc(obs.fetched_at),
        "latest": latest,
        "product": product,
    }
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / CACHE_NAME).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass  # un cache non écrit ne doit pas faire échouer la commande


def _result(
    freshness: Freshness,
    obs: Observation | None,
    now: datetime,
    source: Literal["network", "cache", "none"],
    assumptions: list[str],
) -> FreshnessResult:
    age = round((now - obs.fetched_at).total_seconds() / 3600, 1) if obs else None
    latest = obs.latest if obs else None
    return {
        "freshness": freshness,
        "checked_at": format_utc(obs.fetched_at) if obs else None,
        "age_hours": age,
        "latest_version": latest.version if latest else None,
        "latest_created_at": format_utc(latest.created_at) if latest else None,
        "source": source,
        "assumptions": assumptions,
    }


def _status_assumptions(freshness: Freshness, obs: Observation, prefix: str) -> list[str]:
    if freshness == "stale" and obs.latest:
        return [f"version plus récente publiée : {obs.latest.version} (données locales antérieures)"]
    if freshness == "silent":
        if obs.latest is None:
            return [f"aucune version {prefix}x publiée pour le produit : possible changement de produit"]
        return [f"aucune nouvelle version depuis le {obs.latest.created_at:%Y-%m-%d} : possible changement de produit"]
    return []


def check_freshness(
    deps: Deps, local_version: str, *, product: str, prefix: str, allow_network: bool
) -> FreshnessResult:
    now = deps.now()
    cached = _read_cache(deps.cache_dir, product)

    if allow_network and not deps.offline:
        if cached and now - cached.fetched_at < CACHE_TTL:
            freshness = classify(local_version, cached.latest, now, SILENT_AFTER)
            return _result(freshness, cached, now, "cache", _status_assumptions(freshness, cached, prefix))
        try:
            payload = fetch_builds(deps.http_get)
        except BuildsUnavailable as exc:
            if cached is None:
                return _result("unknown", None, now, "none", [f"fraîcheur inconnue : {exc.message}"])
            last = classify(local_version, cached.latest, now, SILENT_AFTER)
            age = format_age((now - cached.fetched_at).total_seconds() / 3600)
            note = f"réseau indisponible : dernier état connu {last}, vérifié il y a {age}"
            return _result("unknown", cached, now, "cache", [note])
        obs = Observation(now, latest_build(parse_builds(payload, product, prefix)))
        freshness = classify(local_version, obs.latest, now, SILENT_AFTER)
        _write_cache(deps.cache_dir, product, local_version, obs, freshness)
        return _result(freshness, obs, now, "network", _status_assumptions(freshness, obs, prefix))

    if cached is None:
        return _result("unknown", None, now, "none", ["fraîcheur jamais vérifiée (lancer `forever status`)"])
    freshness = classify(local_version, cached.latest, now, SILENT_AFTER)
    assumptions = _status_assumptions(freshness, cached, prefix)
    age_h = (now - cached.fetched_at).total_seconds() / 3600
    if now - cached.fetched_at > CACHE_TTL:
        assumptions.append(f"fraîcheur vérifiée il y a {format_age(age_h)} (lancer `forever status`)")
    return _result(freshness, cached, now, "cache", assumptions)


def freshness_for_version(deps: Deps, version: str, *, allow_network: bool) -> FreshnessResult:
    """Lit produit et préfixe dans `sources.json` de la version, puis appelle `check_freshness`."""
    sources = read_sources(deps.data_dir, version) or {}
    product, prefix = sources.get("product"), sources.get("version_prefix")
    if not (isinstance(product, str) and isinstance(prefix, str)):
        return _result("unknown", None, deps.now(), "none", [f"produit inconnu : sources.json absent pour {version}"])
    return check_freshness(deps, version, product=product, prefix=prefix, allow_network=allow_network)
