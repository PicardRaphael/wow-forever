"""Image BGRA minimale et fichiers BMP 24 et 32 bits (captures de la bande, fixtures), sans Pillow."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

_FILE_HEADER = struct.Struct("<2sIHHI")
_INFO_HEADER = struct.Struct("<IiiHHIIiiII")


@dataclass(frozen=True)
class Image:
    """Pixels en octets B, G, R, A, rangée par rangée de haut en bas."""

    width: int
    height: int
    bgra: bytes

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        """(R, G, B) du pixel (x, y)."""
        i = (y * self.width + x) * 4
        b, g, r = self.bgra[i : i + 3]
        return r, g, b

    def crop(self, x: int, y: int, width: int, height: int) -> Image:
        """Sous-image bornée à l'image."""
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + width, self.width), min(y + height, self.height)
        w, h = max(x1 - x0, 0), max(y1 - y0, 0)
        rows = [self.bgra[((y0 + row) * self.width + x0) * 4 : ((y0 + row) * self.width + x1) * 4] for row in range(h)]
        return Image(w, h, b"".join(rows))


def solid(width: int, height: int, rgb: tuple[int, int, int]) -> Image:
    """Image d'une seule couleur, opaque."""
    r, g, b = rgb
    return Image(width, height, bytes((b, g, r, 255)) * (width * height))


def read_bmp(path: Path) -> Image:
    """BMP non compressé de 24 ou 32 bits, rangées de bas en haut (hauteur positive) ou de haut en bas (négative)."""
    raw = path.read_bytes()
    magic, _, _, _, offset = _FILE_HEADER.unpack_from(raw, 0)
    _, width, height, _, bits, compression, *_ = _INFO_HEADER.unpack_from(raw, _FILE_HEADER.size)
    if magic != b"BM" or bits not in (24, 32) or compression not in (0, 3):
        raise ValueError(f"{path} : BMP non pris en charge (24 ou 32 bits non compressé attendu)")
    step = bits // 8
    stride = (width * step + 3) & ~3
    top_down = height < 0
    height = abs(height)
    out = bytearray()
    for y in range(height):
        row = y if top_down else height - 1 - y
        start = offset + row * stride
        line = raw[start : start + width * step]
        if step == 4:
            out += line
        else:
            for x in range(width):
                out += line[x * 3 : x * 3 + 3] + b"\xff"
    return Image(width, height, bytes(out))


def write_bmp(image: Image, path: Path, *, bits: int = 32) -> None:
    """BMP non compressé, rangées de bas en haut ; en 24 bits, l'alpha est perdu (relu à 255)."""
    if bits not in (24, 32):
        raise ValueError("BMP de 24 ou 32 bits seulement")
    step = bits // 8
    stride = (image.width * step + 3) & ~3
    pixels = bytearray()
    for y in range(image.height - 1, -1, -1):
        line = image.bgra[y * image.width * 4 : (y + 1) * image.width * 4]
        if step == 3:
            line = b"".join(line[x * 4 : x * 4 + 3] for x in range(image.width))
        pixels += line + b"\x00" * (stride - len(line))
    offset = _FILE_HEADER.size + _INFO_HEADER.size
    info = _INFO_HEADER.pack(_INFO_HEADER.size, image.width, image.height, 1, bits, 0, len(pixels), 2835, 2835, 0, 0)
    header = _FILE_HEADER.pack(b"BM", offset + len(pixels), 0, 0, offset)
    path.write_bytes(header + info + bytes(pixels))
