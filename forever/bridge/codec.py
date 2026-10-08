"""Codec de la bande de pixels de ForeverBridge (P06a, bloc A) : octets du message en cellules de 3 bits, chaque
cellule étant un carré dont les canaux R, G et B sont tout allumés ou tout éteints (8 couleurs, résistantes au
gamma).

Message : `[C7 1A] [numéro fort, faible] [longueur forte, faible] [charge] [Fletcher-16 s1, s2]`, somme sur
numéro…charge ; octets découpés en cellules du bit de poids fort au plus faible (bit 2 = R, 1 = G, 0 = B) ; cellules
de 4 × 4 pixels, 200 par rangée, 24 rangées au plus. Le même codec existe en Lua (`addon/ForeverBridge/Codec.lua`) ;
les tests vérifient qu'ils rendent les mêmes cellules.

Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : `addon/WoWAI/Codec.lua`,
décodeur de `bridge/capture.ps1`), sous la licence suivante :

MIT License

Copyright (c) 2026 chelinho139

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from forever.bridge.image import Image

CELL_PX = 4
CELLS_PER_ROW = 200
MAX_ROWS = 24
MAGIC = (0xC7, 0x1A)
HEADER_BYTES = 6
CHECKSUM_BYTES = 2
MAX_PAYLOAD = MAX_ROWS * CELLS_PER_ROW * 3 // 8 - HEADER_BYTES - CHECKSUM_BYTES
MARKER_CELLS = (6, 1, 6, 1, 5)
BAND_WIDTH = CELLS_PER_ROW * CELL_PX
BAND_HEIGHT = MAX_ROWS * CELL_PX
PROBE_WIDTH = len(MARKER_CELLS) * CELL_PX
PROBE_HEIGHT = CELL_PX
# Bande de test (`/fv test`, `forever bridge selftest`) : charge pleine, toutes les valeurs d'octet, 24 rangées.
SELFTEST_ID = 4242


@dataclass(frozen=True)
class Decoded:
    message_id: int
    payload: bytes


@dataclass(frozen=True)
class BandError:
    reason: Literal["length", "truncated", "checksum"]


def selftest_payload() -> bytes:
    """Charge de la bande de test : octet i = i mod 256, sur toute la charge."""
    raise NotImplementedError


def fletcher16(data: bytes) -> tuple[int, int]:
    raise NotImplementedError


def encode_cells(message_id: int, payload: bytes) -> list[int]:
    """Cellules du message ; ValueError si la charge dépasse MAX_PAYLOAD ou si le numéro sort de 0…65535."""
    raise NotImplementedError


def cell_color(value: int) -> tuple[int, int, int]:
    """(R, G, B) d'une cellule : chaque canal à 255 ou 0."""
    raise NotImplementedError


def render_band(cells: Sequence[int]) -> Image:
    """Image de la bande telle que l'addon la dessine : rangées complètes, cellules manquantes à 0 (noir)."""
    raise NotImplementedError


def cell_values(image: Image, rows: int) -> list[int]:
    """Valeurs lues au centre de chaque cellule (seuil 128 par canal), rangée par rangée, dans la limite de l'image."""
    raise NotImplementedError


def marker_present(probe: Image) -> bool:
    """Les cinq cellules de la sonde portent-elles le marqueur `C7 1A` ?"""
    raise NotImplementedError


def decode_band(image: Image) -> Decoded | BandError | None:
    """Message lu dans l'image de la bande ; None sans marqueur ; BandError si le marqueur est là mais que la longueur,
    la taille de l'image ou la somme de contrôle ne vont pas (vérifiées dans cet ordre)."""
    raise NotImplementedError


def cell_mismatches(image: Image, expected: Sequence[int]) -> list[tuple[int, int, int, int]]:
    """Cellules lues différentes des cellules attendues : (rangée, colonne, attendue, lue) ; diagnostic de selftest."""
    raise NotImplementedError
