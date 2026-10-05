"""Définitions de structure des tables du client (format `.dbd` de WoWDBDefs, T08c, bloc B) et décodage des
enregistrements des correctifs du serveur (`DBCache.bin`).

Un `.dbd` déclare les colonnes (`COLUMNS` : type `int`, `float`, `locstring`, `string`, référence `<Table::ID>`)
puis des blocs de disposition (`LAYOUT`, `BUILD` : builds exacts ou plages `a-b`, `COMMENT`), chacun listant les
champs dans l'ordre des octets : annotations `$id$`, `$noninline$`, `$relation$`, taille `<8>`…`<64>` (`u` : non
signé), tableau `[N]`. Seul le bloc qui nomme le build demandé sert : jamais celui d'un build voisin.

Données d'un correctif : les champs dans l'ordre du bloc, sans l'identifiant non intégré (c'est `rec_id`), les
chaînes terminées par un octet nul, les flottants sur 4 octets. Les noms rendus sont ceux des CSV de wago.tools
(`Pos_0`, `_Index`), pour qu'une ligne décodée se lise comme une ligne des tables du build. Aucun chiffre de jeu
ici : le seuil de validation est un réglage de l'outil."""

from __future__ import annotations

import re
import struct
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from forever.errors import DataSchemaError
from forever.pipeline.dbcache import Entry, Status
from forever.pipeline.tables import Value

MIN_EQUAL_RATIO = 0.5  # réglage : en dessous, la disposition donne du bruit (valeurs du build presque toutes fausses)
MIN_COMPARED_VALUES = 10  # réglage : nombre de valeurs comparées à partir duquel le taux d'égalité compte


class Column(NamedTuple):
    name: str
    kind: str  # int, float, locstring, string
    ref: str | None  # table référencée (`int<Table::ID>`)


class Field(NamedTuple):
    name: str
    kind: str
    size: int | None  # bits, entiers seulement
    signed: bool | None
    array: int | None
    inline: bool
    is_id: bool
    relation: bool
    ref: str | None


class Block(NamedTuple):
    layouts: tuple[str, ...]
    builds: frozenset[str]
    ranges: tuple[tuple[str, str], ...]
    fields: tuple[Field, ...]


class Definition(NamedTuple):
    table: str
    columns: dict[str, Column]
    blocks: tuple[Block, ...]


class Layout(NamedTuple):
    table: str
    layout: str
    build: str
    fields: tuple[Field, ...]


class LayoutCheck(NamedTuple):
    table: str
    ok: bool
    reason: str
    decoded: int
    compared: int
    equal_ratio: float | None
    references_ok: bool | None


_COLUMN = re.compile(
    r"^(?P<kind>int|float|locstring|string)(?:<(?P<ref>[A-Za-z0-9_]+)::[A-Za-z0-9_]+>)?\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\??\s*(?://.*)?$"
)
_FIELD = re.compile(
    r"^(?:\$(?P<ann>[a-z,]+)\$)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:<(?P<size>u?\d+)>)?(?:\[(?P<array>\d+)\])?"
    r"\s*(?://.*)?$"
)
_CSV_RENAMES = {"Index": "_Index"}  # nom réservé, renommé dans les CSV de wago.tools
_INT_FORMATS = {8: "b", 16: "h", 32: "i", 64: "q"}


def parse_dbd(text: str, table: str) -> Definition:
    """Colonnes et blocs de disposition d'un `.dbd` ; DataSchemaError si une ligne ne suit pas le format."""
    sections = [s for s in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()) if s.strip()]
    if not sections or sections[0].splitlines()[0].strip() != "COLUMNS":
        raise DataSchemaError(f"{table}.dbd : section COLUMNS attendue en tête.")
    columns: dict[str, Column] = {}
    for line in sections[0].splitlines()[1:]:
        m = _COLUMN.match(line.strip())
        if m is None:
            raise DataSchemaError(f"{table}.dbd : colonne illisible « {line.strip()} ».")
        columns[m["name"]] = Column(m["name"], m["kind"], m["ref"])
    blocks = []
    for section in sections[1:]:
        layouts: list[str] = []
        builds: set[str] = set()
        ranges: list[tuple[str, str]] = []
        fields: list[Field] = []
        for raw in section.splitlines():
            line = raw.strip()
            if line.startswith("LAYOUT "):
                layouts += [h.strip() for h in line[len("LAYOUT ") :].split(",") if h.strip()]
            elif line.startswith("BUILD "):
                for item in (b.strip() for b in line[len("BUILD ") :].split(",")):
                    if "-" in item:
                        lo, hi = (x.strip() for x in item.split("-", 1))
                        ranges.append((lo, hi))
                    elif item:
                        builds.add(item)
            elif line.startswith("COMMENT"):
                continue
            else:
                fields.append(_field(line, columns, table))
        blocks.append(Block(tuple(layouts), frozenset(builds), tuple(ranges), tuple(fields)))
    return Definition(table, columns, tuple(blocks))


