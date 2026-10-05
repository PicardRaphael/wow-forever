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

from collections.abc import Collection, Iterable, Mapping, Sequence
from enum import IntEnum
from pathlib import Path
from typing import Any, NamedTuple

DBCACHE_PATH = ("Cache", "ADB", "{locale}", "DBCache.bin")


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
    raise NotImplementedError


def parse_dbcache(raw: bytes) -> DBCache:
    raise NotImplementedError


def read_dbcache(path: Path) -> DBCache:
    raise NotImplementedError


def table_names(names: Iterable[str]) -> dict[int, str]:
    raise NotImplementedError


def known_tables(rules: Mapping[str, Any]) -> set[str]:
    raise NotImplementedError


def entry_kind(entry: Entry) -> str:
    raise NotImplementedError


def effective(entries: Sequence[Entry], names: Mapping[int, str]) -> Resolved:
    raise NotImplementedError


def summarize_cache(cache: DBCache, names: Mapping[int, str]) -> dict[str, Any]:
    raise NotImplementedError


def crosscheck(
    entries: Sequence[Entry],
    names: Mapping[int, str],
    journal: Sequence[Mapping[str, Any]],
    build: int,
    tracked: Collection[str],
) -> CrossCheck:
    raise NotImplementedError
