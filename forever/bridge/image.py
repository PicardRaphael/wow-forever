"""Image BGRA minimale et fichiers BMP 24 et 32 bits (captures de la bande, fixtures), sans Pillow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Image:
    """Pixels en octets B, G, R, A, rangée par rangée de haut en bas."""

    width: int
    height: int
    bgra: bytes

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        """(R, G, B) du pixel (x, y)."""
        raise NotImplementedError

    def crop(self, x: int, y: int, width: int, height: int) -> Image:
        """Sous-image bornée à l'image."""
        raise NotImplementedError


def solid(width: int, height: int, rgb: tuple[int, int, int]) -> Image:
    """Image d'une seule couleur, opaque."""
    raise NotImplementedError


def read_bmp(path: Path) -> Image:
    raise NotImplementedError


def write_bmp(image: Image, path: Path, *, bits: int = 32) -> None:
    raise NotImplementedError
