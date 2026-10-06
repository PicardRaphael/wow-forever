"""Valeurs des correctifs du serveur appliquées aux tables du build en mode forever (T08c, bloc C).

Les entrées applicables de `DBCache.bin` (poussées réelles, `VALID` et `DELETE`, la plus haute poussée l'emportant)
sont décodées selon la disposition de WoWDBDefs du build, validée table par table contre le CSV du build
(`forever.pipeline.dbd.validate_layout`), puis superposées aux lignes lues par les décodeurs : une ligne `VALID`
remplace celle de même identifiant ou s'ajoute, une ligne `DELETE` est retirée (absente : listée). Une table sans
disposition validée n'est jamais appliquée ; si l'une de ses entrées vise une ligne lue par un décodeur, le décodage
est refusé. La valeur d'un correctif vaut pour le build du client qui l'a reçue : un `DBCache.bin` d'un autre build
est refusé. Origine des valeurs appliquées : `correctif_serveur` (`origins.json`), avec poussées et date vue par le
client (journal des correctifs). Aucun chiffre de jeu ici."""

from __future__ import annotations

import csv
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError, HotfixBuildMismatchError, HotfixLayoutError
from forever.pipeline.dbcache import (
    DBCache,
    Entry,
    Resolved,
    Status,
    effective,
    known_tables,
    read_dbcache,
    table_names,
)
from forever.pipeline.dbd import Layout, LayoutCheck, decode_record, layout_for, parse_dbd, validate_layout
from forever.pipeline.tables import TABLES, Row, Value

SERVER_ORIGIN = "correctif_serveur"
HOTFIX_KEY = "hotfix"
DEFAULT_LOCALE = "enUS"
EXTRA_TABLES = ("TraitNodeGroupXTraitNode",)  # corrigée par le serveur, jamais lue par le pipeline


class HotfixSource(NamedTuple):
    path: Path
    locale: str
    cache: DBCache
    resolved: Resolved
    names: dict[int, str]
    layouts: dict[str, Layout]
    dbd: dict[str, Any]  # repo, commit, empreintes des `.dbd`
    seen_at: dict[int, str | None]  # poussée -> première ligne du journal du même build (heure locale du client)
    read_at: str


class Applied(NamedTuple):
    table: str
    rec_id: int
    status: str  # VALID ou DELETE
    push_id: int
    unique_id: int
    seen_at: str | None
    before: Row | None
    after: Row | None

    @property
    def identical(self) -> bool:
        return self.before is not None and self.after is not None and dict(self.before) == dict(self.after)


class Overlay(NamedTuple):
    tables: dict[str, list[Row]]
    applied: list[Applied]
    listed: dict[str, Any]
    checks: dict[str, LayoutCheck]


def hotfix_source(
    path: Path,
    layouts: Mapping[str, Layout],
    dbd: Mapping[str, Any],
    journal: Sequence[Mapping[str, Any]],
    version: str,
    rules: Mapping[str, Any],
    read_at: str,
    *,
    locale: str = DEFAULT_LOCALE,
) -> HotfixSource:
    """Correctifs lus dans `path`, prêts à appliquer à `version` ; HotfixBuildMismatchError si le build de
    l'en-tête n'est pas celui de la version. `journal` : entrées de `hotfixes.json` (date vue par le client)."""
    cache = read_dbcache(path)
    if not version.endswith(f".{cache.build}"):
        raise HotfixBuildMismatchError(cache.build, version)
    names = table_names(known_tables(rules) | set(EXTRA_TABLES) | set(layouts))
    resolved = effective(cache.entries, names)
    pushes = {e.push_id for e in resolved.applicable.values()}
    seen: dict[int, str | None] = {}
    for push in sorted(pushes):
        times = [
            str(j["at"])
            for j in journal
            if str(j.get("push")) == str(push) and str(j.get("client_build") or "").endswith(f".{cache.build}")
        ]
        seen[push] = min(times) if times else None
    return HotfixSource(path, locale, cache, resolved, names, dict(layouts), dict(dbd), seen, read_at)


