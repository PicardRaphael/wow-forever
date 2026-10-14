"""Sauvegarde et restauration de ce qui n'est pas sur GitHub (LN1, bloc E, décision 271).

Contenu : le profil joueur ; les SavedVariables (`WTF/Account/*/SavedVariables/*.lua` et
`WTF/Account/*/*/*/SavedVariables/*.lua`) et `WTF/Config.wtf` de l'installation lue (et de la bêta tant qu'elle
existe) ; les réglages du pont et le dossier de la conversation « addons » (son dépôt git local compris) ; les
attentes, l'état et la configuration de `forever update` ; le journal des versions du client ; le dernier instantané
des mesures. Jamais un jeton ni `.credentials.json`.

Forme : un dossier daté `<racine>/<AAAA-MM-JJTHHMMSS>/` (copie simple, lisible à la main) et son `manifest.json`
(chemin d'origine, empreinte, taille, produit et dossier de l'installation), écrit dans un dossier `.partiel` renommé
à la fin ; 14 gardées. Racine : `FOREVER_BACKUP_DIR`, sinon un disque fixe hors système (d'abord celui dont le nom
contient « sauvegarde » ou « backup »), sinon OneDrive connecté, sinon Documents avec un avertissement : jamais le
disque système par défaut (la remise à zéro du PC du 12 octobre a effacé tout C:).

Lecture et écriture sur disque seulement, jamais par le réseau."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from forever.config import Deps

BACKUP_SUBDIR = Path("WoW Forever") / "sauvegardes"
KEEP = 14
MIN_FREE = 1 << 30  # 1 Go libre au moins sur un disque de sauvegarde
DAILY_EVERY = timedelta(hours=24)
STAMP_FORMAT = "%Y-%m-%dT%H%M%S"
MANIFEST = "manifest.json"
PARTIAL_SUFFIX = ".partiel"
KINDS = ("profile", "wtf", "bridge", "update", "cache")
NEVER_COPIED = (".credentials.json",)


@dataclass(frozen=True)
class DriveInfo:
    """Disque fixe : racine, nom de volume, octets libres, disque système ou non."""

    root: Path
    label: str
    free: int
    system: bool


@dataclass(frozen=True)
class BackupInfo:
    stamp: str
    path: Path
    created_at: str
    reason: str
    files: int


@dataclass(frozen=True)
class RestorePlan:
    """Restauration prévue ou faite : fichiers écrits (origine), fichiers laissés de côté et pourquoi."""

    stamp: str
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    before: Path | None = None  # sauvegarde de l'état courant faite avant l'écrasement
    applied: bool = False


def backup_root(
    environ: Mapping[str, str], drives: Sequence[DriveInfo], onedrive: Path | None, documents: Path
) -> tuple[Path, str | None]:
    """(racine des sauvegardes, avertissement ou None)."""
    raise NotImplementedError


def default_root(deps: Deps) -> tuple[Path, str | None]:
    """Racine des sauvegardes de ce poste (disques fixes, OneDrive, Documents réels)."""
    raise NotImplementedError


def make_backup(deps: Deps, now: datetime, *, reason: str, root: Path | None = None) -> Path:
    """Une sauvegarde complète ; rend son dossier."""
    raise NotImplementedError


def prune(root: Path, keep: int = KEEP) -> list[Path]:
    """Retire les sauvegardes les plus anciennes au-delà de `keep` ; rend les dossiers retirés."""
    raise NotImplementedError


def list_backups(root: Path) -> list[BackupInfo]:
    """Sauvegardes complètes de la racine, de la plus ancienne à la plus récente."""
    raise NotImplementedError


def daily(deps: Deps, now: datetime, *, root: Path | None = None) -> Path | None:
    """Sauvegarde du jour si aucune n'a moins de 24 h et si le jeu est fermé ; None sinon."""
    raise NotImplementedError


def restore(
    deps: Deps,
    stamp: str | None,
    *,
    only: frozenset[str] = frozenset(),
    confirm: bool,
    root: Path | None = None,
) -> RestorePlan:
    """Restaure une sauvegarde (la plus récente si `stamp` est None)."""
    raise NotImplementedError


def manifest_of(path: Path) -> dict[str, Any]:
    raise NotImplementedError
