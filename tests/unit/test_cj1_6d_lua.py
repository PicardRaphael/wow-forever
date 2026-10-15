"""Essai CJ-6 du 2026-10-15, suite, défaut 2, sous lupa.lua51 : fenêtre agrandie au maximum, impossible à réduire.
La fenêtre ne dépasse jamais l'écran (bornes maximales à la taille de l'écran, taille gardée ramenée à l'écran au
chargement), son coin de redimensionnement reste donc visible ; `/fv reset` et un double-clic sur le titre la
remettent à 640 × 440 au centre.

Client simulé : écran de l'interface de 1024 × 768 (`UIParent`). Aucune règle de jeu."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_window_lua import window

pytest.importorskip("lupa")


def screen(game):
    parent = game.lua.globals().UIParent
    return parent.GetWidth(parent), parent.GetHeight(parent)


def test_window_never_grows_past_the_screen():
    game = Game()
    game.slash("/fv")
    frame = window(game)
    width, height = screen(game)
    assert frame.maxWidth is not None and frame.maxWidth <= width and frame.maxHeight <= height
    frame.SetSize(frame, width * 2, height * 2)  # agrandie au-delà de l'écran par la poignée
    frame.scripts.OnSizeChanged(frame, width * 2, height * 2)
    assert frame.GetWidth(frame) <= width and frame.GetHeight(frame) <= height


def test_oversized_saved_window_is_brought_back_on_screen():
    width, height = 1024, 768
    saved = {"schema": 1, "session": "abcd1234", "next_id": 1,
             "window": {"point": "TOPLEFT", "relPoint": "TOPLEFT", "x": 0, "y": 0, "width": 3 * width, "height": 3 * height}}  # fmt: skip
    game = Game(saved=saved)
    game.slash("/fv")
    frame = window(game)
    assert frame.GetWidth(frame) <= screen(game)[0] and frame.GetHeight(frame) <= screen(game)[1]


def centered_default(game):
    frame = window(game)
    point = frame.points[1]
    return (frame.GetWidth(frame), frame.GetHeight(frame), point.point, point.relPoint, point.x, point.y)


def test_fv_reset_puts_the_window_back_in_the_middle():
    game = Game()
    game.slash("/fv")
    frame = window(game)
    frame.ClearAllPoints(frame)
    frame.SetPoint(frame, "TOPLEFT", game.lua.globals().UIParent, "TOPLEFT", 400, -300)
    frame.SetSize(frame, 1000, 760)
    game.slash("/fv reset")
    assert centered_default(game) == (640, 440, "CENTER", "CENTER", 0, 0)
    state = game.lua.globals().ForeverBridgeDB.window
    assert (state.width, state.height, state.point) == (640, 440, "CENTER")


def test_double_click_on_the_title_resets_the_window():
    game = Game()
    game.slash("/fv")
    frame = window(game)
    frame.SetSize(frame, 1000, 760)
    title = game.lua.globals().ForeverBridgeTitleBar
    assert title is not None and title.IsVisible(title)
    title.scripts.OnDoubleClick(title, "LeftButton")
    assert centered_default(game) == (640, 440, "CENTER", "CENTER", 0, 0)
    assert title.scripts.OnDragStart is not None  # le titre sert toujours à déplacer la fenêtre
