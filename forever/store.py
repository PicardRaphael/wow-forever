"""Chargement d'une version de données, après vérification des empreintes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import DataIntegrityError, ManifestMissingError
from forever.manifest import (
    SOURCES_NAME,
    IntegrityReport,
    ManifestError,
    data_sha,
    load_manifest,
    verify,
    version_dirs,
    version_files,
)


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


@dataclass(frozen=True)
class DataIdentity:
    """Version courante, empreinte réelle de ses fichiers sur disque et empreinte annoncée par le manifeste."""

    game_version: str
    data_sha: str
    manifest_sha: str | None  # None : manifeste absent ou illisible, ou version absente du manifeste

    def notes(self) -> list[str]:
        """Hypothèse signalant l'écart entre les fichiers et le manifeste (liste vide si aucun écart connu)."""
        if self.manifest_sha is None or self.manifest_sha == self.data_sha:
            return []
        return [f"empreinte des fichiers sur disque {self.data_sha} ≠ manifeste {self.manifest_sha}"]


def current_identity(data_dir: Path) -> DataIdentity:
    """Version (celle du manifeste s'il est valide, sinon le dossier le plus récent) et empreinte réelle de ses
    fichiers, sans contrôle d'intégrité complet."""
    try:
        manifest = load_manifest(data_dir)
    except ManifestError:
        manifest = None
    version = manifest.get("game_version") if manifest is not None else None
    if not isinstance(version, str):
        versions = version_dirs(data_dir)
        if not versions:
            return DataIdentity("0.0.0.0", "0" * 12, None)
        version = versions[-1]
    vdir = data_dir / version
    actual = data_sha(version_files(vdir) if vdir.is_dir() else {})
    entry = manifest["versions"].get(version) if manifest is not None else None
    return DataIdentity(version, actual, entry["data_sha"] if entry is not None else None)


def describe_integrity(report: IntegrityReport) -> str:
    """Résumé en français des écarts d'empreintes (chaîne vide si aucun)."""
    return " ; ".join(
        f"{label} : {', '.join(paths)}"
        for label, paths in (
            ("modifiés", report.mismatched),
            ("manquants", report.missing),
            ("inattendus", report.unexpected),
        )
        if paths
    )


def ensure_integrity(data_dir: Path) -> IntegrityReport:
    """Lève ManifestMissingError ou DataIntegrityError si les données ne correspondent pas au manifeste."""
    report = verify(data_dir)
    if not report.manifest_found:
        raise ManifestMissingError(f"Manifeste des données absent dans {data_dir}.")
    if report.manifest_error is not None:
        raise DataIntegrityError(
            f"Manifeste des données illisible ({report.manifest_error}), réponse refusée.",
            "restaurer le manifeste depuis git ; si les données sont voulues, lancer `uv run forever manifest --update`",
        )
    if not report.ok:
        raise DataIntegrityError(f"Empreintes des données invalides, réponse refusée ({describe_integrity(report)}).")
    return report


def load_version(deps: Deps) -> VersionData:
    """Version la plus récente ; lève DataIntegrityError ou ManifestMissingError si les empreintes sont invalides."""
    ensure_integrity(deps.data_dir)
    identity = current_identity(deps.data_dir)
    version = identity.game_version
    return VersionData(version, identity.data_sha, deps.data_dir / version, read_sources(deps.data_dir, version) or {})
