"""Versions publiées du client (wago.tools) : seul appelant réseau de T01, via le client HTTP injecté
(`Deps.http_get`, en production `forever.pipeline.http_client.urllib_get`)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from forever.config import HTTP_TIMEOUT, USER_AGENT, HttpGet
from forever.errors import ForeverError
from forever.timefmt import parse_utc

BUILDS_URL = "https://wago.tools/api/builds"


@dataclass(frozen=True)
class Build:
    version: str
    created_at: datetime


class BuildsUnavailable(ForeverError):
    def __init__(self, message: str) -> None:
        super().__init__("builds_unavailable", message, "réessayer plus tard ou vérifier sur https://wago.tools/builds")


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def fetch_builds(http_get: HttpGet) -> object:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        body = http_get(BUILDS_URL, headers, HTTP_TIMEOUT)
    except OSError as exc:
        raise BuildsUnavailable(f"wago.tools injoignable : {exc}") from exc
    try:
        payload: object = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise BuildsUnavailable("réponse de wago.tools illisible (JSON invalide)") from exc
    return payload


def parse_builds(payload: object, product: str, prefix: str) -> list[Build]:
    """Versions du produit ayant le préfixe, dans l'ordre d'arrivée.

    Accepte un dict par produit (`{"wow_classic_beta": [...]}`) ou une liste d'entrées portant `product`.
    Les entrées mal formées sont ignorées."""
    if isinstance(payload, dict):
        items = payload.get(product, [])
    elif isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict) and x.get("product", product) == product]
    else:
        return []
    builds: list[Build] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        version, created = item.get("version"), item.get("created_at")
        if not (isinstance(version, str) and version.startswith(prefix) and isinstance(created, str)):
            continue
        try:
            version_key(version)
            builds.append(Build(version, parse_utc(created)))
        except ValueError:
            continue
    return builds


def latest_build(builds: Sequence[Build]) -> Build | None:
    return max(builds, key=lambda b: b.created_at, default=None)
