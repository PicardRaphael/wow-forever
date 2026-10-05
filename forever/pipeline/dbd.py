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

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from forever.pipeline.dbcache import Entry
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


def parse_dbd(text: str, table: str) -> Definition:
    raise NotImplementedError


def layout_for(definition: Definition, build: str) -> Layout | None:
    raise NotImplementedError


def csv_header(layout: Layout) -> list[str]:
    raise NotImplementedError


def decode_record(layout: Layout, data: bytes, rec_id: int) -> dict[str, Value]:
    raise NotImplementedError


def layouts_to_json(layouts: Mapping[str, Layout], repo: str, commit: str, build: str) -> dict[str, Any]:
    raise NotImplementedError


def layouts_from_json(doc: Mapping[str, Any]) -> dict[str, Layout]:
    raise NotImplementedError


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
    raise NotImplementedError
