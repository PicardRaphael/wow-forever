"""Empreintes sha256 des données versionnées (`forever/data/manifest.json`).

Le manifeste est déterministe (aucun horodatage) : deux générations sur les mêmes octets donnent le même fichier.
Il n'est jamais écrit à la main : `uv run forever manifest --update`."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.pipeline.builds import version_key

MANIFEST_NAME = "manifest.json"
SOURCES_NAME = "sources.json"
SCHEMA_VERSION = 1
VERSION_DIR_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """Manifeste présent mais illisible, mal formé ou incohérent."""


@dataclass
class IntegrityReport:
    """Résultat de la vérification : chemins relatifs à `data_dir`, séparateur `/`.

    `manifest_error` : manifeste présent mais inutilisable (aucune comparaison de fichiers n'est faite)."""

    manifest_found: bool
    manifest_error: str | None = None
    mismatched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.manifest_found
            and self.manifest_error is None
            and not (self.mismatched or self.missing or self.unexpected)
        )


def version_dirs(data_dir: Path) -> list[str]:
    """Dossiers de version présents, triés par version croissante."""
    if not data_dir.is_dir():
        return []
    names = [p.name for p in data_dir.iterdir() if p.is_dir() and VERSION_DIR_RE.match(p.name)]
    return sorted(names, key=version_key)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version_files(version_dir: Path) -> dict[str, str]:
    """Nom de fichier -> sha256, pour un dossier de version."""
    return {p.name: file_sha256(p) for p in sorted(version_dir.iterdir()) if p.is_file()}


def data_sha256(files: Mapping[str, str]) -> str:
    lines = "".join(f"{name} {sha}\n" for name, sha in sorted(files.items()))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def data_sha(files: Mapping[str, str]) -> str:
    """Empreinte courte (12 hex) d'un ensemble de fichiers."""
    return data_sha256(files)[:12]


def _read_sources(version_dir: Path) -> dict[str, Any]:
    path = version_dir / SOURCES_NAME
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def compute_manifest(data_dir: Path) -> dict[str, Any]:
    versions: dict[str, Any] = {}
    for name in version_dirs(data_dir):
        vdir = data_dir / name
        files = version_files(vdir)
        sources = _read_sources(vdir)
        versions[name] = {
            "product": sources.get("product"),
            "version_prefix": sources.get("version_prefix"),
            "collected_at": sources.get("collected_at"),
            "hotfixes": [],
            "data_sha": data_sha(files),
            "data_sha256": data_sha256(files),
            "files": files,
        }
        if "revision" in sources:  # T06b : révision de la version (forever install)
            versions[name]["revision"] = sources["revision"]
            versions[name]["revised_at"] = sources.get("revised_at")
    names = list(versions)
    return {"schema_version": SCHEMA_VERSION, "game_version": names[-1] if names else None, "versions": versions}


def render_manifest(manifest: Mapping[str, Any]) -> bytes:
    """JSON trié, indentation 2, LF, UTF-8, saut de ligne final."""
    return (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_manifest(data_dir: Path) -> Path:
    path = data_dir / MANIFEST_NAME
    path.write_bytes(render_manifest(compute_manifest(data_dir)))
    return path


def _check_manifest(data: object) -> dict[str, Any]:
    """Contrôle la structure et la cohérence interne du manifeste ; lève ManifestError au premier écart."""
    if not isinstance(data, dict):
        raise ManifestError("le contenu n'est pas un objet JSON")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"schema_version {data.get('schema_version')!r} non pris en charge")
    versions = data.get("versions")
    if not isinstance(versions, dict):
        raise ManifestError("« versions » n'est pas un objet")
    for version, entry in versions.items():
        if not VERSION_DIR_RE.fullmatch(version):
            raise ManifestError(f"version invalide : {version!r}")
        if not isinstance(entry, dict):
            raise ManifestError(f"{version} : l'entrée n'est pas un objet")
        files = entry.get("files")
        if not isinstance(files, dict) or not all(
            isinstance(s, str) and SHA256_RE.fullmatch(s) for s in files.values()
        ):
            raise ManifestError(f"{version} : « files » doit associer chaque fichier à un sha256")
        if entry.get("data_sha256") != data_sha256(files) or entry.get("data_sha") != data_sha(files):
            raise ManifestError(f"{version} : empreinte globale incohérente avec « files »")
    game_version = data.get("game_version")
    if (game_version is None and versions) or (game_version is not None and game_version not in versions):
        raise ManifestError(f"game_version {game_version!r} absente de « versions »")
    return data


def load_manifest(data_dir: Path) -> dict[str, Any] | None:
    """Manifeste validé ; None s'il est absent ; lève ManifestError s'il est illisible, mal formé ou incohérent."""
    path = data_dir / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise ManifestError(f"lecture impossible ({exc.strerror or exc})") from exc
    except UnicodeDecodeError as exc:
        raise ManifestError("encodage invalide (UTF-8 attendu)") from exc
    except ValueError as exc:
        raise ManifestError("JSON invalide") from exc
    return _check_manifest(data)


def verify(data_dir: Path) -> IntegrityReport:
    try:
        manifest = load_manifest(data_dir)
    except ManifestError as exc:
        return IntegrityReport(manifest_found=True, manifest_error=str(exc))
    if manifest is None:
        return IntegrityReport(manifest_found=False)
    report = IntegrityReport(manifest_found=True)
    expected: dict[str, dict[str, str]] = {
        version: dict(entry["files"]) for version, entry in manifest["versions"].items()
    }
    for version in sorted(set(expected) | set(version_dirs(data_dir)), key=version_key):
        vdir = data_dir / version
        actual = version_files(vdir) if vdir.is_dir() else {}
        wanted = expected.get(version, {})
        for name in sorted(set(wanted) | set(actual)):
            rel = f"{version}/{name}"
            if name not in actual:
                report.missing.append(rel)
            elif name not in wanted:
                report.unexpected.append(rel)
            elif actual[name] != wanted[name]:
                report.mismatched.append(rel)
    return report
