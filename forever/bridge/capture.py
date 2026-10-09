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

import struct
import sys
from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol

from forever.bridge.codec import BAND_HEIGHT, BAND_WIDTH, CELL_PX, PROBE_HEIGHT, PROBE_WIDTH
from forever.bridge.image import Image

_PER_MONITOR_AWARE_V2 = -4
_QUERY_LIMITED_INFORMATION = 0x1000
_GW_OWNER = 4
_SRCCOPY = 0x00CC0020


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
    if client.width < PROBE_WIDTH or client.height < PROBE_HEIGHT:
        return None
    return Rect(client.left, client.top, PROBE_WIDTH, PROBE_HEIGHT)


def band_rect(client: Rect, cell_px: int = CELL_PX) -> Rect | None:
    """Rectangle de la bande entière à cette taille de case, borné à la zone client ; None si la sonde n'y tient
    pas."""
    if probe_rect(client) is None:
        return None
    width, height = BAND_WIDTH * cell_px // CELL_PX, BAND_HEIGHT * cell_px // CELL_PX
    return Rect(client.left, client.top, min(width, client.width), min(height, client.height))


def may_capture(game_hwnd: int | None, foreground_hwnd: int | None, iconic: bool) -> bool:
    """Capture permise : fenêtre du jeu trouvée, au premier plan, non réduite."""
    return game_hwnd is not None and foreground_hwnd == game_hwnd and not iconic


def _inside(rect: Rect, outer: Rect) -> bool:
    return (
        rect.width > 0
        and rect.height > 0
        and rect.left >= outer.left
        and rect.top >= outer.top
        and rect.left + rect.width <= outer.left + outer.width
        and rect.top + rect.height <= outer.top + outer.height
    )


class WindowsCapture:
    """Capture limitée à la fenêtre du jeu ; `grab` refuse tout rectangle hors de la zone client, plus grand que la
    bande, ou quand le jeu n'est pas au premier plan."""

    def __init__(self, executables: Collection[str], api: WinApi) -> None:
        self._executables = {name.lower() for name in executables}
        self._api = api
        self.window: GameWindow | None = None

    def find(self) -> GameWindow | None:
        def area(window: GameWindow) -> int:
            rect = self._api.client_rect(window.hwnd)
            return rect.width * rect.height if rect is not None else 0

        # la fenêtre principale du jeu : la plus grande zone client parmi les fenêtres de ses exécutables
        windows = sorted(self._api.game_windows(self._executables), key=area, reverse=True)
        self.window = windows[0] if windows else None
        return self.window

    def client(self) -> Rect | None:
        """Zone client de la fenêtre trouvée (coordonnées de l'écran)."""
        return self._api.client_rect(self.window.hwnd) if self.window is not None else None

    def allowed(self) -> bool:
        if self.window is None:
            return False
        hwnd = self.window.hwnd
        return may_capture(hwnd, self._api.foreground(), self._api.is_iconic(hwnd))

    def grab(self, rect: Rect) -> Image | None:
        if not self.allowed():
            return None
        client = self.client()
        band = band_rect(client) if client is not None else None
        if band is None or not _inside(rect, band):
            return None
        return self._api.blit(rect)


