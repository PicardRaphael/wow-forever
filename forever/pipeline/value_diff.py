"""Comparaison des valeurs des fichiers décodés (`spell_scaling.json`, `character_scaling.json`) : T08b, bloc C.

Une ligne par valeur changée, nommée pour la lecture : sort et rang (`frostbolt r1`), composant (`composant 0
bonus_coefficient`), classe et niveau (`Mage niveau 10`, `base_mana`). Les métadonnées (source, notes, build,
recoupement) ne sont pas comparées."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

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