def load_dbd_layouts(cache_dir: Path, version: str, tables: Sequence[str]) -> tuple[dict[str, Layout], dict[str, Any]]:
    """Dispositions de `version` lues dans le relevé de `forever fetch --dbd` (cache) ; une table sans fichier ou sans
    bloc pour le build est absente du résultat (listée « sans disposition » à l'application)."""
    from forever.pipeline.fetch import dbd_dir, read_dbd_index

    index = read_dbd_index(cache_dir)
    if index is None:
        raise DataSchemaError(
            "Aucun relevé de WoWDBDefs dans le cache.", "relever les définitions : forever fetch --version V --dbd"
        )
    folder = dbd_dir(cache_dir) / str(index["commit"])
    layouts: dict[str, Layout] = {}
    for table in tables:
        path = folder / f"{table}.dbd"
        if path.is_file():
            layout = layout_for(parse_dbd(path.read_text(encoding="utf-8"), table), version)
            if layout is not None:
                layouts[table] = layout
    files = {t: str(v.get("sha256")) for t, v in index["files"].items() if t in layouts}
    return layouts, {"repo": index.get("repo"), "commit": index["commit"], "files": files}


# --- Application ---------------------------------------------------------------------------------------------


def _csv_file(csv_dir: Path, table: str) -> Path:
    return csv_dir / DEFAULT_LOCALE / f"{table}.csv"