class _Win32Api:
    """Appels à user32, gdi32 et kernel32 ; coordonnées physiques (processus « DPI aware »)."""

    def __init__(self) -> None:
        assert sys.platform == "win32"
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._wintypes = wintypes
        win_dll = getattr(ctypes, "WinDLL")  # noqa: B009 : absent hors de Windows (typage sous Linux)
        user32 = win_dll("user32", use_last_error=True)
        gdi32 = win_dll("gdi32", use_last_error=True)
        kernel32 = win_dll("kernel32", use_last_error=True)
        self._user32, self._gdi32, self._kernel32 = user32, gdi32, kernel32
        handle = ctypes.c_void_p
        signatures: list[tuple[object, str, list[object], object]] = [
            (user32, "GetForegroundWindow", [], handle),
            (user32, "IsIconic", [handle], wintypes.BOOL),
            (user32, "IsWindowVisible", [handle], wintypes.BOOL),
            (user32, "GetWindow", [handle, wintypes.UINT], handle),
            (user32, "GetWindowThreadProcessId", [handle, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            (user32, "GetWindowTextW", [handle, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            (user32, "GetClientRect", [handle, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            (user32, "ClientToScreen", [handle, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            (user32, "GetDC", [handle], handle),
            (user32, "ReleaseDC", [handle, handle], ctypes.c_int),
            (gdi32, "CreateCompatibleDC", [handle], handle),
            (gdi32, "CreateCompatibleBitmap", [handle, ctypes.c_int, ctypes.c_int], handle),
            (gdi32, "SelectObject", [handle, handle], handle),
            (
                gdi32,
                "BitBlt",
                [
                    handle,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    handle,
                    ctypes.c_int,
                    ctypes.c_int,
                    wintypes.DWORD,
                ],
                wintypes.BOOL,
            ),
            (
                gdi32,
                "GetDIBits",
                [handle, handle, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT],
                ctypes.c_int,
            ),
            (gdi32, "DeleteObject", [handle], wintypes.BOOL),
            (gdi32, "DeleteDC", [handle], wintypes.BOOL),
            (kernel32, "OpenProcess", [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], handle),
            (
                kernel32,
                "QueryFullProcessImageNameW",
                [handle, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)],
                wintypes.BOOL,
            ),
            (kernel32, "CloseHandle", [handle], wintypes.BOOL),
        ]
        for library, name, args, result in signatures:
            fn = getattr(library, name)
            fn.argtypes, fn.restype = args, result
        self._enum_proc = getattr(ctypes, "WINFUNCTYPE")(wintypes.BOOL, handle, wintypes.LPARAM)  # noqa: B009
        user32.EnumWindows.argtypes = [self._enum_proc, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL
        try:  # coordonnées physiques même sous une mise à l'échelle de Windows
            user32.SetProcessDpiAwarenessContext.argtypes = [handle]
            user32.SetProcessDpiAwarenessContext(handle(_PER_MONITOR_AWARE_V2))
        except (AttributeError, OSError):
            user32.SetProcessDPIAware()

    def _executable(self, pid: int) -> str | None:
        process = self._kernel32.OpenProcess(_QUERY_LIMITED_INFORMATION, False, pid)
        if not process:
            return None
        try:
            size = self._wintypes.DWORD(1024)
            buffer = self._ctypes.create_unicode_buffer(size.value)
            if not self._kernel32.QueryFullProcessImageNameW(process, 0, buffer, self._ctypes.byref(size)):
                return None
            return str(buffer.value).replace("\\", "/").rsplit("/", 1)[-1]
        finally:
            self._kernel32.CloseHandle(process)

    def game_windows(self, executables: Collection[str]) -> list[GameWindow]:
        wanted = {name.lower() for name in executables}
        found: list[GameWindow] = []

        def visit(hwnd: int | None, _: int) -> bool:
            if not hwnd or not self._user32.IsWindowVisible(hwnd) or self._user32.GetWindow(hwnd, _GW_OWNER):
                return True
            pid = self._wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, self._ctypes.byref(pid))
            exe = self._executable(pid.value)
            if exe is not None and exe.lower() in wanted:
                title = self._ctypes.create_unicode_buffer(256)
                self._user32.GetWindowTextW(hwnd, title, 256)
                found.append(GameWindow(int(hwnd), int(pid.value), exe, str(title.value)))
            return True

        self._user32.EnumWindows(self._enum_proc(visit), 0)
        return found

    def foreground(self) -> int | None:
        hwnd = self._user32.GetForegroundWindow()
        return int(hwnd) if hwnd else None

    def is_iconic(self, hwnd: int) -> bool:
        return bool(self._user32.IsIconic(hwnd))

    def client_rect(self, hwnd: int) -> Rect | None:
        rect = self._wintypes.RECT()
        if not self._user32.GetClientRect(hwnd, self._ctypes.byref(rect)):
            return None
        origin = self._wintypes.POINT(0, 0)
        if not self._user32.ClientToScreen(hwnd, self._ctypes.byref(origin)):
            return None
        return Rect(origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top)

    def blit(self, rect: Rect) -> Image | None:
        ctypes = self._ctypes
        screen = self._user32.GetDC(None)
        if not screen:
            return None
        memory = self._gdi32.CreateCompatibleDC(screen)
        bitmap = self._gdi32.CreateCompatibleBitmap(screen, rect.width, rect.height)
        old = self._gdi32.SelectObject(memory, bitmap)
        try:
            if not self._gdi32.BitBlt(memory, 0, 0, rect.width, rect.height, screen, rect.left, rect.top, _SRCCOPY):
                return None
            # BITMAPINFOHEADER : hauteur négative (rangées de haut en bas), 32 bits par pixel, BI_RGB
            header = struct.pack("<IiiHHIIiiII", 40, rect.width, -rect.height, 1, 32, 0, 0, 0, 0, 0, 0)
            info = ctypes.create_string_buffer(header + bytes(16))
            pixels = ctypes.create_string_buffer(rect.width * rect.height * 4)
            if self._gdi32.GetDIBits(memory, bitmap, 0, rect.height, pixels, info, 0) != rect.height:
                return None
            raw = bytearray(pixels.raw)
            raw[3::4] = b"\xff" * (rect.width * rect.height)
            return Image(rect.width, rect.height, bytes(raw))
        finally:
            self._gdi32.SelectObject(memory, old)
            self._gdi32.DeleteObject(bitmap)
            self._gdi32.DeleteDC(memory)
            self._user32.ReleaseDC(None, screen)


def win32_api() -> WinApi:
    """API réelle de Windows (processus marqué « DPI aware ») ; RuntimeError hors de Windows."""
    if sys.platform != "win32":
        raise RuntimeError("capture de la bande : Windows seulement (P06a)")
    return _Win32Api()
