"""Décodeur CBOR minimal (RFC 8949), sans dépendance : lit la base de prix d'Auctionator dans mes SavedVariables.

Code écrit d'après la RFC seulement ; le code de l'addon n'est jamais lu (décision 123). Pris en charge : entiers
positifs et négatifs, chaînes d'octets et de texte (longueur définie ou indéfinie), tableaux, tables, étiquettes
(valeur gardée, étiquette ignorée), `false`, `true`, `null`, `undefined`, flottants de 16, 32 et 64 bits. Toute
entrée tronquée, invalide ou suivie d'octets en trop lève `CborError`."""

from __future__ import annotations


class CborError(ValueError):
    """Entrée CBOR tronquée ou invalide."""


def decode(data: bytes) -> object:
    """Valeur CBOR unique occupant tout `data` (CborError sinon)."""
    raise NotImplementedError
