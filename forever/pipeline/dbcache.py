"""Correctifs du serveur lus dans `Cache/ADB/<locale>/DBCache.bin` du client (T08c, bloc A), lecture locale seulement.

Format (format 9) : en-tête `XFTH`, format, build, 32 octets de contrôle ; puis des entrées contiguës : `XFTH`,
`int32` (sens non établi), `int32 push_id`, `uint32 unique_id`, `uint32 table_hash` (`SStrHash` du nom de table),
`uint32 rec_id`, `uint32 data_size`, `uint8 status` + 3 octets, puis les données de l'enregistrement.

Familles d'entrées : poussée réelle (`push_id` >= 0) ; réponse `DBReply` (`push_id` −1 : « enregistrement absent » en
réponse à une requête du client, jamais une suppression) ; réponse d'objet (`push_id == unique_id >= 0x01000000`,
enregistrement envoyé à la demande, sens non établi : jamais appliquée). Seules les entrées `VALID` et `DELETE` des
poussées réelles sont applicables ; à table et enregistrement égaux, la poussée la plus haute l'emporte, à poussée
égale la dernière du fichier. `INVALID` et `NOTPUBLIC` ne portent aucune valeur. Les entrées `TactKey` (clés de
chiffrement) sont ignorées sans être lues ni nommées. Aucun chiffre de jeu ici."""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Collection, Iterable, Mapping, Sequence
from enum import IntEnum
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError

DBCACHE_PATH = ("Cache", "ADB", "{locale}", "DBCache.bin")
SIGNATURE = b"XFTH"
FORMAT = 9
HEADER_SIZE = 44  # signature, format, build, 32 octets de contrôle
ITEM_REPLY_FLAG = 0x01000000
_HEADER = struct.Struct("<4sII")
_ENTRY = struct.Struct("<4siiIIIIB3x")
_SEED, _SHIFT = 0x7FED7FED, 0xEEEEEEEE
_STORM = (
    0x486E26EE, 0xDCAA16B3, 0xE1918EEF, 0x202DAFDB, 0x341C7DC7, 0x1C365303, 0x40EF2D37, 0x65FD5E49,
    0xD6057177, 0x904ECE93, 0x1C38024F, 0x98FD323B, 0xE3061AE7, 0xA39B0FA1, 0x9797F25F, 0xE4444563,
)  # fmt: skip


class Status(IntEnum):
    VALID = 1
    DELETE = 2
    INVALID = 3
    NOTPUBLIC = 4


class Entry(NamedTuple):
    region_id: int
    push_id: int
    unique_id: int
    table_hash: int
    rec_id: int
    status: int
    data: bytes
    offset: int


class DBCache(NamedTuple):
    format: int
    build: int
    entries: list[Entry]
    sha256: str
    size: int


class Listed(NamedTuple):
    table: str
    rec_id: int
    push_id: int


class Resolved(NamedTuple):
    applicable: dict[tuple[str, int], Entry]  # VALID et DELETE des poussées réelles, tables connues
    invalid: list[Listed]
    notpublic: list[Listed]
    dbreply: dict[str, int]  # table -> nombre de réponses « absent »
    item_reply: dict[str, int]  # table -> nombre de réponses d'objets
    unknown_hash: dict[int, int]  # hachage -> nombre d'entrées


class CrossCheck(NamedTuple):
    matched: int
    only_log: list[dict[str, Any]]
    only_cache: list[dict[str, Any]]


def table_hash(name: str) -> int:
    """`SStrHash` de Storm (nom en majuscules, graine 0x7FED7FED) : hachage du nom de table dans `DBCache.bin`."""
    seed, shift = _SEED, _SHIFT
    for ch in name.upper():
        c = ord(ch)
        seed = ((_STORM[c >> 4] - _STORM[c & 0xF]) & 0xFFFFFFFF) ^ ((shift + seed) & 0xFFFFFFFF)
        shift = (c + seed + 33 * shift + 3) & 0xFFFFFFFF
    return seed or 1