def _csv_header_and_rows(path: Path, ids: set[int]) -> tuple[list[str] | None, dict[int, dict[str, str]]]:
    if not path.is_file():
        return None, {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = {int(r["ID"]): dict(r) for r in reader if r.get("ID", "").lstrip("-").isdigit() and int(r["ID"]) in ids}
        return list(reader.fieldnames or []), rows


def _csv_ids(path: Path, column: str = "ID") -> set[int]:
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {int(r[column]) for r in csv.DictReader(f) if str(r.get(column, "")).lstrip("-").isdigit()}


def _valid_ids(source: HotfixSource, *tables: str) -> set[int]:
    return {r for (t, r), e in source.resolved.applicable.items() if t in tables and e.status == Status.VALID}


def _known_ids(ref: str, tables: Mapping[str, Sequence[Row]], csv_dir: Path, source: HotfixSource) -> set[int] | None:
    """Identifiants connus d'une table référencée (`int<Table::ID>`) : lignes du build et correctifs ; None si la
    table n'est ni lue ni publiée (référence non contrôlée)."""
    if ref == "Spell":
        base = (
            {int(r["ID"]) for r in tables["SpellName"]}
            if "SpellName" in tables
            else _csv_ids(_csv_file(csv_dir, "SpellName"))
        )
        return base | _valid_ids(source, "SpellName", "Spell")
    if ref == "Curve":
        base = (
            {int(r["CurveID"]) for r in tables["CurvePoint"]}
            if "CurvePoint" in tables
            else _csv_ids(_csv_file(csv_dir, "CurvePoint"), "CurveID")
        )
        return base | _valid_ids(source, "Curve")
    if ref in tables:
        return {int(r["ID"]) for r in tables[ref]} | _valid_ids(source, ref)
    if _csv_file(csv_dir, ref).is_file():
        return _csv_ids(_csv_file(csv_dir, ref)) | _valid_ids(source, ref)
    return None


def _check(
    table: str, entries: Sequence[Entry], tables: Mapping[str, Sequence[Row]], csv_dir: Path, source: HotfixSource
) -> LayoutCheck:
    layout = source.layouts.get(table)
    if layout is None:
        return LayoutCheck(table, False, f"aucune disposition pour le build {source.cache.build}", 0, 0, None, None)
    header, rows = _csv_header_and_rows(_csv_file(csv_dir, table), {e.rec_id for e in entries})
    known: dict[str, set[int]] = {}
    for f in layout.fields:
        if f.ref is not None and f.ref not in known:
            ids = _known_ids(f.ref, tables, csv_dir, source)
            if ids is not None:
                known[f.ref] = ids
    return validate_layout(layout, entries, header, rows, known)


def _typed(table: str, schema: str, record: Mapping[str, Value], rec_id: int) -> dict[str, Value]:
    row: dict[str, Value] = {}
    for column in TABLES[schema]:
        name = next((n for n in column.names if n in record), None)  # nom de la disposition du build (T08d)
        if name is None:
            raise DataSchemaError(
                f"{table} {rec_id} : colonne {' ou '.join(column.names)} absente de l'enregistrement du correctif."
            )
        try:
            value = column.kind(record[name])
        except (TypeError, ValueError) as exc:
            raise DataSchemaError(f"{table} {rec_id} : valeur invalide pour {name} ({exc}).") from exc
        for alias in column.names:
            row[alias] = value
    return row


def _listed(source: HotfixSource) -> dict[str, Any]:
    res = source.resolved
    return {
        "invalid": [{"table": i.table, "rec_id": i.rec_id, "push": i.push_id} for i in res.invalid],
        "notpublic": [{"table": i.table, "rec_id": i.rec_id, "push": i.push_id} for i in res.notpublic],
        "dbreply": dict(sorted(res.dbreply.items())),
        "item_reply": dict(sorted(res.item_reply.items())),
        "unknown_hash": {f"{h:#010x}": n for h, n in sorted(res.unknown_hash.items())},
        "delete_absent": [],
        "unvalidated": {},
        "not_loaded": {},
    }


def apply_hotfixes(
    tables: Mapping[str, Sequence[Row]],
    source: HotfixSource,
    csv_dir: Path,
    *,
    schemas: Mapping[str, str] | None = None,
    strict: bool = True,
) -> Overlay:
    """Tables de la locale par défaut corrigées (les clés « frFR/… » sont rendues telles quelles), enregistrements
    appliqués (avant, après, poussée, date vue), listes à part et contrôle de chaque disposition. HotfixLayoutError
    si une table sans disposition validée a des entrées qui visent des lignes lues."""
    schemas = schemas or {}
    by_table: dict[str, list[Entry]] = {}
    for (table, _), entry in sorted(source.resolved.applicable.items()):
        by_table.setdefault(table, []).append(entry)
    out: dict[str, list[Row]] = {k: list(v) for k, v in tables.items()}
    listed = _listed(source)
    listed["not_loaded"] = {t: len(es) for t, es in sorted(by_table.items()) if t not in tables}
    applied: list[Applied] = []
    checks: dict[str, LayoutCheck] = {}
    refused: dict[str, str] = {}
    for table, entries in sorted(by_table.items()):
        if table not in tables:
            continue
        check = _check(table, entries, tables, csv_dir, source)
        checks[table] = check
        rows = out[table]
        index = {int(r["ID"]): i for i, r in enumerate(rows)}
        if not check.ok:
            hit = sorted(e.rec_id for e in entries if e.rec_id in index)
            if hit:
                refused[table] = f"{check.reason} ; enregistrement(s) lu(s) {hit[:5]}"
            else:
                listed["unvalidated"][table] = check.reason
            continue
        layout = source.layouts[table]
        schema = schemas.get(table, table)
        removed: set[int] = set()
        added: list[Row] = []
        for e in entries:
            seen = source.seen_at.get(e.push_id)
            before = rows[index[e.rec_id]] if e.rec_id in index else None
            if e.status == Status.DELETE:
                if before is None:
                    listed["delete_absent"].append({"table": table, "rec_id": e.rec_id, "push": e.push_id})
                    continue
                removed.add(e.rec_id)
                applied.append(Applied(table, e.rec_id, "DELETE", e.push_id, e.unique_id, seen, before, None))
                continue
            row = _typed(table, schema, decode_record(layout, e.data, e.rec_id), e.rec_id)
            if before is None:
                added.append(row)
            else:
                rows[index[e.rec_id]] = row
            applied.append(Applied(table, e.rec_id, "VALID", e.push_id, e.unique_id, seen, before, row))
        out[table] = [r for r in rows if int(r["ID"]) not in removed] + added
    if refused and strict:
        raise HotfixLayoutError(refused)
    listed["unvalidated"].update(refused)
    return Overlay(out, applied, listed, checks)


# --- Entités touchées et provenance ------------------------------------------------------------------------------


class Reach(NamedTuple):
    nodes: set[int]
    spells: set[int]
    items: set[int]


# Entités annotées (pointeurs à motifs) et champs qui portent leurs identifiants.
ENTITY_SPECS: dict[str, tuple[tuple[str, ...], ...]] = {
    "classes.json": (("classes", "*", "trees", "*", "talents", "*"), ("classes", "*", "spells", "*")),
    "talents.json": (("trees", "*", "talents", "*"),),
    "spells.json": (("spells", "*"),),
    "spell_scaling.json": (("spells", "*", "*"),),
    "pets.json": (("abilities", "*"),),
    "pvp_items.json": (("trinkets", "*"),),
    "races.json": (("races", "*", "racials", "*"),),
}


def _ints(value: Any) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, list):
        return {v for v in value if isinstance(v, int) and not isinstance(v, bool)}
    return set()


