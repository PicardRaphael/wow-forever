"""Mes relevés de prix d'Auctionator (`AUCTIONATOR_PRICE_DATABASE`), lus dans mes SavedVariables sans réseau.

Format déduit de mes seules SavedVariables (`tasks/inventaire-addons.md`, certitude `probable`) ; le code de l'addon
n'est jamais lu (décision 123). Une chaîne CBOR par royaume ; par objet (clé : identifiant en texte) `m` (minimum
courant, en cuivre par unité), `h` et `l` (plus haut et plus bas du minimum par jour), `a` (quantité par jour) ; le
jour compte les jours écoulés depuis `DAY_EPOCH`. Seule l'affectation `AUCTIONATOR_PRICE_DATABASE` est lue :
`AUCTIONATOR_POSTING_HISTORY` (mes ventes) ne l'est jamais."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import NamedTuple

VARIABLE = "AUCTIONATOR_PRICE_DATABASE"
DAY_EPOCH = date(2020, 1, 1)  # format de l'addon (probable, inventaire du 2026-09-28), pas une valeur de jeu


class ItemPrice(NamedTuple):
    """Dernier minimum vu d'un objet, son jour (numéro et date) et la quantité vue ce jour-là."""

    min: int
    day: int
    date: str
    quantity: int | None


def read_price_database(path: Path) -> dict[str, dict[int, ItemPrice]]:
    """Prix par royaume puis par objet (PathNotFoundError, DataSchemaError)."""
    raise NotImplementedError