_TACT = table_hash("TactKey")


def parse_dbcache(raw: bytes) -> DBCache:
    """Toutes les entrées du fichier ; DataSchemaError si la signature, le format ou une taille ne tombe pas juste
    (jamais de lecture partielle silencieuse)."""
    if len(raw) < HEADER_SIZE:
        raise DataSchemaError(f"DBCache.bin tronqué : {len(raw)} octets, en-tête de {HEADER_SIZE} attendu.")
    sig, fmt, build = _HEADER.unpack_from(raw, 0)
    if sig != SIGNATURE:
        raise DataSchemaError("DBCache.bin : signature XFTH absente de l'en-tête.")
    if fmt != FORMAT:
        raise DataSchemaError(f"DBCache.bin : format {fmt}, seul le format {FORMAT} est lu.")
    entries: list[Entry] = []
    off = HEADER_SIZE
    while off < len(raw):
        if off + _ENTRY.size > len(raw):
            raise DataSchemaError(f"DBCache.bin tronqué : en-tête d'entrée coupé à l'octet {off}.")
        sig, region, push, unique, th, rec, size, status = _ENTRY.unpack_from(raw, off)
        if sig != SIGNATURE:
            raise DataSchemaError(f"DBCache.bin : signature XFTH absente à l'octet {off} (désalignement).")
        if status not in {s.value for s in Status}:
            raise DataSchemaError(f"DBCache.bin : statut {status} inconnu à l'octet {off}.")
        start = off + _ENTRY.size
        if start + size > len(raw):
            raise DataSchemaError(f"DBCache.bin tronqué : données de l'entrée de l'octet {off} coupées.")
        entries.append(Entry(region, push, unique, th, rec, status, raw[start : start + size], off))
        off = start + size
    return DBCache(fmt, build, entries, hashlib.sha256(raw).hexdigest(), len(raw))


def read_dbcache(path: Path) -> DBCache:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DataSchemaError(f"{path} illisible ({exc}).") from exc
    return parse_dbcache(raw)


def table_names(names: Iterable[str]) -> dict[int, str]:
    """Hachage -> nom, pour les noms donnés (`TactKey` jamais nommée)."""
    return {table_hash(n): n for n in names if table_hash(n) != _TACT}


def known_tables(rules: Mapping[str, Any]) -> set[str]:
    """Tables lues par le projet (`decode_rules.json`) : celles du journal des correctifs et celles des familiers."""
    from forever.pipeline.hotfixes import tracked_tables

    return tracked_tables(rules) | set(rules.get("pet_tables", []))


def entry_kind(entry: Entry) -> str:
    """`push` (poussée réelle), `dbreply` (réponse « absent ») ou `item_reply` (réponse d'objet à la demande)."""
    if entry.push_id >= ITEM_REPLY_FLAG and entry.push_id == entry.unique_id:
        return "item_reply"
    return "push" if entry.push_id >= 0 else "dbreply"


def _name(names: Mapping[int, str], th: int) -> str:
    return names.get(th) or f"{th:#010x}"


