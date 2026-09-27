"""Chargement d'une version de données, après vérification des empreintes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps


@dataclass(frozen=True)
class VersionData:
    game_version: str
    data_sha: str
    path: Path
    sources: dict[str, Any]

    def read_json(self, name: str) -> Any:
        raise NotImplementedError


def read_sources(data_dir: Path, version: str) -> dict[str, Any] | None:
    """`sources.json` d'une version, sans contrôle d'intégrité (None s'il est absent ou illisible)."""
    raise NotImplementedError


def current_identity(data_dir: Path) -> tuple[str, str]:
    """(version, empreinte courte) sans contrôle : d'après le manifeste s'il existe, sinon d'après les fichiers."""
    raise NotImplementedError


def load_version(deps: Deps) -> VersionData:
    """Version la plus récente ; lève DataIntegrityError ou ManifestMissingError si les empreintes sont invalides."""
    raise NotImplementedError
