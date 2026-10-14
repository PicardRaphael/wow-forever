"""Codec commun des chaînes de Naowh Forever (EX1, bloc A) : préfixe + `EncodeForPrint(CompressDeflate(Serialize(t)))`.

Fonctions pures, écrites d'après les formats publiés : LibSerialize (MIT, section « Encoding format » de son README,
version de sérialisation 1), deflate brut (RFC 1951, `zlib` de la bibliothèque standard) et l'encodage 6 bits
`EncodeForPrint` de LibDeflate (zlib : alphabet `a-zA-Z0-9()`, poids faible d'abord, sans remplissage). Les octets ne
sont pas ceux de Naowh (autre compresseur) : toute sortie deflate valide se relit, le va-et-vient se juge sur la table
décodée. Les tests relisent chaque chaîne avec les vraies bibliothèques sous `lupa` (`tests/fixtures/third_party/`)."""

from __future__ import annotations

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


def serialize(value: Any) -> bytes:
    raise NotImplementedError


def deserialize(data: bytes) -> Any:
    raise NotImplementedError


def encode_for_print(data: bytes) -> str:
    raise NotImplementedError


def decode_for_print(text: str) -> bytes:
    raise NotImplementedError


def deflate(data: bytes) -> bytes:
    raise NotImplementedError


def inflate(data: bytes, max_bytes: int) -> bytes:
    raise NotImplementedError


def pack(prefix: str, value: Any) -> str:
    raise NotImplementedError


def unpack(prefix: str, text: str, limits: Limits = NAOWH_LIMITS) -> Any:
    raise NotImplementedError
