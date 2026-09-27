"""Configuration de l'outil et dépendances injectées (données, cache, réseau, horloge).

Les constantes de ce module décrivent l'outil (cache, délais), jamais le jeu."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from forever import __version__

HttpGet = Callable[[str, Mapping[str, str], float], bytes]
"""(url, en-têtes, délai en secondes) -> corps de la réponse ; lève OSError en cas d'échec."""

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
DATA_DIR = PACKAGE_DIR / "data"
REGISTRY_PATH = REPO_ROOT / "docs" / "MECHANICS_REGISTRY.yaml"

CACHE_TTL = timedelta(hours=6)
SILENT_AFTER = timedelta(days=14)
HTTP_TIMEOUT = 2.0
USER_AGENT = f"forever-core/{__version__}"


@dataclass(frozen=True)
class Deps:
    """Tout ce qui touche au monde extérieur, passé explicitement à la CLI et au serveur MCP."""

    data_dir: Path
    registry_path: Path
    cache_dir: Path
    http_get: HttpGet
    now: Callable[[], datetime]
    offline: bool = False


def urllib_get(url: str, headers: Mapping[str, str], timeout: float) -> bytes:
    """Client HTTP de production (bibliothèque standard)."""
    raise NotImplementedError


def utc_now() -> datetime:
    """Heure courante en UTC, avec fuseau."""
    raise NotImplementedError


def default_cache_dir(environ: Mapping[str, str] = os.environ) -> Path:
    """FOREVER_CACHE_DIR, sinon ~/.cache/forever."""
    raise NotImplementedError


def default_deps(environ: Mapping[str, str] = os.environ) -> Deps:
    """Dépendances de production ; FOREVER_OFFLINE=1 interdit tout appel réseau."""
    raise NotImplementedError
