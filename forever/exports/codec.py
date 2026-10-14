"""Codec commun des chaînes de Naowh Forever (EX1, bloc A) : préfixe + `EncodeForPrint(CompressDeflate(Serialize(t)))`.

Fonctions pures, écrites d'après les formats publiés : LibSerialize (MIT, section « Encoding format » de son README,
version de sérialisation 1), deflate brut (RFC 1951, `zlib` de la bibliothèque standard) et l'encodage 6 bits
`EncodeForPrint` de LibDeflate (zlib : alphabet `a-zA-Z0-9()`, poids faible d'abord, sans remplissage). Les octets ne
sont pas ceux de Naowh (autre compresseur) : toute sortie deflate valide se relit, le va-et-vient se juge sur la table
décodée. Les tests relisent chaque chaîne avec les vraies bibliothèques sous `lupa` (`tests/fixtures/third_party/`).

Correspondance des valeurs : `None` ↔ nil, `bool`, `int` (|n| < 2^53, nombres du client en double), `float` fini,
`str` (UTF-8), `list`/`tuple` ↔ table tableau (clés 1..n), `dict` ↔ table ; à la lecture, une table écrite comme
tableau rend une `list`, toute autre table un `dict`. Écriture déterministe : clés triées (comme l'option `stable`),
aucune référence écrite (les références de chaînes et de tables sont lues)."""

from __future__ import annotations

import math
import re
import struct
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class ExportFormatError(ValueError):
    """Chaîne d'import illisible ou hors des bornes de l'addon (message en français)."""


@dataclass(frozen=True)
class Limits:
    """Bornes de lecture d'une chaîne (celles de Naowh Forever pour les builds, macros et listes BiS)."""

    max_chars: int
    max_bytes: int
    max_depth: int
    max_values: int


NAOWH_LIMITS = Limits(max_chars=100_000, max_bytes=1_048_576, max_depth=8, max_values=20_000)

SERIALIZATION_VERSION = 1
READABLE_VERSIONS = (1, 2)
MAX_INT = 2**53
COMPRESSION_LEVEL = 9

# Indices de type de LibSerialize (octet `TTTT T000`) et types à compte intégré (octet `CCCC TT10`).
_NIL, _NUM16, _NUM24, _NUM32, _NUM64 = 0, 1, 3, 5, 7
_FLOAT, _FLOATSTR, _FLOATSTR_NEG = 9, 10, 11
_TRUE, _FALSE = 12, 13
_STR, _TABLE, _ARRAY, _MIXED = 14, 17, 20, 23
_STRREF, _TABLEREF = 26, 29
_EMB_STR, _EMB_TABLE, _EMB_ARRAY, _EMB_MIXED = 0, 1, 2, 3

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789()"
_SIX_BITS = {c: i for i, c in enumerate(_ALPHABET)}


# --- encodage 6 bits (EncodeForPrint) -------------------------------------------------------------------------------


def encode_for_print(data: bytes) -> str:
    """Octets → texte de l'alphabet `a-zA-Z0-9()` : trois octets en quatre caractères, poids faible d'abord ; reste
    d'un octet en deux caractères, de deux octets en trois."""
    out: list[str] = []
    full = len(data) - len(data) % 3
    for i in range(0, full, 3):
        cache = data[i] | data[i + 1] << 8 | data[i + 2] << 16
        out.extend(_ALPHABET[(cache >> s) & 63] for s in (0, 6, 12, 18))
    cache, bits = 0, 0
    for b in data[full:]:
        cache |= b << bits
        bits += 8
    while bits > 0:
        out.append(_ALPHABET[cache & 63])
        cache >>= 6
        bits -= 6
    return "".join(out)


def decode_for_print(text: str) -> bytes:
    """Texte de `EncodeForPrint` → octets ; espaces et caractères de contrôle des bords ignorés, comme LibDeflate ;
    un caractère hors de l'alphabet ou un texte d'un seul caractère est refusé."""
    text = text.strip(" \t\r\n\x0b\x0c")
    if len(text) == 1:
        raise ExportFormatError("texte encodé trop court (un seul caractère)")
    try:
        values = [_SIX_BITS[c] for c in text]
    except KeyError as err:
        raise ExportFormatError(f"caractère hors de l'alphabet d'EncodeForPrint : {err.args[0]!r}") from None
    out = bytearray()
    full = len(values) - len(values) % 4
    for i in range(0, full, 4):
        cache = values[i] | values[i + 1] << 6 | values[i + 2] << 12 | values[i + 3] << 18
        out += bytes((cache & 255, cache >> 8 & 255, cache >> 16 & 255))
    cache, bits = 0, 0
    for v in values[full:]:
        cache |= v << bits
        bits += 6
    while bits >= 8:
        out.append(cache & 255)
        cache >>= 8
        bits -= 8
    return bytes(out)


