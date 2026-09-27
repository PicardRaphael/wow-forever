"""Chargement d'une version de données, après vérification des empreintes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import DataIntegrityError, ManifestMissingError
from forever.manifest import SOURCES_NAME, data_sha, load_manifest, verify, version_dirs, version_files


@dataclass(frozen=True)
class VersionData:
    game_version: str
    data_sha: str
    path: Path
    sources: dict[str, Any]

    def read_json(self, name: str) -> Any:
        return json.loads((self.path / name).read_text(encoding="utf-8"))


def read_sources(data_dir: Path, version: str) -> dict[str, Any] | None:
    """`sources.json` d'une version, sans contrôle d'intégrité (None s'il est absent ou illisible)."""
    try:
        data = json.loads((data_dir / version / SOURCES_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def current_identity(data_dir: Path) -> tuple[str, str]:
    """(version, empreinte courte) sans contrôle : d'après le manifeste s'il existe, sinon d'après les fichiers."""
    manifest = load_manifest(data_dir)
    if manifest is not None:
        version = manifest.get("game_version")
        if isinstance(version, str):
            entry = manifest["versions"].get(version)
            if isinstance(entry, dict) and isinstance(entry.get("data_sha"), str):
                return version, str(entry["data_sha"])
    versions = version_dirs(data_dir)
    if not versions:
        return "0.0.0.0", "0" * 12
    return versions[-1], data_sha(version_files(data_dir / versions[-1]))


def load_version(deps: Deps) -> VersionData:
    """Version la plus récente ; lève DataIntegrityError ou ManifestMissingError si les empreintes sont invalides."""
    report = verify(deps.data_dir)
    if not report.manifest_found:
        raise ManifestMissingError(f"Manifeste des données absent ou illisible dans {deps.data_dir}.")
    if not report.ok:
        parts = [
            f"{label} : {', '.join(paths)}"
            for label, paths in (
                ("modifiés", report.mismatched),
                ("manquants", report.missing),
                ("inattendus", report.unexpected),
            )
            if paths
        ]
        raise DataIntegrityError("Empreintes des données invalides, réponse refusée (" + " ; ".join(parts) + ").")
    game_version, sha = current_identity(deps.data_dir)
    return VersionData(game_version, sha, deps.data_dir / game_version, read_sources(deps.data_dir, game_version) or {})
