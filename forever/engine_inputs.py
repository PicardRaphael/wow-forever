"""Preuve d'entrées identiques par moteur, et rejeu ciblé (T08d, bloc B, décision 180, clause c).

Un moteur calculé (build du Mage, leveling du Mage, rendements décroissants des fiches PvP) ne lit qu'une partie des
données d'une version. Deux versions dont ces entrées sont identiques, hors métadonnées (source, dates de lecture,
reports de révision, provenance d'un correctif), donnent les mêmes résultats : aucune recommandation ne change, et
une installation peut se faire sans accord. C'est la méthode du rapport `docs/research/data-1.60.1.70170-r4.md`
(relevé instrumenté de `VersionData.read_json`, puis empreintes canoniques), devenue du code.

`ENGINES` déclare, pour chaque moteur, les fichiers lus en entier et les pointeurs lus dans un fichier partagé
(`classes.json`) ; la garde de complétude des tests vérifie que les lectures relevées pendant un cas réel y sont
incluses, pour que la preuve ne puisse pas devenir fausse en silence. Aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

PROVENANCE_FILES = frozenset({"sources.json", "manifest.json", "origins.json", "revisions.json"})


class EngineSpec(NamedTuple):
    """Moteur calculé : fichiers lus en entier, pointeurs lus par fichier partagé (`*` : toute clé), cas de rejeu."""

    name: str
    files: tuple[str, ...]
    pointers: Mapping[str, tuple[str, ...]]
    cases: tuple[str, ...]


class InputsDiff(NamedTuple):
    """Entrées d'un moteur comparées entre deux versions ; `items` : une ligne par fichier ou pointeur
    (`file`, `pointer`, `status` « identique » ou « différent », `before`, `after`, `leaves`)."""

    engine: str
    identical: bool
    items: list[dict[str, Any]]


ENGINES: Mapping[str, EngineSpec] = {}


def capture_reads(fn: Callable[[], Any]) -> set[tuple[str, str | None]]:
    """Lectures des données d'une version pendant `fn()` : (fichier, pointeur JSON ou None pour le fichier entier)."""
    raise NotImplementedError


def metadata_keys(*version_dirs: Path) -> frozenset[str]:
    """Clés de métadonnées exclues de la comparaison (`value_diff.META`, `metadata_keys` d'`origins.json`…)."""
    raise NotImplementedError


def canonical_sha(doc: Any, pointers: Sequence[str] | None, metadata: frozenset[str]) -> str:
    """Empreinte du JSON trié, sans les clés de métadonnées, du document entier ou des pointeurs donnés."""
    raise NotImplementedError


def covered(spec: EngineSpec, read: tuple[str, str | None]) -> bool:
    """Vrai si la lecture `(fichier, pointeur)` est incluse dans la déclaration du moteur."""
    raise NotImplementedError


def compare_inputs(before: Path, after: Path) -> dict[str, InputsDiff]:
    """Entrées de chaque moteur comparées entre deux dossiers de version."""
    raise NotImplementedError


def cases_to_replay(diffs: Mapping[str, InputsDiff]) -> list[tuple[str, str]]:
    """(moteur, cas) à rejouer : seulement les moteurs dont une entrée change."""
    raise NotImplementedError


def targeted_replay(diffs: Mapping[str, InputsDiff], replay: Callable[[str, str], Any]) -> dict[str, dict[str, Any]]:
    """Rejoue les seuls cas des moteurs touchés par `replay(moteur, cas)` ; rend {moteur: {cas: résultat}}."""
    raise NotImplementedError
