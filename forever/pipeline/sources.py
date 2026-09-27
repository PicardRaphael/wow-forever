"""Désignation d'une version de données : identifiant d'une version du dépôt ou chemin d'une version candidate.

Une version candidate est un dossier de données complet (`manifest.json` + un seul dossier de version), produit par
`forever decode` hors de `forever/data/`."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple, cast

from forever.config import Deps
from forever.errors import UnknownVersionError
from forever.manifest import MANIFEST_NAME, VERSION_DIR_RE, data_sha, version_dirs, version_files
from forever.provenance import Certainty, Provenance, local_provenance, make_provenance, min_certainty
from forever.store import VersionData, ensure_integrity, read_sources

CERTAINTIES = ("certain", "probable", "suppose")


class DataSource(NamedTuple):
    label: str  # identifiant ou chemin tel que donné
    root: Path  # dossier qui contient manifest.json
    version: str
    candidate: bool


def resolve_source(deps: Deps, ref: str) -> DataSource:
    """Version du dépôt si `ref` est un identifiant présent dans `deps.data_dir`, sinon dossier candidat ;
    lève UnknownVersionError (code 4) si ni l'un ni l'autre."""
    if VERSION_DIR_RE.fullmatch(ref) and (deps.data_dir / ref).is_dir():
        return DataSource(ref, deps.data_dir, ref, False)
    path = Path(ref)
    if not VERSION_DIR_RE.fullmatch(ref) and path.is_dir() and (path / MANIFEST_NAME).is_file():
        versions = version_dirs(path)
        if len(versions) == 1:
            return DataSource(ref, path, versions[0], True)
    raise UnknownVersionError(ref, version_dirs(deps.data_dir))


def load_source(deps: Deps, ref: str) -> tuple[DataSource, VersionData]:
    """Source résolue et chargée après contrôle d'intégrité de son manifeste (DataIntegrityError sinon)."""
    src = resolve_source(deps, ref)
    ensure_integrity(src.root)
    vdir = src.root / src.version
    return src, VersionData(src.version, data_sha(version_files(vdir)), vdir, read_sources(src.root, src.version) or {})


def inherited_files(v: VersionData) -> list[str]:
    """Fichiers repris tels quels d'une version antérieure (`inherited_from` dans leur entrée de `sources.json`)."""
    files = v.sources.get("files", {})
    if not isinstance(files, dict):
        return []
    return sorted(n for n, e in files.items() if isinstance(e, dict) and e.get("inherited_from"))


def source_certainty(v: VersionData) -> Certainty:
    """Certitude la plus basse annoncée par `sources.json` (suppose si aucune n'est lisible)."""
    files = v.sources.get("files", {})
    values = [f.get("certainty") for f in files.values() if isinstance(f, dict)] if isinstance(files, dict) else []
    valid = [cast(Certainty, c) for c in values if c in CERTAINTIES]
    return min_certainty(valid) if valid else "suppose"


def source_notes(src: DataSource, v: VersionData) -> list[str]:
    notes = []
    if src.candidate:
        notes.append(f"{src.version} : version candidate non installée ({src.root})")
    inherited = inherited_files(v)
    if inherited:
        notes.append(f"{src.version} : fichiers hérités d'une version antérieure ({', '.join(inherited)})")
    return notes


def source_provenance(deps: Deps, src: DataSource, v: VersionData, extra: Iterable[str] = ()) -> Provenance:
    """Provenance d'un résultat qui porte sur la version `v` (fraîcheur : celle des données locales)."""
    local = local_provenance(deps)
    return make_provenance(
        deps,
        game_version=v.game_version,
        data_sha=v.data_sha,
        freshness=local["freshness"],
        certainty=source_certainty(v),
        assumptions=[*local["assumptions"], *source_notes(src, v), *extra],
    )
