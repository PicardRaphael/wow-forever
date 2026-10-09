"""Fenêtre dédiée, bande d'une case par pixel et sonde `/fv poll` de ForeverBridge (P06a, bloc A2, décision 212
amendée le 2026-10-09), sous lupa.lua51 avec le client simulé. Rien dans la discussion générale hors `/fv diag`."""

import pytest
from conftest import REPO_ROOT
from test_bridge_addon_lua import ALL_FILES, Game

from forever.bridge.codec import SELFTEST_ID, Decoded, decode_band, detect_cell_px, selftest_payload

pytest.importorskip("lupa")

ADDON = REPO_ROOT / "addon" / "ForeverBridge"


def window(game):
    return game.lua.globals().ForeverBridgeWindow


def history(game) -> list[str]:
    frame = game.lua.globals().ForeverBridgeHistory
    if frame is None:
        return []
    return [str(line) for line in frame.messages.values()]


def test_window_is_closed_at_login_and_toggled_by_fv():
    game = Game(saved={"schema": 1, "session": "abcd1234", "next_id": 1, "window": {"point": "CENTER"}})
    frame = window(game)
    assert frame is None or not frame.IsShown(frame)
    game.slash("/fv")
    frame = window(game)
    assert frame.IsShown(frame)
    assert any("/fv test" in line for line in history(game))
    game.slash("/fv")
    assert not frame.IsShown(frame)
    game.slash("/forever")
    assert frame.IsShown(frame)


def test_escape_closes_the_window_and_strata_is_dialog():
    game = Game()
    game.slash("/fv")
    names = list(game.lua.globals().UISpecialFrames.values())
    assert "ForeverBridgeWindow" in names
    frame = window(game)
    assert frame.GetFrameStrata(frame) == "DIALOG"
    assert frame.movable and frame.resizable and frame.clamped


def test_window_geometry_is_saved_and_restored():
    game = Game()
    game.slash("/fv")
    frame = window(game)
    frame.ClearAllPoints(frame)
    frame.SetPoint(frame, "TOPLEFT", game.lua.globals().UIParent, "TOPLEFT", 120, -80)
    frame.SetSize(frame, 610, 420)
    frame.scripts.OnDragStop(frame)
    saved = game.lua.globals().ForeverBridgeDB.window
    assert (saved.point, saved.relPoint, saved.x, saved.y) == ("TOPLEFT", "TOPLEFT", 120, -80)
    assert (saved.width, saved.height) == (610, 420)

    again = Game(
        saved={
            "schema": 1,
            "session": "abcd1234",
            "next_id": 1,
            "window": {"point": "TOPLEFT", "relPoint": "TOPLEFT", "x": 120, "y": -80, "width": 610, "height": 420},
        }
    )
    again.slash("/fv")
    frame = window(again)
    point = frame.points[1]
    assert (point.point, point.relPoint, point.x, point.y) == ("TOPLEFT", "TOPLEFT", 120, -80)
    assert (frame.GetWidth(frame), frame.GetHeight(frame)) == (610, 420)


def test_key_binding_is_declared():
    game = Game()
    lua = game.lua.globals()
    assert lua.BINDING_HEADER_FOREVERBRIDGE == "ForeverBridge"
    assert isinstance(lua.BINDING_NAME_FOREVERBRIDGE_TOGGLE, str)
    xml = (ADDON / "Bindings.xml").read_text(encoding="utf-8")
    assert 'name="FOREVERBRIDGE_TOGGLE"' in xml and "ForeverBridge.Toggle()" in xml
    lua.ForeverBridge.Toggle()
    assert window(game).IsShown(window(game))


@pytest.mark.parametrize(("command", "cell_px"), [("/fv test", 1), ("/fv test 2", 2), ("/fv test 4", 4)])
def test_selftest_band_cell_size(command, cell_px):
    game = Game(screen=(2560, 1440))
    game.slash(command)
    image = game.screen_image()
    assert detect_cell_px(image) == cell_px
    assert decode_band(image) == Decoded(SELFTEST_ID, selftest_payload())


def test_band_redrawn_at_another_size_then_removed():
    game = Game()
    game.slash("/fv test")
    game.slash("/fv test 3")
    assert detect_cell_px(game.screen_image()) == 3
    game.slash("/fv test")
    assert decode_band(game.screen_image()) is None


def test_nothing_in_the_general_chat_except_diag():
    game = Game(files=ALL_FILES, probe="installation")
    game.stub.addons["ForeverBridge_Probe2"] = 'ForeverBridge_Probe2Value = "modifié à 08:13:00"\n'
    for line in ("/fv", "/fv test", "/fv test", "/fv poll", "/fv aide", "/fv"):
        game.slash(line)
    game.stub.Advance(5)
    assert list(game.stub.printed.values()) == []
    game.slash("/fv diag")
    assert any("autotest .wav" in str(line) for line in game.stub.printed.values())


def test_fv_poll_loads_the_second_probe_once():
    game = Game()
    game.stub.addons["ForeverBridge_Probe2"] = 'ForeverBridge_Probe2Value = "modifié à 08:13:00"\n'
    game.slash("/fv poll")
    assert window(game).IsShown(window(game))
    assert any("ForeverBridge_Probe2 : chargé, valeur « modifié à 08:13:00 »" in line for line in history(game))
    game.slash("/fv poll")
    assert any("ForeverBridge_Probe2 : déjà chargé" in line for line in history(game))


def test_fv_poll_without_the_probe():
    game = Game()
    game.slash("/fv poll")
    assert any("ForeverBridge_Probe2 : non chargé (MISSING)" in line for line in history(game))


def test_diag_says_the_sound_channel_is_unusable_on_forever():
    game = Game(files={**ALL_FILES, "valid.ogg": "valid", "flip.ogg": "empty"})
    game.slash("/fv diag")
    text = "\n".join(str(line) for line in game.stub.printed.values())
    assert "canal son inutilisable" in text


def test_no_forbidden_call_with_the_window():
    game = Game()
    for line in ("/fv", "/fv test", "/fv poll", "/fv"):
        game.slash(line)
    window(game).scripts.OnDragStop(window(game))
    assert list(game.stub.forbidden.values()) == []