def entity_ids(entity: Mapping[str, Any]) -> Reach:
    """Nœud, sorts et objets propres à une entité (pas ceux de ses prérequis)."""
    spells = _ints(entity.get("spell_id")) | _ints(entity.get("spellIds")) | _ints(entity.get("teach_spell_id"))
    spells |= (
        _ints((entity.get("source") or {}).get("rank_spell_ids")) if isinstance(entity.get("source"), dict) else set()
    )
    for sub in ("ranks", "components"):
        for item in entity.get(sub) or []:
            if isinstance(item, dict):
                spells |= _ints(item.get("spell_id")) | _ints(item.get("teach_spell_id"))
    return Reach(_ints(entity.get("node_id")), spells, _ints(entity.get("item_id")))


def _walk(doc: Any, pattern: tuple[str, ...], path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    if not pattern:
        yield path, doc
        return
    head, rest = pattern[0], pattern[1:]
    if isinstance(doc, dict):
        keys = list(doc) if head == "*" else ([head] if head in doc else [])
        for k in keys:
            yield from _walk(doc[k], rest, (*path, str(k)))
    elif isinstance(doc, list) and head == "*":
        for i, v in enumerate(doc):
            yield from _walk(v, rest, (*path, str(i)))


def pointer(path: Sequence[str]) -> str:
    return "".join("/" + s.replace("~", "~0").replace("/", "~1") for s in path)


def reach(
    applied: Sequence[Applied], before: Mapping[str, Sequence[Row]], after: Mapping[str, Sequence[Row]]
) -> dict[tuple[str, int], Reach]:
    """Pour chaque enregistrement qui change une valeur : nœuds, sorts et objets qu'il atteint, par les tables du build
    et les tables corrigées (nœud -> entrées -> définitions -> sorts ; courbe -> points d'effet -> définition)."""

    def rows(table: str) -> list[Row]:
        return [*before.get(table, []), *after.get(table, [])]

    def col(table: str, key: str, value: int, out: str) -> set[int]:
        return {int(r[out]) for r in rows(table) if int(r[key]) == value}

    def spells_of_defs(defs: set[int]) -> set[int]:
        return {int(r["SpellID"]) for r in rows("TraitDefinition") if int(r["ID"]) in defs}

    def nodes_of_defs(defs: set[int]) -> set[int]:
        entries = {int(r["ID"]) for r in rows("TraitNodeEntry") if int(r["TraitDefinitionID"]) in defs}
        return {
            int(r["TraitNodeID"]) for r in rows("TraitNodeXTraitNodeEntry") if int(r["TraitNodeEntryID"]) in entries
        }

    def spells_of_nodes(nodes: set[int]) -> set[int]:
        entries = {
            int(r["TraitNodeEntryID"]) for r in rows("TraitNodeXTraitNodeEntry") if int(r["TraitNodeID"]) in nodes
        }
        defs = {int(r["TraitDefinitionID"]) for r in rows("TraitNodeEntry") if int(r["ID"]) in entries}
        return spells_of_defs(defs)

    out: dict[tuple[str, int], Reach] = {}
    for a in applied:
        if a.identical:
            continue
        versions = [r for r in (a.before, a.after) if r is not None]

        def field(name: str, versions: list[Row] = versions) -> set[int]:
            return {int(r[name]) for r in versions if name in r}

        nodes: set[int] = set()
        spells: set[int] = set()
        items: set[int] = set()
        defs: set[int] = set()
        if a.table == "TraitNode":
            nodes = {a.rec_id}
        elif a.table == "TraitEdge":
            nodes = field("LeftTraitNodeID") | field("RightTraitNodeID")
        elif a.table == "TraitNodeXTraitNodeEntry":
            nodes = field("TraitNodeID")
        elif a.table == "TraitNodeEntry":
            nodes = col("TraitNodeXTraitNodeEntry", "TraitNodeEntryID", a.rec_id, "TraitNodeID")
            defs = field("TraitDefinitionID")
        elif a.table == "TraitDefinition":
            defs = {a.rec_id}
            spells = field("SpellID")
        elif a.table == "TraitDefinitionEffectPoints":
            defs = field("TraitDefinitionID")
        elif a.table == "CurvePoint":
            curves = field("CurveID")
            defs = {
                int(r["TraitDefinitionID"]) for r in rows("TraitDefinitionEffectPoints") if int(r["CurveID"]) in curves
            }
        elif a.table in ("Spell", "SpellName"):
            spells = {a.rec_id}
        elif a.table == "SkillLineAbility":
            spells = field("Spell")
        elif a.table in ("Item", "ItemSparse"):
            items = {a.rec_id}
        elif a.table == "ItemXItemEffect":
            items = field("ItemID")
        elif "SpellID" in (versions[0] if versions else {}):
            spells = field("SpellID")
        nodes |= nodes_of_defs(defs)
        spells |= spells_of_defs(defs) | spells_of_nodes(nodes)
        out[(a.table, a.rec_id)] = Reach(nodes, spells, items)
    return out


def annotate(
    docs: Mapping[str, Any], applied: Sequence[Applied], reached: Mapping[tuple[str, int], Reach], source: HotfixSource
) -> tuple[list[dict[str, Any]], list[str]]:
    """Pose `hotfix` (poussées, enregistrements, première date vue) sur chaque entité atteinte et rend les règles
    d'origine `correctif_serveur` (chemins exacts, groupés par fichier, poussées et date), plus les enregistrements
    qui changent une valeur sans entité atteinte."""
    by_rec = {(a.table, a.rec_id): a for a in applied}
    used: set[tuple[str, int]] = set()
    groups: dict[tuple[str, tuple[int, ...], str | None], list[str]] = {}
    for file, patterns in ENTITY_SPECS.items():
        doc = docs.get(file)
        if doc is None:
            continue
        for pattern in patterns:
            for path, entity in _walk(doc, pattern):
                if not isinstance(entity, dict):
                    continue
                ids = entity_ids(entity)
                recs = sorted(
                    key
                    for key, r in reached.items()
                    if r.nodes & ids.nodes or r.spells & ids.spells or r.items & ids.items
                )
                if not recs:
                    continue
                used |= set(recs)
                pushes = tuple(sorted({by_rec[k].push_id for k in recs}))
                dates = [d for d in (source.seen_at.get(p) for p in pushes) if d]
                first = min(dates) if dates else None
                info: dict[str, Any] = {
                    "pushes": list(pushes),
                    "rows": [f"{t} {r}" for t, r in recs],
                    "first_logged_at": first,
                }
                if first is None:
                    info["dbcache_date"] = source.read_at
                entity[HOTFIX_KEY] = info
                groups.setdefault((file, pushes, first), []).append(pointer(path))
    sha = source.cache.sha256[:12]
    commit = str(source.dbd.get("commit") or "")[:12]
    rules = []
    for (file, pushes, first), paths in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "")):
        rule: dict[str, Any] = {
            "file": file,
            "paths": sorted(paths),
            "origin": SERVER_ORIGIN,
            "source": f"DBCache.bin du client (build {source.cache.build}, {source.locale}, sha256 {sha}…), "
            f"dispositions WoWDBDefs {commit} ; poussée(s) {', '.join(map(str, pushes))}",
            "certainty": "certain",
            "pushes": list(pushes),
            "seen_at": first,
        }
        if first is None:
            rule["dbcache_date"] = source.read_at
        rules.append(rule)
    unattributed = sorted(f"{t} {r}" for (t, r) in reached if (t, r) not in used)
    return rules, unattributed