# --- deflate brut ---------------------------------------------------------------------------------------------------


def deflate(data: bytes) -> bytes:
    """Deflate brut (RFC 1951, sans en-tête zlib), niveau fixé : sortie déterministe."""
    comp = zlib.compressobj(COMPRESSION_LEVEL, zlib.DEFLATED, -15)
    return comp.compress(data) + comp.flush()


def inflate(data: bytes, max_bytes: int) -> bytes:
    """Deflate brut décompressé, refusé au-delà de `max_bytes` octets (bombe) ou s'il est incomplet ou abîmé."""
    dec = zlib.decompressobj(-15)
    try:
        out = dec.decompress(data, max_bytes + 1)
    except zlib.error as err:
        raise ExportFormatError(f"données compressées abîmées ({err})") from None
    if len(out) > max_bytes:
        raise ExportFormatError(f"données décompressées au-delà de {max_bytes} octets")
    if not dec.eof:
        raise ExportFormatError("données compressées incomplètes")
    return out


# --- LibSerialize ---------------------------------------------------------------------------------------------------


def _count_bytes(n: int) -> int:
    if n < 256:
        return 1
    if n < 65536:
        return 2
    if n < 16777216:
        return 3
    raise ValueError(f"compte trop grand pour LibSerialize : {n}")


def _number_bytes(n: int) -> int:
    for size, bound in ((1, 256), (2, 65536), (3, 16777216), (4, 4294967296)):
        if n < bound:
            return size
    return 7


def _sort_key(key: Any) -> tuple[int, Any]:
    if isinstance(key, bool):
        return (2, key)
    if isinstance(key, int | float):
        return (0, key)
    return (1, key)


class _Writer:
    def __init__(self) -> None:
        self.out = bytearray()
        self.active: set[int] = set()

    def byte(self, value: int) -> None:
        self.out.append(value)

    def uint(self, value: int, size: int) -> None:
        self.out += value.to_bytes(size, "big")

    def value(self, v: Any) -> None:
        if v is None:
            self.byte(_NIL * 8)
        elif isinstance(v, bool):
            self.byte((_TRUE if v else _FALSE) * 8)
        elif isinstance(v, int):
            self.integer(v)
        elif isinstance(v, float):
            if not math.isfinite(v):
                raise ValueError(f"nombre non fini refusé : {v}")
            if v.is_integer() and abs(v) < MAX_INT:
                self.integer(int(v))
            else:
                self.byte(_FLOAT * 8)
                self.out += struct.pack(">d", v)
        elif isinstance(v, str):
            self.string(v)
        elif isinstance(v, list | tuple):
            self.table(dict(enumerate(v, 1)), v)
        elif isinstance(v, Mapping):
            self.table(v, v)
        else:
            raise TypeError(f"type non sérialisable pour LibSerialize : {type(v).__name__}")

    def integer(self, n: int) -> None:
        if abs(n) >= MAX_INT:
            raise ValueError(f"entier hors des nombres exacts du client (|n| < 2^53) : {n}")
        if 0 <= n < 128:
            self.byte(n * 2 + 1)
        elif -4096 < n < 4096:
            packed = abs(n) * 16 + (8 if n < 0 else 0) + 4
            self.byte(packed & 255)
            self.byte(packed >> 8)
        else:
            size = _number_bytes(abs(n))
            index = {2: _NUM16, 3: _NUM24, 4: _NUM32, 7: _NUM64}[size]
            self.byte((index + (1 if n < 0 else 0)) * 8)
            self.uint(abs(n), size)

    def string(self, s: str) -> None:
        raw = s.encode("utf-8")
        if len(raw) < 16:
            self.byte(len(raw) * 16 + _EMB_STR * 4 + 2)
        else:
            size = _count_bytes(len(raw))
            self.byte((_STR + size - 1) * 8)
            self.uint(len(raw), size)
        self.out += raw

    def table(self, items: Mapping[Any, Any], source: object) -> None:
        if id(source) in self.active:
            raise ValueError("table qui se contient elle-même : refusée")
        for key in items:
            if not isinstance(key, str | int | float) or key is None:
                raise TypeError(f"clé de table non sérialisable : {type(key).__name__}")
            if isinstance(key, float) and not math.isfinite(key):
                raise ValueError(f"clé non finie refusée : {key}")
        self.active.add(id(source))
        whole = {int(k) for k in items if _is_array_key(k, len(items))}
        array = 0
        while array + 1 in whole:
            array += 1
        rest = sorted((k for k in items if not _is_array_key(k, array)), key=_sort_key)
        mapped = len(rest)
        if mapped == 0:
            if array < 16:
                self.byte(array * 16 + _EMB_ARRAY * 4 + 2)
            else:
                size = _count_bytes(array)
                self.byte((_ARRAY + size - 1) * 8)
                self.uint(array, size)
        elif array:
            if array < 5 and mapped < 5:
                self.byte(((mapped - 1) * 4 + array - 1) * 16 + _EMB_MIXED * 4 + 2)
            else:
                size = max(_count_bytes(array), _count_bytes(mapped))
                self.byte((_MIXED + size - 1) * 8)
                self.uint(array, size)
                self.uint(mapped, size)
        elif mapped < 16:
            self.byte(mapped * 16 + _EMB_TABLE * 4 + 2)
        else:
            size = _count_bytes(mapped)
            self.byte((_TABLE + size - 1) * 8)
            self.uint(mapped, size)
        for i in range(1, array + 1):
            self.value(items[i])
        for key in rest:
            self.value(key)
            self.value(items[key])
        self.active.discard(id(source))