def effective(entries: Sequence[Entry], names: Mapping[int, str]) -> Resolved:
    """Entrées applicables (la poussée la plus haute l'emporte, à égalité la dernière du fichier) et listes à part."""
    applicable: dict[tuple[str, int], Entry] = {}
    invalid: list[Listed] = []
    notpublic: list[Listed] = []
    dbreply: dict[str, int] = {}
    item_reply: dict[str, int] = {}
    unknown: dict[int, int] = {}
    voided: dict[tuple[str, int], int] = {}  # poussée la plus haute d'une entrée sans valeur
    for e in entries:
        if e.table_hash == _TACT:
            continue
        kind = entry_kind(e)
        if kind != "push":
            counts = dbreply if kind == "dbreply" else item_reply
            counts[_name(names, e.table_hash)] = counts.get(_name(names, e.table_hash), 0) + 1
            continue
        table = names.get(e.table_hash)
        if table is None:
            unknown[e.table_hash] = unknown.get(e.table_hash, 0) + 1
        elif e.status in (Status.INVALID, Status.NOTPUBLIC):
            (invalid if e.status == Status.INVALID else notpublic).append(Listed(table, e.rec_id, e.push_id))
            voided[(table, e.rec_id)] = max(voided.get((table, e.rec_id), e.push_id), e.push_id)
        else:
            key = (table, e.rec_id)
            if key not in applicable or e.push_id >= applicable[key].push_id:
                applicable[key] = e
    # une entrée sans valeur d'une poussée plus haute rend caduque la valeur plus ancienne : rien n'est appliqué
    for key, push in voided.items():
        if key in applicable and applicable[key].push_id < push:
            del applicable[key]
    return Resolved(applicable, invalid, notpublic, dbreply, item_reply, unknown)


def summarize_cache(cache: DBCache, names: Mapping[int, str]) -> dict[str, Any]:
    """Comptes par table et par statut des poussées réelles ; réponses et hachages inconnus à part."""
    order = [s.name for s in Status]
    tables: dict[str, dict[str, int]] = {}
    pushes: set[int] = set()
    for e in cache.entries:
        if e.table_hash == _TACT or entry_kind(e) != "push":
            continue
        pushes.add(e.push_id)
        table = names.get(e.table_hash)
        if table is not None:
            row = tables.setdefault(table, {})
            row[Status(e.status).name] = row.get(Status(e.status).name, 0) + 1
    res = effective(cache.entries, names)
    return {
        "format": cache.format,
        "build": cache.build,
        "size": cache.size,
        "sha256": cache.sha256,
        "entries": len(cache.entries),
        "tables": {
            t: dict(sorted(row.items(), key=lambda kv: order.index(kv[0]))) for t, row in sorted(tables.items())
        },
        "dbreply": dict(sorted(res.dbreply.items())),
        "item_reply": dict(sorted(res.item_reply.items())),
        "unknown_hash": {f"{h:#010x}": n for h, n in sorted(res.unknown_hash.items())},
        "pushes": sorted(pushes),
        "max_push": max(pushes) if pushes else None,
    }


Key = tuple[str, str, int, str]  # (poussée, table, enregistrement, statut)


def crosscheck(
    entries: Sequence[Entry],
    names: Mapping[int, str],
    journal: Sequence[Mapping[str, Any]],
    build: int,
    tracked: Collection[str],
) -> CrossCheck:
    """Poussées réelles des tables suivies face aux lignes du journal des correctifs du même build (`client_build`
    finissant par le build de l'en-tête) ; `NOTPUBLIC`, `DBReply` et réponses d'objets hors du recoupement."""
    cache_keys: set[Key] = set()
    for e in entries:
        table = names.get(e.table_hash)
        if table is None or table not in tracked or entry_kind(e) != "push" or e.status == Status.NOTPUBLIC:
            continue
        cache_keys.add((str(e.push_id), table, e.rec_id, Status(e.status).name))
    log_keys: set[Key] = set()
    for j in journal:
        push = str(j.get("push", ""))
        if not str(j.get("client_build") or "").endswith(f".{build}") or not push.isdigit():
            continue
        if int(push) >= ITEM_REPLY_FLAG or j.get("table") not in tracked:
            continue
        log_keys.add((push, str(j["table"]), int(j["rec_id"]), str(j["result"])))

    def rows(keys: Iterable[Key]) -> list[dict[str, Any]]:
        return [{"push": p, "table": t, "rec_id": r, "result": s} for p, t, r, s in sorted(keys)]

    return CrossCheck(len(cache_keys & log_keys), rows(log_keys - cache_keys), rows(cache_keys - log_keys))
