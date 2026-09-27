"""Désignation d'une version de données : identifiant d'une version du dépôt ou chemin d'une version candidate.

Une version candidate est un dossier de données complet (`manifest.json` + un seul dossier de version), produit par
`forever decode` hors de `forever/data/`."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from forever.config import Deps
from forever.store import VersionData


class DataSource(NamedTuple):
    label: str  # identifiant ou chemin tel que donné
    root: Path  # dossier qui contient manifest.json
    version: str
    candidate: bool


def resolve_source(deps: Deps, ref: str) -> DataSource:
    """Version du dépôt si `ref` est un identifiant présent dans `deps.data_dir`, sinon dossier candidat ;
    lève UnknownVersionError (code 4) si ni l'un ni l'autre."""
    raise NotImplementedError


def load_source(deps: Deps, ref: str) -> tuple[DataSource, VersionData]:
    """Source résolue et chargée après contrôle d'intégrité de son manifeste (DataIntegrityError sinon)."""
    raise NotImplementedError
