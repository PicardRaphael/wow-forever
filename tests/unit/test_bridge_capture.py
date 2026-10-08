"""Capture de la bande (P06a, bloc A) : rectangles dans la zone client, capture permise seulement quand le jeu est au
premier plan et non réduit, `grab` qui refuse tout rectangle hors de la zone client ou plus grand que la bande.
Fenêtres et écran simulés : aucun appel à Windows."""

import sys

import pytest

from forever.bridge.capture import GameWindow, Rect, WindowsCapture, band_rect, may_capture, probe_rect, win32_api
from forever.bridge.image import Image, solid

CLIENT = Rect(100, 50, 1920, 1080)


def test_rectangles_in_the_client_area():
    assert band_rect(CLIENT) == Rect(100, 50, 800, 96)
    assert probe_rect(CLIENT) == Rect(100, 50, 20, 4)
    small = Rect(-1280, 10, 640, 80)
    assert band_rect(small) == Rect(-1280, 10, 640, 80)
    assert probe_rect(small) == Rect(-1280, 10, 20, 4)
    assert probe_rect(Rect(0, 0, 16, 4)) is None
    assert band_rect(Rect(0, 0, 16, 4)) is None
    assert probe_rect(Rect(0, 0, 20, 3)) is None


def test_may_capture():
    assert may_capture(7, 7, False)
    assert not may_capture(7, 9, False)
    assert not may_capture(7, 7, True)
    assert not may_capture(None, 7, False)
    assert not may_capture(7, None, False)


class FakeApi:
    """Une fenêtre du jeu (hwnd 7) dont la zone client est CLIENT ; écran uni."""

    def __init__(self, *, foreground=7, iconic=False, windows=None):
        self.foreground_hwnd = foreground
        self.iconic = iconic
        self.windows = windows if windows is not None else [GameWindow(7, 4242, "WowB.exe", "World of Warcraft")]
        self.blits: list[Rect] = []

    def game_windows(self, executables):
        return [w for w in self.windows if w.executable.lower() in {e.lower() for e in executables}]

    def foreground(self):
        return self.foreground_hwnd

    def is_iconic(self, hwnd):
        return self.iconic

    def client_rect(self, hwnd):
        return CLIENT if hwnd == 7 else None

    def blit(self, rect) -> Image:
        self.blits.append(rect)
        return solid(rect.width, rect.height, (0, 0, 0))


def test_find_uses_the_client_executables():
    api = FakeApi(windows=[GameWindow(3, 1, "notepad.exe", "Bloc-notes"), GameWindow(7, 4242, "WowB.exe", "WoW")])
    capture = WindowsCapture({"WowB.exe"}, api)
    assert capture.find() == GameWindow(7, 4242, "WowB.exe", "WoW")
    assert capture.client() == CLIENT
    assert WindowsCapture({"Wow.exe"}, FakeApi()).find() is None


def test_grab_inside_the_client_area_when_in_front():
    api = FakeApi()
    capture = WindowsCapture({"WowB.exe"}, api)
    capture.find()
    image = capture.grab(Rect(100, 50, 20, 4))
    assert image is not None and (image.width, image.height) == (20, 4)
    assert api.blits == [Rect(100, 50, 20, 4)]


@pytest.mark.parametrize(
    "rect",
    [
        Rect(100, 50, 801, 96),  # plus large que la bande
        Rect(100, 50, 800, 97),  # plus haute que la bande
        Rect(99, 50, 20, 4),  # déborde à gauche de la zone client
        Rect(100, 49, 20, 4),  # déborde au-dessus
        Rect(2010, 1120, 20, 20),  # déborde à droite et en bas
    ],
)
def test_grab_refuses_rectangles_outside_the_band(rect):
    api = FakeApi()
    capture = WindowsCapture({"WowB.exe"}, api)
    capture.find()
    assert capture.grab(rect) is None
    assert api.blits == []


@pytest.mark.parametrize("api", [FakeApi(foreground=9), FakeApi(iconic=True), FakeApi(foreground=None)])
def test_grab_refuses_when_the_game_is_not_in_front(api):
    capture = WindowsCapture({"WowB.exe"}, api)
    capture.find()
    assert not capture.allowed()
    assert capture.grab(Rect(100, 50, 20, 4)) is None
    assert api.blits == []


def test_grab_without_window_reads_nothing():
    api = FakeApi(windows=[])
    capture = WindowsCapture({"WowB.exe"}, api)
    assert capture.find() is None
    assert capture.grab(Rect(100, 50, 20, 4)) is None
    assert api.blits == []


@pytest.mark.skipif(sys.platform == "win32", reason="hors de Windows seulement")
def test_win32_api_refused_off_windows():
    with pytest.raises(RuntimeError):
        win32_api()
