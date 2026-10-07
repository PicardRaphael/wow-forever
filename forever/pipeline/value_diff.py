"""Comparaison des valeurs des fichiers décodés (`spell_scaling.json`, `character_scaling.json`) : T08b, bloc C.

Une ligne par valeur changée, nommée pour la lecture : sort et rang (`frostbolt r1`), composant (`composant 0
bonus_coefficient`), classe et niveau (`Mage niveau 10`, `base_mana`). Les métadonnées (source, notes, build,
recoupement) ne sont pas comparées."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any, NamedTuple

META = frozenset(
    {"source", "notes", "build", "schema_version", "inherited_from", "crosscheck", "certainty", "hotfix"}
)  # T08c : hotfix (provenance d'un correctif du serveur), pas une valeur
Line = tuple[str, str, str | None, Any, Any]  # (changement, clé, champ, avant, après)


def _leaves(doc: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k not in META:
                yield from _leaves(v, (*path, str(k)))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _leaves(v, (*path, str(i)))
    else:
        yield path, doc


def _pairs(a: Any, b: Any) -> Iterator[Line]:
    """Feuilles modifiées, ajoutées ou retirées entre deux sous-arbres (chemin relatif pointé)."""
    la = dict(_leaves(a)) if a is not None else {}
    lb = dict(_leaves(b)) if b is not None else {}
    for p in sorted(set(la) | set(lb), key=lambda s: [x.zfill(8) if x.isdigit() else x for x in s]):
        field = ".".join(p) or None
        if p not in lb:
            yield ("removed", "", field, la[p], None)
        elif p not in la:
            yield ("added", "", field, None, lb[p])
        elif la[p] != lb[p]:
            yield ("modified", "", field, la[p], lb[p])


def _by(items: Any, key: str) -> dict[Any, Any]:
    return {x.get(key): x for x in items} if isinstance(items, list) else {}


def scaling_lines(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[Line]:
    out: list[Line] = []
    for top in sorted(set(a) | set(b)):
        if top in META:
            continue
        va, vb = a.get(top), b.get(top)
        if top == "spells":
            sa, sb = va or {}, vb or {}
            for spell in sorted(set(sa) | set(sb)):
                ra, rb = _by(sa.get(spell, []), "rank"), _by(sb.get(spell, []), "rank")
                for rank in sorted(set(ra) | set(rb), key=lambda r: (r is None, r)):
                    key = f"{spell} r{rank}"
                    if rank not in rb:
                        out.append(("removed", key, None, None, None))
                        continue
                    if rank not in ra:
                        out.append(("added", key, None, None, None))
                        continue
                    xa = {k: v for k, v in ra[rank].items() if k != "components"}
                    xb = {k: v for k, v in rb[rank].items() if k != "components"}
                    out += [(c, key, f, o, n) for c, _, f, o, n in _pairs(xa, xb)]
                    ca, cb = _by(ra[rank].get("components", []), "index"), _by(rb[rank].get("components", []), "index")
                    for idx in sorted(set(ca) | set(cb), key=lambda i: (i is None, i)):
                        for c, _, f, o, n in _pairs(ca.get(idx, {}), cb.get(idx, {})):
                            out.append((c, key, f"composant {idx} {f}", o, n))
        elif isinstance(va, dict) or isinstance(vb, dict):
            da, db = va if isinstance(va, dict) else {}, vb if isinstance(vb, dict) else {}
            for name in sorted(set(da) | set(db)):
                out += [(c, f"{top} {name}", f, o, n) for c, _, f, o, n in _pairs(da.get(name), db.get(name))]
        else:
            out += [(c, top, f, o, n) for c, _, f, o, n in _pairs(va, vb)]
    return out


def character_lines(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[Line]:
    out: list[Line] = []
    ca, cb = a.get("classes", {}) or {}, b.get("classes", {}) or {}
    for cls in sorted(set(ca) | set(cb)):
        xa, xb = ca.get(cls, {}), cb.get(cls, {})
        for field in sorted(set(xa) | set(xb)):
            va, vb = xa.get(field), xb.get(field)
            if isinstance(va, list) or isinstance(vb, list):
                la, lb = va or [], vb or []
                for i in range(max(len(la), len(lb))):
                    o = la[i] if i < len(la) else None
                    n = lb[i] if i < len(lb) else None
                    if o != n:
                        change = "added" if o is None else "removed" if n is None else "modified"
                        out.append((change, f"{cls} niveau {i + 1}", field, o, n))
            else:
                out += [(c, f"{cls} {field}", f, o, n) for c, _, f, o, n in _pairs(va, vb)]
    for field in ("xp_to_next", "armor_constant"):
        la, lb = a.get(field) or [], b.get(field) or []
        for i in range(max(len(la), len(lb))):
            o = la[i] if i < len(la) else None
            n = lb[i] if i < len(lb) else None
            if o != n:
                out.append(
                    ("added" if o is None else "removed" if n is None else "modified", f"niveau {i + 1}", field, o, n)
                )
    for top in sorted((set(a) | set(b)) - {"classes", "xp_to_next", "armor_constant"} - META):
        out += [(c, top, f, o, n) for c, _, f, o, n in _pairs(a.get(top), b.get(top))]
    return out


# --- Fiches recopiées du client (T08e, décision 207) ---------------------------------------------------------------


class CopiedLine(NamedTuple):
    """Valeur changée d'une fiche recopiée : classe (ou fichier), entité nommée, champ, avant, après."""

    cls: str
    entity: str
    field: str
    before: Any
    after: Any


