"""Mes relevés de prix d'Auctionator (`AUCTIONATOR_PRICE_DATABASE`), lus dans mes SavedVariables sans réseau.

Format déduit de mes seules SavedVariables (`tasks/inventaire-addons.md`, certitude `probable`) ; le code de l'addon
n'est jamais lu (décision 123). Une chaîne CBOR par royaume, clés en chaînes d'octets ; par objet (clé :
identifiant) `m` (minimum
courant, en cuivre par unité), `h` et `l` (plus haut et plus bas du minimum par jour), `a` (quantité par jour) ; le
jour compte les jours écoulés depuis `DAY_EPOCH`. Seule l'affectation `AUCTIONATOR_PRICE_DATABASE` est lue :
`AUCTIONATOR_POSTING_HISTORY` (mes ventes) ne l'est jamais."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.cbor import CborError, decode
from forever.pipeline.lua_table import parse_lua_value

VARIABLE = "AUCTIONATOR_PRICE_DATABASE"
DAY_EPOCH = date(2020, 1, 1)  # format de l'addon (probable, inventaire du 2026-09-28), pas une valeur de jeu
# Début d'une affectation globale : en tête de ligne, un nom suivi de « = ». Une chaîne Lua du client n'a jamais de
# saut de ligne brut (écrit `\n`) : aucune chaîne ne peut donc contenir ce motif.
_ASSIGNMENT = re.compile(rb"^([A-Za-z_]\w*)[ \t]*=", re.MULTILINE)


class ItemPrice(NamedTuple):
    """Dernier minimum vu d'un objet, son jour (numéro et date) et la quantité vue ce jour-là."""

    min: int
    day: int
    date: str
    quantity: int | None


def _value_text(raw: bytes, path: Path) -> str:
    """Texte de la seule valeur de `AUCTIONATOR_PRICE_DATABASE` (octets lus en latin-1 : un octet, un caractère)."""
    starts = list(_ASSIGNMENT.finditer(raw))
    for i, match in enumerate(starts):
        if match[1] == VARIABLE.encode():
            end = starts[i + 1].start() if i + 1 < len(starts) else len(raw)
            return raw[match.end() : end].decode("latin-1")
    raise DataSchemaError(f"{path.name} : variable {VARIABLE} absente.")


def _text_keys(value: object) -> object:
    """Clés en chaînes d'octets (le client encode les chaînes Lua en octets, type majeur 2) rendues en texte."""
    if isinstance(value, dict):
        return {(k.decode("utf-8", "replace") if isinstance(k, bytes) else k): _text_keys(v) for k, v in value.items()}
    return value


def _days(entry: dict[Any, Any], key: str) -> dict[int, Any]:
    table = entry.get(key)
    if not isinstance(table, dict):
        return {}
    return {int(k): v for k, v in table.items() if isinstance(k, str | int) and str(k).isdigit()}


def _item(entry: object) -> ItemPrice | None:
    if not isinstance(entry, dict) or not isinstance(entry.get("m"), int):
        return None
    highs, quantities = _days(entry, "h"), _days(entry, "a")
    seen = set(highs) | set(quantities)
    if not seen:
        return None
    day = max(seen)
    quantity = quantities.get(day)
    return ItemPrice(
        entry["m"],
        day,
        (DAY_EPOCH + timedelta(days=day)).isoformat(),
        quantity if isinstance(quantity, int) else None,
    )


def read_price_database(path: Path) -> dict[str, dict[int, ItemPrice]]:
    """Prix par royaume puis par objet (PathNotFoundError, DataSchemaError). Un royaume sans entrée d'objet est omis."""
    if not path.is_file():
        raise PathNotFoundError(
            "SavedVariables d'Auctionator",
            str(path),
            "donner WTF/Account/<COMPTE>/SavedVariables/Auctionator.lua (écrit au /reload ou à la déconnexion)",
        )
    text = _value_text(path.read_bytes(), path)
    try:
        root = parse_lua_value(text.rstrip().removesuffix(";"))
    except ValueError as exc:
        raise DataSchemaError(f"{path.name} : {exc}.") from exc
    if not isinstance(root, dict):
        raise DataSchemaError(f"{path.name} : {VARIABLE} n'est pas une table.")
    out: dict[str, dict[int, ItemPrice]] = {}
    for realm, blob in root.items():
        if not isinstance(realm, str) or not isinstance(blob, str) or realm.startswith("__"):
            continue
        try:
            items = _text_keys(decode(blob.encode("latin-1")))
        except CborError as exc:
            raise DataSchemaError(f"{path.name}, royaume {realm} : {exc}.") from exc
        prices = {
            int(key): price
            for key, entry in (items.items() if isinstance(items, dict) else [])
            if isinstance(key, str) and key.isdigit() and (price := _item(entry)) is not None
        }
        if prices:
            out[realm] = prices
    return out