def sources_block(
    source: HotfixSource,
    applied: Sequence[Applied],
    listed: Mapping[str, Any],
    checks: Mapping[str, LayoutCheck],
    entities: int,
    unattributed: Sequence[str],
    file_date: str,
) -> dict[str, Any]:
    """Bloc `hotfixes` de `sources.json` : fichier lu, définitions, poussées appliquées et dates vues, comptes,
    enregistrements appliqués (avec `unique_id`, pour la veille), listes à part, contrôles des dispositions."""
    pushes = sorted({a.push_id for a in applied})
    counts: dict[str, dict[str, int]] = {}
    for a in applied:
        row = counts.setdefault(a.table, {"VALID": 0, "DELETE": 0, "identical": 0})
        row[a.status] += 1
        row["identical"] += a.identical
    c = source.cache
    return {
        "dbcache": {
            "file": f"Cache/ADB/{source.locale}/DBCache.bin",
            "locale": source.locale,
            "format": c.format,
            "build": c.build,
            "size": c.size,
            "sha256": c.sha256,
            "file_date": file_date,
            "read_at": source.read_at,
        },
        "dbd": dict(source.dbd),
        "pushes": pushes,
        "max_push": max(pushes) if pushes else None,
        "seen_at": {str(p): source.seen_at.get(p) for p in pushes},
        "counts": dict(sorted(counts.items())),
        "applied": [
            {
                "table": a.table,
                "rec_id": a.rec_id,
                "status": a.status,
                "push": a.push_id,
                "unique_id": a.unique_id,
                "identical": a.identical,
            }
            for a in sorted(applied, key=lambda x: (x.table, x.rec_id))
        ],
        "entities": entities,
        "unattributed": list(unattributed),
        "listed": dict(listed),
        "checks": {
            t: {
                "ok": k.ok,
                "reason": k.reason,
                "decoded": k.decoded,
                "compared": k.compared,
                "equal_ratio": k.equal_ratio,
                "references_ok": k.references_ok,
            }
            for t, k in sorted(checks.items())
        },
    }


