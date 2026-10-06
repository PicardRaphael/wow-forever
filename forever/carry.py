"""Report des changements faits à la main d'une version à la suivante (T08d, bloc C, décision 180, clause b).

Une version contient des valeurs qui ne viennent pas du décodage : règles d'origine `manuel` et `journal`
(`origins.json`), changements écrits à la main dans une révision (`manual_changes` de `revisions.json`), état du jeu
relevé en jeu (`meta.json` `game_state`). Avant toute installation automatique, chacune est classée :

- `gardé` : même valeur au même chemin dans la nouvelle version (métadonnées exclues) ;
- `réappliqué` : absente d'un fichier **hérité** de la nouvelle version, réécrite par `carry_apply` ;
- `remplacé` : une autre valeur au même chemin (fichier désormais décodé : le client donne une autre valeur ;
  fichier hérité : changement de la nouvelle version) ; elle l'emporte après accord ;
- `perdu` : absente sans explication (jamais approuvable).

Lecture et écriture locales seulement ; aucun chiffre de jeu ici."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

from forever.engine_inputs import PROVENANCE_FILES, metadata_keys
from forever.origins import format_pointer, parse_pointer

ORIGINS = ("manuel", "journal")
_MISSING = object()


class ManualValue(NamedTuple):
    file: str
    pointer: str
    value: Any
    origin: str  # manuel | journal
    revision: int | None
    reason: str


class CarryReport(NamedTuple):
    kept: list[ManualValue]
    reapplied: list[ManualValue]
    superseded: list[tuple[ManualValue, Any]]
    lost: list[ManualValue]


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _MISSING


def _get(doc: Any, segments: tuple[str, ...]) -> Any:
    node = doc
    for s in segments:
        if isinstance(node, dict) and s in node:
            node = node[s]
        elif isinstance(node, list) and s.isdigit() and int(s) < len(node):
            node = node[int(s)]
        else:
            return _MISSING
    return node


def _dotted(doc: Any, path: str) -> tuple[str, ...] | None:
    """Chemin pointé d'un `manual_changes` (« coefficient.low_level_default.certainty ») -> segments : à chaque
    niveau, la plus longue suite de parties qui forme une clé ; essayé à la racine, puis sous `values`."""

    def walk(node: Any, parts: list[str]) -> tuple[str, ...] | None:
        if not parts:
            return ()
        if not isinstance(node, dict):
            return None
        for n in range(len(parts), 0, -1):
            key = ".".join(parts[:n])
            if key in node:
                rest = walk(node[key], parts[n:])
                if rest is not None:
                    return (key, *rest)
        return None

    if path.startswith("/"):
        segments = parse_pointer(path)
        return segments if _get(doc, segments) is not _MISSING else None
    parts = path.split(".")
    found = walk(doc, parts)
    if found is None and isinstance(doc, dict) and isinstance(doc.get("values"), dict):
        inner = walk(doc["values"], parts)
        found = ("values", *inner) if inner is not None else None
    return found


def manual_values(version_dir: Path) -> list[ManualValue]:
    """Valeurs `manuel` et `journal`, chemins des `manual_changes` et `meta.json` `game_state` d'une version."""
    out: dict[tuple[str, str], ManualValue] = {}
    docs: dict[str, Any] = {}

    def doc_of(file: str) -> Any:
        if file not in docs:
            docs[file] = _load(version_dir / file)
        return docs[file]

    def add(file: str, segments: tuple[str, ...], origin: str, revision: int | None, reason: str) -> None:
        if file in PROVENANCE_FILES:
            return
        value = _get(doc_of(file), segments)
        if value is _MISSING:
            return
        key = (file, format_pointer(segments))
        if key in out:
            if out[key].revision is None and revision is not None:
                out[key] = out[key]._replace(revision=revision)
            return
        out[key] = ManualValue(file, key[1], value, origin, revision, reason)

    origins = _load(version_dir / "origins.json")
    for rule in origins.get("rules", []) if isinstance(origins, dict) else []:
        if rule.get("origin") not in ORIGINS:
            continue
        for path in rule.get("paths", []):
            reason = str(rule.get("reason") or rule.get("source") or "")
            add(str(rule["file"]), parse_pointer(path), str(rule["origin"]), None, reason)
    revisions = _load(version_dir / "revisions.json")
    for rev in revisions.get("revisions", []) if isinstance(revisions, dict) else []:
        for change in rev.get("manual_changes") or []:
            file = str(change.get("file", ""))
            if not file or file in PROVENANCE_FILES:
                continue
            segments = _dotted(doc_of(file), str(change.get("path", "")))
            if segments is not None:
                add(file, segments, "manuel", rev.get("revision"), str(change.get("source") or ""))
    add("meta.json", ("game_state",), "journal", None, "état du jeu relevé en jeu (installation)")
    return list(out.values())