def _is_array_key(key: Any, array: int) -> bool:
    if isinstance(key, bool):
        return False
    if isinstance(key, float):
        return key.is_integer() and 1 <= key <= array
    return isinstance(key, int) and 1 <= key <= array


def serialize(value: Any) -> bytes:
    """Valeur Python → octets de LibSerialize (version 1), clés triées ; `TypeError` sur un type non pris (ensemble,
    objet, octets), `ValueError` sur un nombre que le client ne représente pas (non fini, |n| ≥ 2^53)."""
    w = _Writer()
    w.byte(SERIALIZATION_VERSION)
    w.value(value)
    return bytes(w.out)


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0
        self.strings: list[str] = []
        self.tables: list[Any] = []

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ExportFormatError("données sérialisées tronquées")
        chunk = self.data[self.pos : self.pos + n]
        self.pos += n
        return chunk

    def uint(self, size: int) -> int:
        return int.from_bytes(self.take(size), "big")

    def text(self, n: int) -> str:
        raw = self.take(n)
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ExportFormatError("chaîne non UTF-8") from None
        if n > 2:
            self.strings.append(s)
        return s

    def ref(self, refs: list[Any], index: int) -> Any:
        if not 1 <= index <= len(refs):
            raise ExportFormatError(f"référence inconnue n° {index}")
        return refs[index - 1]

    def value(self) -> Any:
        b = self.uint(1)
        if b % 2 == 1:
            return (b - 1) // 2
        if b % 4 == 2:
            typ, count = (b >> 2) & 3, b >> 4
            if typ == _EMB_STR:
                return self.text(count)
            if typ == _EMB_TABLE:
                return self.mapping(count, {})
            if typ == _EMB_ARRAY:
                return self.array(count)
            return self.mixed(count % 4 + 1, count // 4 + 1)
        if b % 8 == 4:
            packed = self.uint(1) * 256 + b
            return -((packed - 12) // 16) if b % 16 == 12 else (packed - 4) // 16
        typ = b // 8
        if typ == _NIL:
            return None
        if _NUM16 <= typ <= _NUM64 + 1:
            size = {0: 2, 1: 3, 2: 4, 3: 7}[(typ - 1) // 2]
            n = self.uint(size)
            return -n if (typ - 1) % 2 else n
        if typ == _FLOAT:
            f = struct.unpack(">d", self.take(8))[0]
            return int(f) if f.is_integer() and abs(f) < MAX_INT else f
        if typ in (_FLOATSTR, _FLOATSTR_NEG):
            raw = self.take(self.uint(1))
            try:
                f = float(raw.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                raise ExportFormatError("nombre écrit en texte illisible") from None
            return -f if typ == _FLOATSTR_NEG else f
        if typ in (_TRUE, _FALSE):
            return typ == _TRUE
        if _STR <= typ <= _STR + 2:
            return self.text(self.uint(typ - _STR + 1))
        if _TABLE <= typ <= _TABLE + 2:
            return self.mapping(self.uint(typ - _TABLE + 1), {})
        if _ARRAY <= typ <= _ARRAY + 2:
            return self.array(self.uint(typ - _ARRAY + 1))
        if _MIXED <= typ <= _MIXED + 2:
            size = typ - _MIXED + 1
            return self.mixed(self.uint(size), self.uint(size))
        if _STRREF <= typ <= _STRREF + 2:
            return self.ref(self.strings, self.uint(typ - _STRREF + 1))
        if _TABLEREF <= typ <= _TABLEREF + 2:
            return self.ref(self.tables, self.uint(typ - _TABLEREF + 1))
        raise ExportFormatError(f"octet de type inconnu : {b}")

    def mapping(self, count: int, table: dict[Any, Any], register: bool = True) -> dict[Any, Any]:
        if register:
            self.tables.append(table)
        for _ in range(count):
            key = self.value()
            if key is None or (isinstance(key, float) and math.isnan(key)):
                raise ExportFormatError("clé de table nil ou NaN")
            if isinstance(key, dict | list):
                raise ExportFormatError("clé de table qui est une table : refusée")
            table[key] = self.value()
        return table

    def array(self, count: int) -> list[Any]:
        items: list[Any] = []
        self.tables.append(items)
        for _ in range(count):
            items.append(self.value())
        return items

    def mixed(self, array: int, mapped: int) -> dict[Any, Any]:
        table: dict[Any, Any] = {}
        self.tables.append(table)
        for i in range(1, array + 1):
            table[i] = self.value()
        return self.mapping(mapped, table, register=False)


def deserialize(data: bytes) -> Any:
    """Octets de LibSerialize → une valeur Python ; références de chaînes et de tables lues ; refus en français d'une
    entrée vide, d'une version inconnue, tronquée, ou qui porte plus d'une valeur."""
    if not data:
        raise ExportFormatError("données sérialisées vides")
    if data[0] not in READABLE_VERSIONS:
        raise ExportFormatError(f"version de sérialisation inconnue : {data[0]}")
    r = _Reader(data)
    r.pos = 1
    value = r.value()
    if r.pos != len(data):
        raise ExportFormatError("plusieurs valeurs sérialisées : une seule attendue")
    return value


# --- chaîne complète ------------------------------------------------------------------------------------------------


def _check_plain(value: Any, limits: Limits) -> None:
    """Profondeur et nombre de valeurs bornés (une table qui se contient dépasse la profondeur)."""
    count = 0
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        v, depth = stack.pop()
        count += 1
        if count > limits.max_values:
            raise ExportFormatError(f"plus de {limits.max_values} valeurs")
        if isinstance(v, dict | list):
            if depth + 1 > limits.max_depth:
                raise ExportFormatError(f"tables imbriquées au-delà de la profondeur {limits.max_depth}")
            items = v.items() if isinstance(v, dict) else enumerate(v, 1)
            for k, item in items:
                stack.append((k, depth + 1))
                stack.append((item, depth + 1))
        elif isinstance(v, float) and not math.isfinite(v):
            raise ExportFormatError("nombre non fini")


def pack(prefix: str, value: Any) -> str:
    """Chaîne d'import complète : préfixe + `EncodeForPrint(deflate(serialize(value)))`."""
    return prefix + encode_for_print(deflate(serialize(value)))


def unpack(prefix: str, text: str, limits: Limits = NAOWH_LIMITS) -> Any:
    """Valeur d'une chaîne d'import : un seul jeton après le préfixe (espaces des bords permis), bornes de `limits`
    (caractères, octets décompressés, profondeur, valeurs) ; erreur en français sinon."""
    match = re.fullmatch(r"\s*" + re.escape(prefix) + r"(\S+)\s*", text)
    if match is None:
        raise ExportFormatError(f"chaîne qui ne commence pas par {prefix} suivi d'un seul jeton")
    body = match.group(1)
    if len(body) > limits.max_chars:
        raise ExportFormatError(f"chaîne de plus de {limits.max_chars} caractères")
    value = deserialize(inflate(decode_for_print(body), limits.max_bytes))
    _check_plain(value, limits)
    return value