CHAIN_TABLES = (
    "TraitNode",
    "TraitNodeXTraitNodeEntry",
    "TraitNodeEntry",
    "TraitDefinition",
    "TraitDefinitionEffectPoints",
    "TraitEdge",
    "CurvePoint",
    "SpellName",
)  # tables qui relient un enregistrement à son talent ou à son sort


def _label(file: str, doc: Mapping[str, Any], path: Sequence[str], entity: Mapping[str, Any]) -> str:
    name = entity.get("name")
    name = name.get("en") if isinstance(name, dict) else name
    if file == "classes.json" and len(path) == 6:
        return f"{path[1]} {doc['classes'][path[1]]['trees'][int(path[3])]['name']} {name}"
    if file == "classes.json":
        return f"{path[1]} sort {name}"
    if file == "talents.json":
        return f"Mage {entity.get('tree')} {name}"
    if file == "spells.json":
        return f"sort {path[1]}"
    if file == "spell_scaling.json":
        return f"sort {path[1]} rang {entity.get('rank')}"
    if file == "pets.json":
        return f"familier {path[1]}"
    if file == "pvp_items.json":
        return f"bijou {name}"
    return f"{path[1]} racial {name}"


def entity_labels(version_dir: Path, reached: Mapping[tuple[str, int], Reach]) -> dict[tuple[str, int], list[str]]:
    """Entités de la version installée atteintes par chaque enregistrement (« Warrior Fury Flurry »…)."""
    import json

    out: dict[tuple[str, int], list[str]] = {}
    for file, patterns in ENTITY_SPECS.items():
        path = version_dir / file
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for pattern in patterns:
            for where, entity in _walk(doc, pattern):
                if not isinstance(entity, dict):
                    continue
                ids = entity_ids(entity)
                for key, r in reached.items():
                    if r.nodes & ids.nodes or r.spells & ids.spells or r.items & ids.items:
                        out.setdefault(key, []).append(_label(file, doc, where, entity))
    return {k: sorted(set(v)) for k, v in out.items()}


