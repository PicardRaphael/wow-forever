"""Empreintes sha256 des données versionnées (`forever/data/manifest.json`).

Le manifeste est déterministe (aucun horodatage) : deux générations sur les mêmes octets donnent le même fichier.
Il n'est jamais écrit à la main : `uv run forever manifest --update`."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"
SOURCES_NAME = "sources.json"
SCHEMA_VERSION = 1
VERSION_DIR_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


@dataclass
class IntegrityReport:
    """Résultat de la vérification : chemins relatifs à `data_dir`, séparateur `/`."""

    manifest_found: bool
    mismatched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.manifest_found and not (self.mismatched or self.missing or self.unexpected)


def version_dirs(data_dir: Path) -> list[str]:
    """Dossiers de version présents, triés par version croissante."""
    raise NotImplementedError


def file_sha256(path: Path) -> str:
    raise NotImplementedError


def version_files(version_dir: Path) -> dict[str, str]:
    """Nom de fichier -> sha256, pour un dossier de version."""
    raise NotImplementedError


def data_sha(files: Mapping[str, str]) -> str:
    """Empreinte courte (12 hex) d'un ensemble de fichiers."""
    raise NotImplementedError


def data_sha256(files: Mapping[str, str]) -> str:
    raise NotImplementedError


def compute_manifest(data_dir: Path) -> dict[str, Any]:
    raise NotImplementedError


def render_manifest(manifest: Mapping[str, Any]) -> bytes:
    """JSON trié, indentation 2, LF, UTF-8, saut de ligne final."""
    raise NotImplementedError


def write_manifest(data_dir: Path) -> Path:
    raise NotImplementedError


def load_manifest(data_dir: Path) -> dict[str, Any] | None:
    raise NotImplementedError


def verify(data_dir: Path) -> IntegrityReport:
    raise NotImplementedError