STABLE_KEYS = ("key", "spell_id", "node_id", "id")  # alignement des éléments de liste, avant l'indice
ENGINE_LABELS = {"pvp_dr": "fiches PvP"}
SUMMARY_KEYS = (
    "talents_added",
    "talents_removed",
    "talents_modified",
    "spells_added",
    "spells_removed",
    "spells_modified",
    "other",
)
ADDED, REMOVED = "ajouté", "retiré"
Segment = tuple[str, str]  # (« clé », nom), (« indice », i) ou (« id », valeur de la clé stable)


class _Missing:
    def __repr__(self) -> str:
        return "absent"


_MISSING: Any = _Missing()


def _stable_key(items: Sequence[Any]) -> str | None:
    """Clé stable commune aux éléments d'une liste (unique, jamais nulle), sinon None (alignement par indice)."""
    if not items or not all(isinstance(x, dict) for x in items):
        return None
    for name in STABLE_KEYS:
        values = [x.get(name) for x in items]
        if all(v is not None for v in values) and len({str(v) for v in values}) == len(values):
            return name
    return None


def _diff(a: Any, b: Any, path: tuple[Segment, ...]) -> Iterator[tuple[tuple[Segment, ...], Any, Any]]:
    """Feuilles changées entre deux sous-arbres, éléments de liste alignés par clé stable."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in [*a, *(k for k in b if k not in a)]:
            if k not in META:
                yield from _diff(a.get(k, _MISSING), b.get(k, _MISSING), (*path, ("clé", str(k))))
        return
    if isinstance(a, list) and isinstance(b, list):
        key = _stable_key([*a, *b])
        if key is not None and (not a or _stable_key(a) == key) and (not b or _stable_key(b) == key):
            ia, ib = {str(x[key]): x for x in a}, {str(x[key]): x for x in b}
            for k in [*ia, *(k for k in ib if k not in ia)]:
                yield from _diff(ia.get(k, _MISSING), ib.get(k, _MISSING), (*path, ("id", k)))
            return
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else _MISSING
            y = b[i] if i < len(b) else _MISSING
            yield from _diff(x, y, (*path, ("indice", str(i))))
        return
    if a is _MISSING or b is _MISSING or a != b:
        yield path, a, b


def _field(path: Sequence[Segment]) -> str:
    """« rang 1 level », « prereq tier », « prereqs 105927 », « n°2 counts 256 »."""
    out: list[str] = []
    for i, (kind, seg) in enumerate(path):
        if kind == "clé" and seg == "ranks" and i + 1 < len(path) and path[i + 1][0] == "indice":
            continue
        if kind == "indice":
            ranks = i > 0 and path[i - 1] == ("clé", "ranks")
            out.append(f"rang {int(seg) + 1}" if ranks else f"n°{int(seg) + 1}")
        else:
            out.append(seg)
    return " ".join(out)


def _value(x: Any) -> Any:
    return None if x is _MISSING else x


def _name(entity: Any, fallback: str) -> str:
    name = entity.get("name") if isinstance(entity, dict) else None
    name = name.get("en") if isinstance(name, dict) else name
    return name if isinstance(name, str) and name else fallback


def _entity_lines(cls: str, entity: str, kind: str, a: Any, b: Any) -> list[CopiedLine]:
    if b is _MISSING:
        return [CopiedLine(cls, entity, kind, "présent", REMOVED)]
    if a is _MISSING:
        return [CopiedLine(cls, entity, kind, "absent", ADDED)]
    return [CopiedLine(cls, entity, _field(p), _value(x), _value(y)) for p, x, y in _diff(a, b, ())]


def _talents(doc: Mapping[str, Any]) -> dict[tuple[str, str], Any]:
    found: dict[tuple[str, str], Any] = {}
    for tree in doc.get("trees") or []:
        if not isinstance(tree, dict):
            continue
        for talent in tree.get("talents") or []:
            if isinstance(talent, dict):
                found[(str(tree.get("name")), str(talent.get("key")))] = talent
    return found


def _class_lines(cls: str, a: Any, b: Any) -> list[CopiedLine]:
    a = a if isinstance(a, dict) else {}
    b = b if isinstance(b, dict) else {}
    out: list[CopiedLine] = []
    ta, tb = _talents(a), _talents(b)
    for k in [*ta, *(k for k in tb if k not in ta)]:
        x, y = ta.get(k, _MISSING), tb.get(k, _MISSING)
        entity = f"talent {k[0]} {_name(y if y is not _MISSING else x, k[1])}"
        out += _entity_lines(cls, entity, "talent", x, y)
    trees_a, trees_b = a.get("trees") or [], b.get("trees") or []
    for i in range(max(len(trees_a), len(trees_b))):
        x = {k: v for k, v in (trees_a[i] if i < len(trees_a) else {}).items() if k != "talents"}
        y = {k: v for k, v in (trees_b[i] if i < len(trees_b) else {}).items() if k != "talents"}
        entity = f"arbre {_name(y, '') or _name(x, str(i + 1))}"
        out += [CopiedLine(cls, entity, _field(p), _value(u), _value(v)) for p, u, v in _diff(x, y, ())]
    sa, sb = a.get("spells") or {}, b.get("spells") or {}
    for k in [*sa, *(k for k in sb if k not in sa)]:
        x, y = sa.get(k, _MISSING), sb.get(k, _MISSING)
        out += _entity_lines(cls, f"sort {_name(y if y is not _MISSING else x, k)}", "sort", x, y)
    for top in [*a, *(k for k in b if k not in a)]:
        if top in ("trees", "spells") or top in META:
            continue
        diffs = _diff(a.get(top, _MISSING), b.get(top, _MISSING), ())
        out += [CopiedLine(cls, top, _field(p) or top, _value(x), _value(y)) for p, x, y in diffs]
    return out


def copied_lines(file: str, before: Any, after: Any, pointer: str | None) -> list[CopiedLine]:
    """Lignes des valeurs changées d'une entrée (`file`, `pointer`) : pour une classe de `classes.json`, talents
    alignés par arbre et clé, sorts par clé, jamais par indice (une refonte décale les talents dans les listes) ;
    ailleurs, entité nommée par son premier segment. Éléments de liste alignés par clé stable (`STABLE_KEYS`)."""
    parts = [p for p in (pointer or "").split("/") if p]
    if file == "classes.json" and len(parts) == 2 and parts[0] == "classes":
        return _class_lines(parts[1], before, after)
    where = f"{file} {pointer}" if pointer else file
    a = before if before is not None else _MISSING
    b = after if after is not None else _MISSING
    out: list[CopiedLine] = []
    for path, x, y in _diff(a, b, ()):
        entity = path[0][1] if path else where
        out.append(CopiedLine(where, entity, _field(path[1:]) or entity, _value(x), _value(y)))
    return out


def copied_summary(lines: Sequence[CopiedLine]) -> dict[str, dict[str, int]]:
    """Comptes par classe : talents et sorts ajoutés, retirés, modifiés ; autres entités changées."""
    found: dict[str, dict[str, set[str]]] = {}
    for line in lines:
        row = found.setdefault(line.cls, {k: set() for k in SUMMARY_KEYS})
        for prefix, kind, group in (("talent ", "talent", "talents"), ("sort ", "sort", "spells")):
            if line.entity.startswith(prefix):
                state = "modified"
                if line.field == kind and line.after in (ADDED, REMOVED):
                    state = "added" if line.after == ADDED else "removed"
                row[f"{group}_{state}"].add(line.entity)
                break
        else:
            row["other"].add(line.entity)
    return {cls: {k: len(v) for k, v in row.items()} for cls, row in found.items()}


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def summary_sentence(summary: Mapping[str, Mapping[str, int]], engine: str) -> str:
    """Phrase courte du résumé (ligne de démarrage, `forever update status`) : « fiches PvP : Warrior, 9 talents
    ajoutés ou retirés, 18 talents et 4 sorts modifiés »."""
    parts = []
    for cls, row in summary.items():
        bits = []
        talents = row.get("talents_added", 0) + row.get("talents_removed", 0)
        spells = row.get("spells_added", 0) + row.get("spells_removed", 0)
        if talents:
            bits.append(_count(talents, "talent ajouté ou retiré", "talents ajoutés ou retirés"))
        if spells:
            bits.append(_count(spells, "sort ajouté ou retiré", "sorts ajoutés ou retirés"))
        mt, ms = row.get("talents_modified", 0), row.get("spells_modified", 0)
        if mt and ms:
            bits.append(f"{_count(mt, 'talent', 'talents')} et {_count(ms, 'sort', 'sorts')} modifiés")
        elif mt:
            bits.append(_count(mt, "talent modifié", "talents modifiés"))
        elif ms:
            bits.append(_count(ms, "sort modifié", "sorts modifiés"))
        if not bits and row.get("other"):
            bits.append(_count(row["other"], "autre valeur changée", "autres valeurs changées"))
        parts.append(", ".join([cls, *bits]))
    return f"{ENGINE_LABELS.get(engine, engine)} : {' ; '.join(parts)}"


VALUES_CAP = 50  # lignes gardées dans un JSON (attente, rapport de passage) ; tableau complet dans le rapport


def capped_lines(lines: Sequence[CopiedLine], limit: int = VALUES_CAP) -> dict[str, Any]:
    """`{"lines": [...], "more": N, "note": "et N autres"}` : les `limit` premières lignes et le reste compté."""
    more = max(0, len(lines) - limit)
    return {"lines": [list(line) for line in lines[:limit]], "more": more, "note": f"et {more} autres" if more else ""}
