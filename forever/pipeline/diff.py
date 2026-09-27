"""Comparaison de deux versions de données (dépôt ou candidate) : talents, sorts, fichiers.

Champs comparés : talents `name`, `tree`, `tier`, `col`, `max`, `prereq`, puis chaque rang (`ranks[i]`, à partir
de 1) ; sorts, chaque champ de `rank_format` de chaque rang (`ranks[i].mana`), un rang en plus ou en moins
(`ranks[i]`). Ne sont pas comparés : descriptions, identifiants de sorts, noms français, certitudes, notes."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

from forever.config import Deps
from forever.errors import DataSchemaError
from forever.pipeline.sources import load_source, source_provenance
from forever.provenance import Provenance
from forever.store import VersionData

TALENT_FIELDS = ("name", "tree", "tier", "col", "max", "prereq")
KINDS = ("talent", "spell", "file")

Kind = Literal["talent", "spell", "file"]
ChangeType = Literal["added", "removed", "modified"]


class Change(TypedDict):
    kind: Kind
    key: str
    change: ChangeType
    field: str | None
    old: object
    new: object


class VersionDiff(TypedDict):
    a: str
    b: str
    changes: list[Change]
    counts: dict[str, int]
    provenance: Provenance


def _change(kind: Kind, key: str, change: ChangeType, field: str | None, old: object, new: object) -> Change:
    return {"kind": kind, "key": key, "change": change, "field": field, "old": old, "new": new}


def _read(v: VersionData, name: str) -> Any:
    path = v.path / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"{path} illisible ({exc}).") from exc


def _keys(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    return [*a, *(k for k in b if k not in a)]


def _talents(doc: Any) -> dict[str, Any]:
    if not isinstance(doc, dict):
        return {}
    return {t["key"]: t for tree in doc.get("trees", []) for t in tree.get("talents", [])}


def _rows(kind: Kind, key: str, old: Sequence[Any], new: Sequence[Any], fields: Sequence[str] | None) -> list[Change]:
    """Rangs comparés un à un ; `fields` : noms des colonnes d'un rang de sort (None : rang comparé en bloc)."""
    out: list[Change] = []
    for i in range(max(len(old), len(new))):
        where = f"ranks[{i + 1}]"
        if i >= len(new):
            out.append(_change(kind, key, "removed", where, old[i], None))
        elif i >= len(old):
            out.append(_change(kind, key, "added", where, None, new[i]))
        elif fields is None:
            if old[i] != new[i]:
                out.append(_change(kind, key, "modified", where, old[i], new[i]))
        else:
            out += [
                _change(kind, key, "modified", f"{where}.{f}", x, y)
                for f, x, y in zip(fields, old[i], new[i], strict=False)
                if x != y or (x is None) != (y is None)
            ]
    return out


def compare_data(a: VersionData, b: VersionData) -> list[Change]:
    """Changements de `a` vers `b`, dans un ordre stable (fichiers, talents, sorts ; ordre des données)."""
    changes: list[Change] = []
    fa = {p.name for p in a.path.iterdir() if p.is_file()}
    fb = {p.name for p in b.path.iterdir() if p.is_file()}
    changes += [_change("file", n, "removed", None, None, None) for n in sorted(fa - fb)]
    changes += [_change("file", n, "added", None, None, None) for n in sorted(fb - fa)]

    ta, tb = _talents(_read(a, "talents.json")), _talents(_read(b, "talents.json"))
    for key in _keys(ta, tb):
        if key not in tb:
            changes.append(_change("talent", key, "removed", None, None, None))
        elif key not in ta:
            changes.append(_change("talent", key, "added", None, None, None))
        else:
            old, new = ta[key], tb[key]
            changes += [
                _change("talent", key, "modified", f, old.get(f), new.get(f))
                for f in TALENT_FIELDS
                if old.get(f) != new.get(f)
            ]
            changes += _rows("talent", key, old.get("ranks", []), new.get("ranks", []), None)

    sa, sb = _read(a, "spells.json") or {}, _read(b, "spells.json") or {}
    fields = sb.get("rank_format") or sa.get("rank_format") or []
    spells_a, spells_b = sa.get("spells", {}), sb.get("spells", {})
    for key in _keys(spells_a, spells_b):
        if key not in spells_b:
            changes.append(_change("spell", key, "removed", None, None, None))
        elif key not in spells_a:
            changes.append(_change("spell", key, "added", None, None, None))
        else:
            changes += _rows("spell", key, spells_a[key].get("ranks", []), spells_b[key].get("ranks", []), fields)
    return changes


def diff_versions(deps: Deps, a: str, b: str) -> VersionDiff:
    """`a`, `b` : identifiant de version du dépôt ou chemin d'une candidate ; intégrité exigée des deux côtés."""
    src_a, va = load_source(deps, a)
    src_b, vb = load_source(deps, b)
    changes = compare_data(va, vb)
    counts = {k: sum(1 for c in changes if c["kind"] == k) for k in KINDS}
    extra = [f"comparaison {a} (données {va.data_sha}) -> {b} (données {vb.data_sha})"]
    if src_a.candidate:
        extra.append(f"{a} : version candidate non installée")
    return {
        "a": a,
        "b": b,
        "changes": changes,
        "counts": counts,
        "provenance": source_provenance(deps, src_b, vb, extra),
    }
