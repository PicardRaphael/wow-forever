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
    names = list(versions)
    return {"schema_version": SCHEMA_VERSION, "game_version": names[-1] if names else None, "versions": versions}


def render_manifest(manifest: Mapping[str, Any]) -> bytes:
    """JSON trié, indentation 2, LF, UTF-8, saut de ligne final."""
    return (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_manifest(data_dir: Path) -> Path:
    path = data_dir / MANIFEST_NAME
    path.write_bytes(render_manifest(compute_manifest(data_dir)))
    return path


def load_manifest(data_dir: Path) -> dict[str, Any] | None:
    path = data_dir / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("versions"), dict) else None


def verify(data_dir: Path) -> IntegrityReport:
    manifest = load_manifest(data_dir)
    if manifest is None:
        return IntegrityReport(manifest_found=False)
    report = IntegrityReport(manifest_found=True)
    expected: dict[str, dict[str, str]] = {
        version: dict(entry.get("files", {})) for version, entry in manifest["versions"].items()
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
