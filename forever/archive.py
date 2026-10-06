"""Archivage des fichiers du client par build (T08d, bloc A, décision 182), lecture locale seulement.

`Cache/ADB/<locale>/DBCache.bin` et `Logs/Hotfix.log` sont réécrits par le client : le `DBCache.bin` de 1.60.1.70205
a été remplacé par celui de 70235 avant d'être copié, et ses correctifs du serveur sont perdus. Ce module les copie
dans `<cache>/dbcache/<build>/` dès qu'ils changent, sans jamais écrire dans le dossier du client ni rien effacer :

- `DBCache.bin` est lu en entier et contrôlé par `dbcache.parse_dbcache` avant la copie (un fichier tronqué, copié
  pendant une écriture du client, n'est pas archivé et sera relu au passage suivant) ; il est rangé par le build de son
  en-tête ; un contenu différent pour le même build garde l'ancien sous `DBCache-<sha12>.bin` ;
- `Hotfix.log` grossit pendant une session du client et il est réécrit au démarrage suivant : une copie par session,
  reconnue à sa première ligne, remplacée tant que le fichier ne fait que grossir ;
- `index.json` de chaque build liste les copies (sha256, taille, dates, entrées, poussée maximale, source du build).

L'état du dernier passage (taille et date des fichiers vivants, échecs de lecture) est gardé dans
`<cache>/dbcache/state.json` : un fichier inchangé n'est pas relu. Aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from forever.config import Deps

ARCHIVE_DIR = "dbcache"
STATE_NAME = "state.json"
INDEX_NAME = "index.json"
FAILURE_ALERT = 3  # passages illisibles d'affilée avant une ligne de démarrage (paramètre de l'outil)


class ArchivedCopy(NamedTuple):
    """Une copie faite (ou déjà présente) d'un fichier du client."""

    kind: str  # "dbcache" | "hotfix_log"
    build: str  # "70235" : en-tête de DBCache.bin, ou build du client à la date du journal
    path: Path
    sha256: str
    size: int
    file_mtime: str
    copied_at: str
    new: bool


class ArchiveResult(NamedTuple):
    """Résultat d'un passage : copies faites, erreurs (jamais levées), build du client inscrit au journal."""

    copies: list[ArchivedCopy]
    errors: list[str]
    client_build: str | None


def archive_client_files(
    deps: Deps, *, locale: str = "enUS", read_bytes: Callable[[Path], bytes] = Path.read_bytes
) -> ArchiveResult:
    """Un passage d'archivage ; ne lève jamais (les erreurs sont dans le résultat)."""
    raise NotImplementedError


def archived_dbcache(cache_dir: Path, build: str) -> Path | None:
    """Copie la plus récente du `DBCache.bin` d'un build (`70235`), ou None."""
    raise NotImplementedError


def archive_line(cache_dir: Path) -> str | None:
    """Ligne de démarrage quand `DBCache.bin` est illisible depuis `FAILURE_ALERT` passages ; None sinon."""
    raise NotImplementedError
