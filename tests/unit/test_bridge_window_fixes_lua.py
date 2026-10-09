"""Retours de la sonde en jeu B du 2026-10-09 (P06a) : aide affichée une seule fois, fond opaque par défaut et réglable
(`/fv fond N`), `/fv diag` qui confirme son passage dans la fenêtre et y montre une erreur Lua au lieu de se taire ;
capture réelle d'une bande d'une case par pixel en non-régression."""

import pytest
from conftest import FIXTURES
from test_bridge_addon_lua import ALL_FILES, Game
from test_bridge_selftest import selftest_cells
from test_bridge_window_lua import history, window

from forever.bridge.codec import SELFTEST_ID, Decoded, cell_mismatches, decode_band, detect_cell_px, selftest_payload
from forever.bridge.image import read_bmp

pytest.importorskip("lupa")

HELP_FIRST = "/fv : ouvrir ou fermer cette fenêtre"


def test_live_capture_at_one_pixel_per_cell_still_decodes():
    """Capture réelle de la sonde en jeu B (2026-10-09, 2 560 × 1 440, une case par pixel)."""
    image = read_bmp(FIXTURES / "bridge" / "band_live_1px.bmp")
    assert (image.width, image.height) == (200, 24)
    assert detect_cell_px(image) == 1
    assert decode_band(image) == Decoded(SELFTEST_ID, selftest_payload())
    assert cell_mismatches(image, selftest_cells()) == []


def test_help_is_shown_once():
    game = Game()
    for line in ("/fv", "/fv", "/fv", "/fv aide", "/fv aide"):
        game.slash(line)
    assert sum(HELP_FIRST in line for line in history(game)) == 1
    game.slash("/fv test")
    game.slash("/fv aide")
    assert sum(HELP_FIRST in line for line in history(game)) == 2


def test_background_is_opaque_by_default_and_adjustable():
    game = Game()
    game.slash("/fv")
    frame = window(game)
    assert frame.backdropColor[4] == 1
    game.slash("/fv fond 60")
    assert frame.backdropColor[4] == pytest.approx(0.6)
    assert game.lua.globals().ForeverBridgeDB.window.alpha == pytest.approx(0.6)
    game.slash("/fv fond 5")
    assert frame.backdropColor[4] == pytest.approx(0.6)
    assert any("fond" in line and "30" in line and "100" in line for line in history(game))

    again = Game(saved={"schema": 1, "session": "abcd1234", "next_id": 1, "window": {"alpha": 0.75}})
    again.slash("/fv")
    assert window(again).backdropColor[4] == pytest.approx(0.75)


def test_diag_confirms_in_the_window():
    game = Game(files=ALL_FILES)
    game.slash("/fv diag")
    assert any("autotest .wav" in str(line) for line in game.stub.printed.values())
    assert any("/fv diag" in line and "discussion générale" in line for line in history(game))


def test_diag_error_is_shown_instead_of_silence():
    game = Game(files=ALL_FILES)
    game.lua.execute('GetPhysicalScreenSize = function() error("panne simulée") end')
    game.slash("/fv diag")
    assert any("/fv diag en erreur" in line and "panne simulée" in line for line in history(game))
    assert any("/fv diag en erreur" in str(line) for line in game.stub.printed.values())