def _field(line: str, columns: Mapping[str, Column], table: str) -> Field:
    m = _FIELD.match(line)
    if m is None or m["name"] not in columns:
        raise DataSchemaError(f"{table}.dbd : champ illisible ou sans colonne « {line} ».")
    column = columns[m["name"]]
    annotations = set((m["ann"] or "").split(",")) - {""}
    size = m["size"]
    return Field(
        name=m["name"],
        kind=column.kind,
        size=int(size.lstrip("u")) if size else None,
        signed=(not (size or "").startswith("u")) if column.kind == "int" else None,
        array=int(m["array"]) if m["array"] else None,
        inline="noninline" not in annotations,
        is_id="id" in annotations,
        relation="relation" in annotations,
        ref=column.ref,
    )


def _build_key(build: str) -> tuple[int, ...]:
    return tuple(int(x) for x in build.split("."))


def layout_for(definition: Definition, build: str) -> Layout | None:
    """Bloc qui nomme `build` (build exact ou plage qui le contient) ; None sinon, jamais un bloc voisin."""
    key = _build_key(build)
    for block in definition.blocks:
        inside = any(_build_key(lo) <= key <= _build_key(hi) for lo, hi in block.ranges)
        if build in block.builds or inside:
            name = block.layouts[0] if block.layouts else ""
            return Layout(definition.table, name, build, block.fields)
    return None


def _csv_name(field: Field) -> str:
    return _CSV_RENAMES.get(field.name, field.name)


def csv_header(layout: Layout) -> list[str]:
    """Colonnes du CSV de wago.tools pour cette disposition : identifiant non intégré en tête, puis les champs dans
    l'ordre, un tableau en `Nom_0`, `Nom_1`…"""
    head: list[str] = []
    rest: list[str] = []
    for f in layout.fields:
        if f.is_id and not f.inline:
            head.append(_csv_name(f))
        elif f.array:
            rest += [f"{_csv_name(f)}_{i}" for i in range(f.array)]
        else:
            rest.append(_csv_name(f))
    return head + rest


def _float32(raw: bytes) -> float:
    """Flottant sur 4 octets rendu par l'écriture décimale la plus courte qui le redonne (0.1, pas 0.100000001…)."""
    value = float(struct.unpack("<f", raw)[0])
    for digits in range(6, 10):
        short = float(f"{value:.{digits}g}")
        if struct.pack("<f", short) == raw:
            return short
    return value


def decode_record(layout: Layout, data: bytes, rec_id: int) -> dict[str, Value]:
    """Enregistrement d'un correctif, noms des CSV ; DataSchemaError si les données ne remplissent pas exactement la
    disposition (taille des données différente : disposition fausse ou format autre)."""
    out: dict[str, Value] = {}
    off = 0
    try:
        for f in layout.fields:
            if f.is_id and not f.inline:
                out[_csv_name(f)] = rec_id
                continue
            values: list[Value] = []
            for _ in range(f.array or 1):
                if f.kind in ("locstring", "string"):
                    end = data.index(b"\0", off)
                    values.append(data[off:end].decode("utf-8"))
                    off = end + 1
                elif f.kind == "float":
                    if off + 4 > len(data):
                        raise ValueError("données coupées")
                    values.append(_float32(data[off : off + 4]))
                    off += 4
                else:
                    if f.size not in _INT_FORMATS:
                        raise ValueError(f"taille d'entier {f.size} inconnue pour {f.name}")
                    fmt = _INT_FORMATS[f.size]
                    values.append(struct.unpack_from("<" + (fmt if f.signed else fmt.upper()), data, off)[0])
                    off += f.size // 8
            if f.array:
                out |= {f"{_csv_name(f)}_{i}": v for i, v in enumerate(values)}
            else:
                out[_csv_name(f)] = values[0]
    except (ValueError, struct.error, UnicodeDecodeError) as exc:
        raise DataSchemaError(
            f"{layout.table} {rec_id} : taille des données ({len(data)} octets) différente de la disposition "
            f"{layout.layout} ({exc})."
        ) from exc
    if off != len(data):
        raise DataSchemaError(
            f"{layout.table} {rec_id} : taille des données ({len(data)} octets) différente de la disposition "
            f"{layout.layout} ({off} octets lus)."
        )
    return out


def layouts_to_json(layouts: Mapping[str, Layout], repo: str, commit: str, build: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "repo": repo,
        "commit": commit,
        "build": build,
        "layouts": {
            table: {
                "layout": lay.layout,
                "fields": [
                    {
                        "name": f.name,
                        "kind": f.kind,
                        "size": f.size,
                        "signed": f.signed,
                        "array": f.array,
                        "inline": f.inline,
                        "id": f.is_id,
                        "relation": f.relation,
                        "ref": f.ref,
                    }
                    for f in lay.fields
                ],
            }
            for table, lay in sorted(layouts.items())
        },
    }