def _strip(doc: Any, metadata: frozenset[str]) -> Any:
    if isinstance(doc, dict):
        return {k: _strip(v, metadata) for k, v in doc.items() if k not in metadata}
    if isinstance(doc, list):
        return [_strip(v, metadata) for v in doc]
    return doc


def carry_check(old_dir: Path, new_dir: Path) -> CarryReport:
    """Classe chaque valeur faite à la main de `old_dir` face à `new_dir`."""
    metadata = metadata_keys(old_dir, new_dir)
    sources = _load(new_dir / "sources.json")
    files = sources.get("files", {}) if isinstance(sources, dict) else {}
    report = CarryReport([], [], [], [])
    docs: dict[str, Any] = {}
    for value in manual_values(old_dir):
        if value.file not in docs:
            docs[value.file] = _load(new_dir / value.file)
        doc = docs[value.file]
        if doc is _MISSING:
            report.lost.append(value)
            continue
        now = _get(doc, parse_pointer(value.pointer))
        if now is not _MISSING and _strip(now, metadata) == _strip(value.value, metadata):
            report.kept.append(value)
        elif now is _MISSING and "inherited_from" in (files.get(value.file) or {}):
            report.reapplied.append(value)  # absente d'un fichier hérité : la valeur faite à la main est réécrite
        elif now is _MISSING:
            report.lost.append(value)
        else:
            # autre valeur : le client (fichier décodé) ou un changement de la nouvelle version (fichier hérité)
            # l'emporte, jamais sans accord ; une valeur présente n'est jamais écrasée par l'ancienne
            report.superseded.append((value, now))
    return report


def _set(doc: Any, segments: tuple[str, ...], value: Any, model: Any) -> None:
    """Écrit `value` au chemin, en créant les objets manquants ; l'ordre des clés suit celui de `model`."""
    node, ref = doc, model
    for s in segments[:-1]:
        if not isinstance(node.get(s), dict):
            node[s] = {}
        node, ref = node[s], ref.get(s) if isinstance(ref, dict) else None
    node[segments[-1]] = value
    if isinstance(ref, dict):
        order = [k for k in ref if k in node] + [k for k in node if k not in ref]
        items = [(k, node[k]) for k in order]
        node.clear()
        node.update(items)


def carry_apply(old_dir: Path, new_dir: Path, report: CarryReport) -> list[Path]:
    """Réécrit les valeurs `réappliqué` dans `new_dir` (en octets), puis le manifeste de son dossier de données."""
    from forever.manifest import write_manifest

    by_file: dict[str, list[ManualValue]] = {}
    for value in report.reapplied:
        by_file.setdefault(value.file, []).append(value)
    written: list[Path] = []
    for file, values in sorted(by_file.items()):
        doc = _load(new_dir / file)
        model = _load(old_dir / file)
        if not isinstance(doc, dict):
            continue
        for value in values:
            _set(doc, parse_pointer(value.pointer), value.value, model)
        path = new_dir / file
        path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        written.append(path)
    if written:
        write_manifest(new_dir.parent)
    return written
