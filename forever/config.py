"""Configuration de l'outil et dépendances injectées (données, cache, réseau, horloge).

Les constantes de ce module décrivent l'outil (cache, délais), jamais le jeu. Le client HTTP de production vit dans
`forever/pipeline/` (règle réseau) ; ce module ne fait que l'injecter."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from forever import __version__
from forever.pipeline.http_client import urllib_get

HttpGet = Callable[[str, Mapping[str, str], float], bytes]
"""(url, en-têtes, délai en secondes) -> corps de la réponse ; lève OSError en cas d'échec."""

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
DATA_DIR = PACKAGE_DIR / "data"
REGISTRY_PATH = REPO_ROOT / "docs" / "MECHANICS_REGISTRY.yaml"

CACHE_TTL = timedelta(hours=6)
SILENT_AFTER = timedelta(days=14)
HTTP_TIMEOUT = 2.0
FETCH_TIMEOUT = 30.0  # téléchargement d'une table CSV (plusieurs Mo)
USER_AGENT = f"forever-core/{__version__}"
DEFAULT_WOW_DIR = Path(r"C:\Program Files (x86)\World of Warcraft\_classic_beta_")
# Mesure des journaux : au-delà de cet écart, deux sorts instantanés ne sont pas « enchaînés » (paramètre de
# l'outil, modifiable par --max-gap ; ce n'est pas une règle du jeu).
CHAIN_MAX_GAP_S = 3.0


@dataclass(frozen=True)
class Deps:
    """Tout ce qui touche au monde extérieur, passé explicitement à la CLI et au serveur MCP."""

    data_dir: Path
    registry_path: Path
    cache_dir: Path
    http_get: HttpGet
    now: Callable[[], datetime]
    offline: bool = False
    wow_dir: Path | None = None  # dossier du client (journaux, addons, SavedVariables), lu sans réseau
    confirm: Callable[[str], bool] | None = None  # demande d'accord avant une écriture (None : refus)


def terminal_confirm(prompt: str) -> bool:
    """Accord demandé sur le terminal (question sur la sortie d'erreur, « o » ou « oui ») ; refus si l'entrée
    standard n'est pas un terminal."""
    if not sys.stdin.isatty():
        return False
    print(prompt, end="", file=sys.stderr, flush=True)
    return input().strip().lower() in ("o", "oui")


def utc_now() -> datetime:
    """Heure courante en UTC, avec fuseau."""
    return datetime.now(UTC)


def default_cache_dir(environ: Mapping[str, str] = os.environ) -> Path:
    """FOREVER_CACHE_DIR, sinon ~/.cache/forever."""
    configured = environ.get("FOREVER_CACHE_DIR")
    return Path(configured) if configured else Path.home() / ".cache" / "forever"


# Emplacements usuels du client sous Windows, dans l'ordre d'essai (Program Files 32 bits, puis 64 bits).
WOW_DIR_CANDIDATES: tuple[Path, ...] = (
    DEFAULT_WOW_DIR,
    Path(r"C:\Program Files\World of Warcraft\_classic_beta_"),
)


def default_wow_dir(environ: Mapping[str, str] = os.environ, exists: Callable[[Path], bool] = Path.is_dir) -> Path:
    """FOREVER_WOW_DIR, sinon le premier dossier de `WOW_DIR_CANDIDATES` présent, sinon le dossier de la bêta Forever
    sous Program Files (x86)."""
    configured = environ.get("FOREVER_WOW_DIR")
    if configured:
        return Path(configured)
    return next((p for p in WOW_DIR_CANDIDATES if exists(p)), DEFAULT_WOW_DIR)


def default_deps(environ: Mapping[str, str] = os.environ) -> Deps:
    """Dépendances de production ; FOREVER_OFFLINE=1 interdit tout appel réseau."""
    return Deps(
        data_dir=DATA_DIR,
        registry_path=REGISTRY_PATH,
        cache_dir=default_cache_dir(environ),
        http_get=urllib_get,
        now=utc_now,
        offline=environ.get("FOREVER_OFFLINE", "") not in ("", "0"),
        wow_dir=default_wow_dir(environ),
        confirm=terminal_confirm,
    )
