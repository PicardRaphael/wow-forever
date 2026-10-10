"""Panneau d'action unique à droite de la fenêtre (retour de la sonde en jeu H du 2026-10-10, décision 238), sous
lupa.lua51 : cartes « À valider », zone de collage de l'export `/simc` et copie des liens (Talents Forever) dans un
seul panneau collé à la fenêtre, qui défile (molette et barre de défilement du modèle `UIPanelScrollFrameTemplate`) ;
plus aucune petite fenêtre séparée."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import CARD_NETWORK, CARD_UPDATE, with_cards
from test_bridge_window_lua import window

pytest.importorskip("lupa")

LINK = "https://talentsforever.com/mage/20/abc"


def panel(game):
    return game.lua.globals().ForeverBridgePanel


def shown(widget):
    return widget is not None and widget.IsVisible(widget)


def toplevel_names(game):
    lua = game.lua.globals()
    return {
        str(f.name)
        for f in game.stub.frames.values()
        if f.name and game.lua.eval("rawequal")(f.parent, lua.UIParent) and str(f.name).startswith("ForeverBridge")
    }


def test_one_panel_holds_cards_paste_and_copy():
    game = Game()
    game.slash("/fv")
    with_cards(game, [CARD_UPDATE, CARD_NETWORK])
    lua = game.lua.globals()
    lua.ForeverBridgeCardsButton.scripts.OnClick(lua.ForeverBridgeCardsButton)
    p = panel(game)
    assert shown(p)
    point = p.points[1]
    assert game.lua.eval("rawequal")(point.rel, window(game)) and (point.point, point.relPoint) == (
        "TOPLEFT",
        "TOPRIGHT",
    )
    lua.ForeverBridge.OpenPaste()
    lua.ForeverBridge.ShowCopy(LINK)
    for name in ("ForeverBridgeCard1Text", "ForeverBridgePasteBox", "ForeverBridgePasteSend", "ForeverBridgeCopyBox"):
        assert shown(lua[name]), name
    assert lua.ForeverBridgeCopyBox.GetText(lua.ForeverBridgeCopyBox) == LINK
    assert not {"ForeverBridgePaste", "ForeverBridgeCopy", "ForeverBridgeCards"} & toplevel_names(game)


def test_panel_scrolls_with_the_wheel_and_has_a_scroll_bar():
    game = Game()
    game.slash("/fv")
    many = [{**CARD_UPDATE, "id": f"c{i}", "lines": ["ligne"] * 6} for i in range(8)]
    with_cards(game, many)
    lua = game.lua.globals()
    lua.ForeverBridgeCardsButton.scripts.OnClick(lua.ForeverBridgeCardsButton)
    scroll = lua.ForeverBridgePanelScroll
    assert scroll.template == "UIPanelScrollFrameTemplate" and scroll.wheel
    assert scroll.GetVerticalScrollRange(scroll) > 0
    assert scroll.GetVerticalScroll(scroll) == 0
    scroll.scripts.OnMouseWheel(scroll, -1)
    assert scroll.GetVerticalScroll(scroll) > 0
    for _ in range(100):
        scroll.scripts.OnMouseWheel(scroll, -1)
    assert scroll.GetVerticalScroll(scroll) == scroll.GetVerticalScrollRange(scroll)
    for _ in range(100):
        scroll.scripts.OnMouseWheel(scroll, 1)
    assert scroll.GetVerticalScroll(scroll) == 0


def test_escape_closes_the_panel_and_the_opener_toggles_it():
    game = Game()
    game.slash("/fv")
    lua = game.lua.globals()
    lua.ForeverBridge.OpenPaste()
    assert "ForeverBridgePanel" in list(lua.UISpecialFrames.values())
    opener = lua.ForeverBridgePasteButton
    opener.scripts.OnClick(opener)
    assert not shown(panel(game))
    opener.scripts.OnClick(opener)
    assert shown(panel(game)) and shown(lua.ForeverBridgePasteBox)
