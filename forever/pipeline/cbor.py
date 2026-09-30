"""Décodeur CBOR minimal (RFC 8949), sans dépendance : lit la base de prix d'Auctionator dans mes SavedVariables.

Code écrit d'après la RFC seulement ; le code de l'addon n'est jamais lu (décision 123). Pris en charge : entiers
positifs et négatifs, chaînes d'octets et de texte (longueur définie ou indéfinie), tableaux, tables, étiquettes
(valeur gardée, étiquette ignorée), `false`, `true`, `null`, `undefined`, flottants de 16, 32 et 64 bits. Toute
entrée tronquée, invalide ou suivie d'octets en trop lève `CborError`."""

from __future__ import annotations

import struct

_BREAK = object()  # marqueur de fin d'un élément de longueur indéfinie
_SIMPLE = {20: False, 21: True, 22: None, 23: None}


class CborError(ValueError):
    """Entrée CBOR tronquée ou invalide."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.data):
            raise CborError(f"CBOR tronqué : {n} octet(s) attendu(s) à la position {self.pos}")
        chunk = self.data[self.pos : end]
        self.pos = end
        return chunk

    def argument(self, info: int) -> int | None:
        """Argument de l'en-tête ; None pour une longueur indéfinie (31)."""
        if info < 24:
            return info
        if info in (24, 25, 26, 27):
            return int.from_bytes(self.take(1 << (info - 24)), "big")
        if info == 31:
            return None
        raise CborError(f"CBOR invalide : information additionnelle réservée ({info}) à la position {self.pos - 1}")

    def chunks(self, major: int) -> bytes:
        """Chaîne de longueur indéfinie : morceaux définis du même type majeur jusqu'au « break »."""
        out = bytearray()
        while True:
            if self.take(1)[0] == 0xFF:
                return bytes(out)
            self.pos -= 1
            head = self.take(1)[0]
            if head >> 5 != major:
                raise CborError("CBOR invalide : morceau de chaîne d'un autre type")
            n = self.argument(head & 0x1F)
            if n is None:
                raise CborError("CBOR invalide : morceau de chaîne de longueur indéfinie")
            out += self.take(n)

    def item(self) -> object:
        head = self.take(1)[0]
        major, info = head >> 5, head & 0x1F
        if major == 7:
            return self.simple(info)
        n = self.argument(info)
        if major == 0:
            return n if n is not None else self.fail_indefinite()
        if major == 1:
            return -1 - n if n is not None else self.fail_indefinite()
        if major in (2, 3):
            raw = self.chunks(major) if n is None else self.take(n)
            if major == 2:
                return raw
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise CborError(f"CBOR invalide : texte non UTF-8 ({exc})") from exc
        if major == 4:
            return self.array(n)
        if major == 5:
            return self.table(n)
        return self.item()  # étiquette (6) : valeur gardée

    def array(self, n: int | None) -> list[object]:
        out: list[object] = []
        while n is None or len(out) < n:
            value = self.item()
            if value is _BREAK:
                if n is None:
                    return out
                raise CborError("CBOR invalide : « break » dans un tableau de longueur définie")
            out.append(value)
        return out

    def table(self, n: int | None) -> dict[object, object]:
        out: dict[object, object] = {}
        count = 0
        while n is None or count < n:
            key = self.item()
            if key is _BREAK:
                if n is None:
                    return out
                raise CborError("CBOR invalide : « break » dans une table de longueur définie")
            value = self.item()
            if value is _BREAK:
                raise CborError("CBOR invalide : clé sans valeur")
            if isinstance(key, list | dict):
                raise CborError("CBOR non pris en charge : clé de table composée")
            out[key] = value
            count += 1
        return out

    def simple(self, info: int) -> object:
        if info in _SIMPLE:
            return _SIMPLE[info]
        if info == 25:
            return struct.unpack(">e", self.take(2))[0]
        if info == 26:
            return struct.unpack(">f", self.take(4))[0]
        if info == 27:
            return struct.unpack(">d", self.take(8))[0]
        if info == 31:
            return _BREAK
        raise CborError(f"CBOR non pris en charge : valeur simple {info}")

    @staticmethod
    def fail_indefinite() -> int:
        raise CborError("CBOR invalide : entier de longueur indéfinie")


def decode(data: bytes) -> object:
    """Valeur CBOR unique occupant tout `data` (CborError sinon)."""
    reader = _Reader(data)
    value = reader.item()
    if value is _BREAK:
        raise CborError("CBOR invalide : « break » hors d'un élément de longueur indéfinie")
    if reader.pos != len(data):
        raise CborError(f"CBOR invalide : {len(data) - reader.pos} octet(s) en trop après la valeur")
    return value
