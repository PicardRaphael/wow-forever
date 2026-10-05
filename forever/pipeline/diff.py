"""Comparaison de deux versions de données (dépôt ou candidate) : talents, sorts, fichiers.

Champs comparés : talents `name`, `tree`, `tier`, `col`, `max`, `prereq`, puis chaque rang (`ranks[i]`, à partir
de 1) ; sorts, chaque champ de `rank_format` de chaque rang (`ranks[i].mana`), un rang en plus ou en moins
(`ranks[i]`) ; `tooltip_values[i]` quand les deux versions l'ont. Ne sont pas comparés : descriptions, identifiants de sorts, noms français, certitudes, notes."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal, NotRequired, TypedDict, cast

from forever.config import Deps
from forever.errors import DataSchemaError
from forever.pipeline.sources import load_source, source_provenance
from forever.pipeline.value_diff import META, character_lines, scaling_lines
from forever.pipeline.value_diff import _pairs as value_pairs
from forever.provenance import Provenance
from forever.store import VersionData

TALENT_FIELDS = ("name", "tree", "tier", "col", "max", "prereq")
SCALING = "spell_scaling.json"
CHARACTER = "character_scaling.json"
CLASSES, PETS, PVP_ITEMS = "classes.json", "pets.json", "pvp_items.json"  # T08c, bloc D : valeurs comparées
KINDS = ("talent", "spell", "file", "scaling", "character", "class", "pet", "pvp_item")

Kind = Literal["talent", "spell", "file", "scaling", "character", "class", "pet", "pvp_item"]
ChangeType = Literal["added", "removed", "modified"]


class Change(TypedDict):
    kind: Kind
    key: str
    change: ChangeType
    field: str | None
    old: object
    new: object
    hotfix: NotRequired[dict[str, Any]]  # T08c : poussées et première date vue du correctif qui porte la valeur


class VersionDiff(TypedDict):
    a: str
    b: str
    changes: list[Change]
    counts: dict[str, int]
    provenance: Provenance


def _change(
    kind: Kind,
    key: str,
    change: ChangeType,
    field: str | None,
    old: object,
    new: object,
    hotfix: Mapping[str, Any] | None = None,
) -> Change:
    out: Change = {"kind": kind, "key": key, "change": change, "field": field, "old": old, "new": new}
    if hotfix is not None:
        out["hotfix"] = dict(hotfix)
    return out


def _attribution(entity: Any) -> dict[str, Any] | None:
    """Correctif du serveur porté par une entité (champ `hotfix` posé par forever decode --hotfixes)."""
    fix = entity.get("hotfix") if isinstance(entity, dict) else None
    if not isinstance(fix, dict):
        return None
    return {"pushes": list(fix.get("pushes", [])), "first_logged_at": fix.get("first_logged_at")}


def _deleted(sources: Any, table: str) -> dict[int, dict[str, Any]]:
    """Enregistrements retirés par un correctif (`sources.json`, bloc `hotfixes`) : une entité disparue n'a plus de
    champ `hotfix`, son attribution vient de là."""
    block = sources.get("hotfixes") if isinstance(sources, dict) else None
    if not isinstance(block, dict):
        return {}
    seen = block.get("seen_at", {})
    return {
        int(a["rec_id"]): {"pushes": [a["push"]], "first_logged_at": seen.get(str(a["push"]))}
        for a in block.get("applied", [])
        if a.get("table") == table and a.get("status") == "DELETE"
    }


def _entity_changes(
    kind: Kind, key: str, old: Any, new: Any, removed_fix: Mapping[str, Any] | None = None
) -> list[Change]:
    if new is None:
        return [_change(kind, key, "removed", None, None, None, removed_fix or _attribution(old))]
    if old is None:
        return [_change(kind, key, "added", None, None, None, _attribution(new))]
    fix = _attribution(new)
    return [_change(kind, key, cast(ChangeType, c), f, o, n, fix) for c, _, f, o, n in value_pairs(old, new)]


def _class_changes(a: Any, b: Any, deleted_nodes: Mapping[int, Mapping[str, Any]]) -> list[Change]:
    """`classes.json` : talents par nœud (« Warrior Fury Flurry »), sorts de classe, autres champs ; une ligne par
    valeur."""
    out: list[Change] = []
    ca, cb = (a or {}).get("classes", {}), (b or {}).get("classes", {})
    for cls in _keys(ca, cb):
        xa, xb = ca.get(cls, {}), cb.get(cls, {})
        ta = {t["node_id"]: (tree["name"], t) for tree in xa.get("trees", []) for t in tree.get("talents", [])}
        tb = {t["node_id"]: (tree["name"], t) for tree in xb.get("trees", []) for t in tree.get("talents", [])}
        for node in _keys(ta, tb):
            tree, talent = tb.get(node) or ta[node]
            old, new = ta.get(node, (None, None))[1], tb.get(node, (None, None))[1]
            out += _entity_changes("class", f"{cls} {tree} {talent['name']}", old, new, deleted_nodes.get(int(node)))
        sa, sb = xa.get("spells", {}), xb.get("spells", {})
        for key in _keys(sa, sb):
            name = (sb.get(key) or sa[key]).get("name", key)
            out += _entity_changes("class", f"{cls} sort {name}", sa.get(key), sb.get(key))
        for field in _keys(xa, xb):
            if field in ("trees", "spells") or field in META:
                continue
            out += [
                _change("class", f"{cls} {field}", cast(ChangeType, c), f, o, n)
                for c, _, f, o, n in value_pairs(xa.get(field), xb.get(field))
            ]
    return out


def _keyed_changes(kind: Kind, a: Any, b: Any, top: str, ident: str | None) -> list[Change]:
    """Fichier à entités nommées sous `top` (dictionnaire, ou liste repérée par `ident`) ; autres champs en vrac."""
    out: list[Change] = []
    a, b = a or {}, b or {}
    ea, eb = a.get(top, {}), b.get(top, {})
    if ident is not None:
        ea = {str(x.get(ident)): x for x in ea} if isinstance(ea, list) else {}
        eb = {str(x.get(ident)): x for x in eb} if isinstance(eb, list) else {}
    for key in _keys(ea, eb):
        entity = eb.get(key) or ea[key]
        name = entity.get("name") if isinstance(entity, dict) else None
        label = name.get("en") if isinstance(name, dict) else name
        out += _entity_changes(kind, f"{key} {label}" if label and ident else str(key), ea.get(key), eb.get(key))
    for field in _keys(a, b):
        if field == top or field in META:
            continue
        out += [
            _change(kind, field, cast(ChangeType, c), f, o, n)
            for c, _, f, o, n in value_pairs(a.get(field), b.get(field))
        ]
    return out


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


def _rows(
    kind: Kind, key: str, old: Sequence[Any], new: Sequence[Any], fields: Sequence[str] | None, name: str = "ranks"
) -> list[Change]:
    """Rangs comparés un à un ; `fields` : noms des colonnes d'un rang de sort (None : rang comparé en bloc)."""
    out: list[Change] = []
    for i in range(max(len(old), len(new))):
        where = f"{name}[{i + 1}]"
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
            changes.append(_change("talent", key, "added", None, None, None, _attribution(tb[key])))
        else:
            old, new = ta[key], tb[key]
            changes += [
                _change("talent", key, "modified", f, old.get(f), new.get(f), _attribution(new))
                for f in TALENT_FIELDS
                if old.get(f) != new.get(f)
            ]
            changes += _rows("talent", key, old.get("ranks", []), new.get("ranks", []), None)
            if "tooltip_values" in old and "tooltip_values" in new:  # champ du décodage (T03), absent de la référence
                changes += _rows("talent", key, old["tooltip_values"], new["tooltip_values"], None, "tooltip_values")

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
    # T08b, bloc C : valeurs des fichiers décodés, une ligne par valeur changée (plus de simple « fichier remplacé »)
    for kind, name, lines in (("scaling", SCALING, scaling_lines), ("character", CHARACTER, character_lines)):
        da, db = _read(a, name), _read(b, name)
        if isinstance(da, dict) and isinstance(db, dict):
            changes += [
                _change(cast(Kind, kind), key, cast(ChangeType, change), field, old, new)
                for change, key, field, old, new in lines(da, db)
            ]
    # T08c, bloc D : valeurs des fichiers des classes, des familiers et des bijoux PvP, attribuées aux correctifs
    deleted = _deleted(_read(b, "sources.json"), "TraitNode")
    if isinstance(_read(a, CLASSES), dict) and isinstance(_read(b, CLASSES), dict):
        changes += _class_changes(_read(a, CLASSES), _read(b, CLASSES), deleted)
    for kind, name, top, ident in (("pet", PETS, "abilities", None), ("pvp_item", PVP_ITEMS, "trinkets", "item_id")):
        da, db = _read(a, name), _read(b, name)
        if isinstance(da, dict) and isinstance(db, dict):
            changes += _keyed_changes(cast(Kind, kind), da, db, top, ident)
    return changes


def diff_versions(deps: Deps, a: str, b: str) -> VersionDiff:
    """`a`, `b` : identifiant de version du dépôt ou chemin d'une candidate ; intégrité exigée des deux côtés."""
    src_a, va = load_source(deps, a)
    src_b, vb = load_source(deps, b)
    changes = compare_data(va, vb)
    counts = {k: sum(1 for c in changes if c["kind"] == k) for k in KINDS}
    # valeurs des fichiers décodés (T08b) : comptées seulement quand il y en a (forme du résumé inchangée sinon)
    counts = {k: n for k, n in counts.items() if k in ("talent", "spell", "file") or n}
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