def _build_value(raw: str, like: Value) -> Value:
    try:
        if isinstance(like, float):
            return float(raw)
        if isinstance(like, int):
            return int(raw)
    except ValueError:
        return raw
    return raw


def hotfix_values(source: HotfixSource, csv_dir: Path, version_dir: Path) -> dict[str, Any]:
    """`forever hotfixes --values` : pour chaque enregistrement applicable, champ par champ, valeur du build (CSV) et
    valeur du correctif (DBCache.bin), entités de la version installée qu'il touche ; listes à part."""
    from forever.pipeline.dbd import _same
    from forever.pipeline.tables import read_table

    app = source.resolved.applicable
    wanted = dict.fromkeys([*sorted({t for t, _ in app}), *CHAIN_TABLES])
    names = [t for t in wanted if t in TABLES and _csv_file(csv_dir, t).is_file()]
    typed: dict[str, list[Row]] = {t: list(read_table(_csv_file(csv_dir, t), t)) for t in names}
    ov = apply_hotfixes(typed, source, csv_dir, strict=False)
    labels = entity_labels(version_dir, reach(ov.applied, typed, ov.tables))
    raw_rows: dict[str, dict[int, dict[str, str]]] = {}
    for table in {a.table for a in ov.applied}:
        ids = {a.rec_id for a in ov.applied if a.table == table}
        raw_rows[table] = _csv_header_and_rows(_csv_file(csv_dir, table), ids)[1]
    records = []
    for a in sorted(ov.applied, key=lambda x: (x.table, x.rec_id)):
        fields: list[dict[str, Any]] = []
        if a.status == "VALID":
            full = decode_record(source.layouts[a.table], app[(a.table, a.rec_id)].data, a.rec_id)
            raw = raw_rows[a.table].get(a.rec_id)
            for name, value in full.items():
                if name == "ID":
                    continue
                if raw is None:
                    fields.append({"field": name, "build": None, "hotfix": value})
                elif name in raw and not _same(value, raw[name]):
                    fields.append({"field": name, "build": _build_value(raw[name], value), "hotfix": value})
        records.append(
            {
                "table": a.table,
                "rec_id": a.rec_id,
                "status": a.status,
                "push": a.push_id,
                "seen_at": a.seen_at,
                "new": a.before is None,
                "identical": a.status == "VALID" and a.before is not None and not fields,
                "fields": fields,
                "entities": labels.get((a.table, a.rec_id), []),
            }
        )
    listed = {**ov.listed, "not_loaded": {t: n for t, n in ov.listed["not_loaded"].items() if t not in TABLES}}
    return {
        "build": source.cache.build,
        "sha256": source.cache.sha256,
        "dbd": dict(source.dbd),
        "records": records,
        "listed": listed,
        "checks": {t: {"ok": k.ok, "reason": k.reason} for t, k in sorted(ov.checks.items())},
    }
