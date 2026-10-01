"""Sonde de l'API Blizzard (T08b, point 10). Squelette."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps

TOKEN_URL = "https://oauth.battle.net/token"


def candidate_namespaces(region: str) -> list[str]:
    raise NotImplementedError


def is_forever_namespace(namespace: str) -> bool:
    raise NotImplementedError


def load_keys(environ: Mapping[str, str], env_file: Path | None) -> dict[str, str]:
    raise NotImplementedError


def probe(
    deps: Deps,
    keys: Mapping[str, str],
    *,
    regions: Sequence[str] = ("eu", "us"),
    http_post: Callable[..., bytes] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    raise NotImplementedError


def probe_issue_body(result: Mapping[str, Any]) -> str:
    raise NotImplementedError
