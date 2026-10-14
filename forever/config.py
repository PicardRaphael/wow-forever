"""Configuration de l'outil et dépendances injectées (données, cache, réseau, horloge).

Les constantes de ce module décrivent l'outil (cache, délais), jamais le jeu. Le client HTTP de production vit dans
`forever/pipeline/` (règle réseau) ; ce module ne fait que l'injecter."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from forever import __version__
from forever.installs import fixed_drives, no_drives, survey
from forever.pipeline.http_client import urllib_get
from forever.pipeline.live_logs import detect_game_running

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
# Décision 230 : chaque table est essayée au plus FETCH_ATTEMPTS fois ; le délai de la requête double à chaque essai
# (FETCH_TIMEOUT, puis 2 et 4 fois), avec une attente croissante entre deux essais (secondes).
FETCH_ATTEMPTS = 3
FETCH_BACKOFF = (5.0, 15.0)
USER_AGENT = f"forever-core/{__version__}"
# Repli quand aucune installation n'est trouvée ni déclarée (LN1 : le choix vient de `forever.installs`).
FALLBACK_WOW_DIR = Path(r"C:\Program Files (x86)\World of Warcraft\_classic_beta_")
# Mesure des journaux : au-delà de cet écart, deux sorts instantanés ne sont pas « enchaînés » (paramètre de
# l'outil, modifiable par --max-gap ; ce n'est pas une règle du jeu).
CHAIN_MAX_GAP_S = 3.0
# Mise à jour automatique (T08d, décision 180) : passage au démarrage au plus toutes les 6 h (CACHE_TTL), verrou
# déclaré périmé après 3 h, attente de la CI limitée à 60 min. Paramètres de l'outil, pas des chiffres de jeu.
UPDATE_LOCK_STALE = timedelta(hours=3)
UPDATE_CI_TIMEOUT = timedelta(minutes=60)
UPDATE_HOTFIX_WAIT = timedelta(hours=24)  # attente du DBCache.bin d'une nouvelle version (décision 207)


def game_closed() -> bool | None:
    """État du jeu par défaut des Deps construites à la main (tests) : fermé."""
    return False


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
    profile_path: Path | None = None  # profil joueur hors du dépôt (None : FOREVER_PROFILE ou ~/.forever, T06b)
    game_running: Callable[[], bool | None] = game_closed  # client lancé ? None : inconnu (décision 205)
    sleep: Callable[[float], None] = time.sleep  # attente entre deux essais d'un téléchargement (décision 230)
    # Variables d'environnement et disques fixes lus pour trouver les installations du client (LN1) : vides dans les
    # dépendances construites à la main (tests), jamais le disque réel.
    environ: Mapping[str, str] = field(default_factory=dict)
    drives: Callable[[], list[Path]] = no_drives


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


def deps_drives(environ: Mapping[str, str]) -> Callable[[], list[Path]]:
    """Disques fixes examinés pour trouver le client ; aucun si `FOREVER_WOW_NO_DRIVES` est posée (suite de tests :
    jamais l'installation réelle du poste)."""
    return no_drives if environ.get("FOREVER_WOW_NO_DRIVES", "") not in ("", "0") else fixed_drives


def default_wow_dir(
    environ: Mapping[str, str] = os.environ,
    *,
    drives: Callable[[], list[Path]] | None = None,
    cache_dir: Path | None = None,
    data_dir: Path = DATA_DIR,
) -> Path:
    """Dossier du client choisi par `forever.installs` (`FOREVER_WOW_FORCE`, version finale adoptée, bêta,
    `FOREVER_WOW_DIR`, LN1) ; à défaut `FOREVER_WOW_DIR` même absent, sinon `FALLBACK_WOW_DIR`."""
    choice, _ = survey(
        environ,
        drives=drives or deps_drives(environ),
        cache_dir=cache_dir or default_cache_dir(environ),
        data_dir=data_dir,
    )
    if choice.folder is not None:
        return choice.folder
    configured = environ.get("FOREVER_WOW_DIR", "").strip()
    return Path(configured) if configured else FALLBACK_WOW_DIR


def default_deps(environ: Mapping[str, str] = os.environ) -> Deps:
    """Dépendances de production ; FOREVER_OFFLINE=1 interdit tout appel réseau."""
    drives = deps_drives(environ)
    wow_dir = default_wow_dir(environ, drives=drives)
    return Deps(
        data_dir=DATA_DIR,
        registry_path=REGISTRY_PATH,
        cache_dir=default_cache_dir(environ),
        http_get=urllib_get,
        now=utc_now,
        offline=environ.get("FOREVER_OFFLINE", "") not in ("", "0"),
        wow_dir=wow_dir,
        confirm=terminal_confirm,
        game_running=lambda: detect_game_running(wow_dir),
        environ=environ,
        drives=drives,
    )
