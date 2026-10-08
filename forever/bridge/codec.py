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

from collections.abc import Iterator, Sequence
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
    return bytes(i % 256 for i in range(MAX_PAYLOAD))


def fletcher16(data: bytes) -> tuple[int, int]:
    s1 = s2 = 0
    for byte in data:
        s1 = (s1 + byte) % 255
        s2 = (s2 + s1) % 255
    return s1, s2


def encode_cells(message_id: int, payload: bytes) -> list[int]:
    """Cellules du message ; ValueError si la charge dépasse MAX_PAYLOAD ou si le numéro sort de 0…65535."""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"charge de {len(payload)} octets : la bande en porte {MAX_PAYLOAD} au plus")
    if not 0 <= message_id <= 0xFFFF:
        raise ValueError(f"numéro de message hors de 0…65535 : {message_id}")
    body = message_id.to_bytes(2, "big") + len(payload).to_bytes(2, "big") + payload
    data = bytes(MAGIC) + body + bytes(fletcher16(body))
    value = int.from_bytes(data, "big")
    bits = len(data) * 8
    pad = -bits % 3
    value <<= pad
    count = (bits + pad) // 3
    return [(value >> (3 * (count - 1 - i))) & 7 for i in range(count)]


def cell_color(value: int) -> tuple[int, int, int]:
    """(R, G, B) d'une cellule : chaque canal à 255 ou 0."""
    return (255 if value & 4 else 0, 255 if value & 2 else 0, 255 if value & 1 else 0)


def render_band(cells: Sequence[int]) -> Image:
    """Image de la bande telle que l'addon la dessine : rangées complètes, cellules manquantes à 0 (noir)."""
    rows = max(1, -(-len(cells) // CELLS_PER_ROW))
    out = bytearray()
    for row in range(rows):
        line = bytearray()
        for col in range(CELLS_PER_ROW):
            i = row * CELLS_PER_ROW + col
            r, g, b = cell_color(cells[i] if i < len(cells) else 0)
            line += bytes((b, g, r, 255)) * CELL_PX
        out += bytes(line) * CELL_PX
    return Image(BAND_WIDTH, rows * CELL_PX, bytes(out))


def _value(image: Image, col: int, row: int) -> int:
    r, g, b = image.pixel(col * CELL_PX + CELL_PX // 2, row * CELL_PX + CELL_PX // 2)
    return (4 if r >= 128 else 0) | (2 if g >= 128 else 0) | (1 if b >= 128 else 0)


def _shape(image: Image) -> tuple[int, int]:
    """(rangées, colonnes) de cellules entièrement lisibles dans l'image."""
    return image.height // CELL_PX, min(CELLS_PER_ROW, image.width // CELL_PX)


def _stream(image: Image) -> Iterator[int]:
    """Cellules dans l'ordre du message ; s'arrête à la première cellule hors de l'image."""
    rows, cols = _shape(image)
    for row in range(rows):
        for col in range(CELLS_PER_ROW):
            if col >= cols:
                return
            yield _value(image, col, row)


def cell_values(image: Image, rows: int) -> list[int]:
    """Valeurs lues au centre de chaque cellule (seuil 128 par canal), rangée par rangée, dans la limite de l'image."""
    max_rows, cols = _shape(image)
    return [_value(image, col, row) for row in range(min(rows, max_rows)) for col in range(cols)]


def marker_present(probe: Image) -> bool:
    """Les cinq cellules de la sonde portent-elles le marqueur `C7 1A` ?"""
    rows, cols = _shape(probe)
    if rows < 1 or cols < len(MARKER_CELLS):
        return False
    return tuple(_value(probe, col, 0) for col in range(len(MARKER_CELLS))) == MARKER_CELLS


def decode_band(image: Image) -> Decoded | BandError | None:
    """Message lu dans l'image de la bande ; None sans marqueur ; BandError si le marqueur est là mais que la longueur,
    la taille de l'image ou la somme de contrôle ne vont pas (vérifiées dans cet ordre)."""
    data = bytearray()
    acc = nbits = 0
    needed = HEADER_BYTES
    for value in _stream(image):
        acc = (acc << 3) | value
        nbits += 3
        if nbits < 8:
            continue
        nbits -= 8
        data.append(acc >> nbits)
        acc &= (1 << nbits) - 1
        if len(data) == len(MAGIC) and tuple(data) != MAGIC:
            return None
        if len(data) == HEADER_BYTES:
            length = int.from_bytes(data[4:6], "big")
            if length > MAX_PAYLOAD:
                return BandError("length")
            needed = HEADER_BYTES + length + CHECKSUM_BYTES
        if len(data) >= needed:
            break
    if len(data) < len(MAGIC):
        return None
    if len(data) < needed:
        return BandError("truncated")
    length = needed - HEADER_BYTES - CHECKSUM_BYTES
    body = bytes(data[2 : HEADER_BYTES + length])
    if bytes(fletcher16(body)) != bytes(data[HEADER_BYTES + length : needed]):
        return BandError("checksum")
    return Decoded(int.from_bytes(data[2:4], "big"), body[4:])


def cell_mismatches(image: Image, expected: Sequence[int]) -> list[tuple[int, int, int, int]]:
    """Cellules lues différentes des cellules attendues : (rangée, colonne, attendue, lue) ; diagnostic de selftest.
    Une cellule hors de l'image est lue -1."""
    rows, cols = _shape(image)
    out = []
    for i, want in enumerate(expected):
        row, col = divmod(i, CELLS_PER_ROW)
        got = _value(image, col, row) if row < rows and col < cols else -1
        if got != want:
            out.append((row, col, want, got))
    return out
