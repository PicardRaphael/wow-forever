"""Capture de la bande dans la fenêtre du jeu (P06a, bloc A, décision 212) : fenêtre trouvée par les exécutables du
client, rectangle pris dans sa zone client (coin haut gauche), lu depuis l'écran **seulement si la fenêtre du jeu est
au premier plan et non réduite** (sinon une fenêtre posée par-dessus serait lue). Sonde du marqueur (20 × 4 pixels),
bande entière (800 × 96 pixels au plus) seulement quand la sonde reconnaît le marqueur. Rien n'est gardé ni écrit.

API de Windows par `ctypes` (aucune dépendance) ; hors de Windows, le module s'importe mais `win32_api()` lève.
Mode fenêtré ou plein écran fenêtré requis (le plein écran exclusif rend une capture noire, d'après wow-ai).

Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : logique de
`bridge/capture.ps1`), sous la licence suivante :

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

from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol

from forever.bridge.image import Image


@dataclass(frozen=True)
class Rect:
    """Rectangle en pixels physiques de l'écran."""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class GameWindow:
    hwnd: int
    pid: int
    executable: str
    title: str


class WinApi(Protocol):
    """Fonctions de Windows dont la capture a besoin (injectées dans les tests)."""

    def game_windows(self, executables: Collection[str]) -> list[GameWindow]: ...
    def foreground(self) -> int | None: ...
    def is_iconic(self, hwnd: int) -> bool: ...
    def client_rect(self, hwnd: int) -> Rect | None: ...
    def blit(self, rect: Rect) -> Image | None: ...


def probe_rect(client: Rect) -> Rect | None:
    """Rectangle de la sonde (cinq premières cellules) ; None si la zone client est plus petite que la sonde."""
    raise NotImplementedError


def band_rect(client: Rect) -> Rect | None:
    """Rectangle de la bande entière, borné à la zone client ; None si la sonde n'y tient pas."""
    raise NotImplementedError


def may_capture(game_hwnd: int | None, foreground_hwnd: int | None, iconic: bool) -> bool:
    """Capture permise : fenêtre du jeu trouvée, au premier plan, non réduite."""
    raise NotImplementedError


class WindowsCapture:
    """Capture limitée à la fenêtre du jeu ; `grab` refuse tout rectangle hors de la zone client, plus grand que la
    bande, ou quand le jeu n'est pas au premier plan."""

    def __init__(self, executables: Collection[str], api: WinApi) -> None:
        raise NotImplementedError

    def find(self) -> GameWindow | None:
        raise NotImplementedError

    def client(self) -> Rect | None:
        """Zone client de la fenêtre trouvée (coordonnées de l'écran)."""
        raise NotImplementedError

    def allowed(self) -> bool:
        raise NotImplementedError

    def grab(self, rect: Rect) -> Image | None:
        raise NotImplementedError


def win32_api() -> WinApi:
    """API réelle de Windows (processus marqué « DPI aware ») ; RuntimeError hors de Windows."""
    raise NotImplementedError