def layouts_from_json(doc: Mapping[str, Any]) -> dict[str, Layout]:
    build = str(doc["build"])
    return {
        table: Layout(
            table,
            str(spec["layout"]),
            build,
            tuple(
                Field(
                    name=str(f["name"]),
                    kind=str(f["kind"]),
                    size=f["size"],
                    signed=f["signed"],
                    array=f["array"],
                    inline=bool(f["inline"]),
                    is_id=bool(f["id"]),
                    relation=bool(f["relation"]),
                    ref=f["ref"],
                )
                for f in spec["fields"]
            ),
        )
        for table, spec in doc["layouts"].items()
    }


def _same(value: Value, text: str) -> bool:
    try:
        if isinstance(value, float):
            return abs(float(text) - value) <= 1e-6 * max(1.0, abs(value))
        if isinstance(value, int):
            return int(text) == value
    except ValueError:
        return False
    return str(value) == text


def validate_layout(
    layout: Layout,
    entries: Sequence[Entry],
    header: Sequence[str] | None,
    csv_rows: Mapping[int, Mapping[str, str]],
    known_ids: Mapping[str, set[int]],
    *,
    min_ratio: float = MIN_EQUAL_RATIO,
    min_values: int = MIN_COMPARED_VALUES,
) -> LayoutCheck:
    """Disposition validée pour les entrées `VALID` d'une table : (1) en-tête du CSV du build égal aux noms de la
    disposition ; (2) données de chaque entrée remplies exactement ; (3) identifiant égal à `rec_id` ; (4) au moins
    `min_ratio` des valeurs égales à la ligne du build de même identifiant, dès `min_values` valeurs comparées ; (5)
    au moins `min_ratio` des références non nulles résolues dans `known_ids` (table référencée -> identifiants
    connus). Toutes les raisons d'un refus sont rendues ensemble. Limite : deux champs de même taille inversés sans
    référence ni ligne comparable ne se voient pas."""
    reasons: list[str] = []
    expected = csv_header(layout)
    if header is not None and list(header) != expected:
        missing = [h for h in expected if h not in header]
        extra = [h for h in header if h not in expected]
        detail = f"absentes {missing}, en plus {extra}" if missing or extra else "ordre différent"
        reasons.append(f"en-tête du CSV différent de la disposition ({detail})")
    rows: list[tuple[int, dict[str, Value]]] = []
    size_errors = id_errors = 0
    for e in entries:
        if e.status != Status.VALID:
            continue
        try:
            row = decode_record(layout, e.data, e.rec_id)
        except DataSchemaError:
            size_errors += 1
            continue
        if row.get("ID") != e.rec_id:
            id_errors += 1
            continue
        rows.append((e.rec_id, row))
    if size_errors:
        reasons.append(f"taille des données différente de la disposition ({size_errors} entrée(s))")
    if id_errors:
        reasons.append(f"identifiant intégré différent de rec_id ({id_errors} entrée(s))")
    compared = total = equal = 0
    for rec_id, row in rows:
        base = csv_rows.get(rec_id)
        if base is None:
            continue
        compared += 1
        for name, value in row.items():
            if name != "ID" and name in base:
                total += 1
                equal += _same(value, base[name])
    ratio = equal / total if total else None
    if ratio is not None and total >= min_values and ratio < min_ratio:
        reasons.append(f"valeurs égales au build : {ratio:.0%} < {min_ratio:.0%} (bruit)")
    checked = resolved = 0
    for f in layout.fields:
        if f.ref is None or f.ref not in known_ids or f.is_id:
            continue
        names = [f"{_csv_name(f)}_{i}" for i in range(f.array)] if f.array else [_csv_name(f)]
        for _, row in rows:
            for name in names:
                ref_value = row.get(name)
                if isinstance(ref_value, int) and ref_value != 0:
                    checked += 1
                    resolved += ref_value in known_ids[f.ref]
    references_ok = None if checked == 0 else resolved / checked >= min_ratio
    if references_ok is False:
        reasons.append(f"références non résolues ({checked - resolved}/{checked})")
    summary = (
        f"disposition {layout.layout} validée : {len(rows)} entrée(s) décodée(s), {compared} comparée(s)"
        + (f", {ratio:.0%} des valeurs égales au build" if ratio is not None else "")
        + (f", {resolved}/{checked} références résolues" if checked else "")
    )
    return LayoutCheck(
        layout.table, not reasons, "; ".join(reasons) or summary, len(rows), compared, ratio, references_ok
    )
