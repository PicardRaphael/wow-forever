"""Objet LibDataBroker « Forever » de ForeverBridge 0.4.0 (EX1, bloc G, ROADMAP EX1 point 3), sous lupa.lua51 :
créé seulement si `LibStub("LibDataBroker-1.1", true)` existe (chargé par EllesmereUI ; rien d'embarqué), texte tiré
de l'état publié par le pont (ligne de fraîcheur ; XP par heure et prochain objectif seulement s'ils sont envoyés,
jamais inventés), clic qui ouvre la fenêtre ; sans LibStub, rien et aucune erreur. Bouchons synthétiques."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_reply_lua import STATUS

from forever.bridge.buttons import button_payload, visible_buttons
from forever.bridge.slots import inbox_lua, status_lua

pytest.importorskip("lupa")

LDB = """
LDB_OBJECTS = {}
local ldb = {}
function ldb:NewDataObject(name, obj) LDB_OBJECTS[name] = obj; return obj end
LibStub = setmetatable({}, { __call = function(_, name, silent)
    if name == "LibDataBroker-1.1" then return ldb end
    if not silent then error("bibliothèque absente : " .. tostring(name)) end
end })
"""


def logged_in(prelude=LDB, status=STATUS):
    game = Game(prelude=prelude)
    game.lua.execute(status_lua(status, button_payload(visible_buttons()), 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    return game


def broker(game):
    objects = game.lua.globals().LDB_OBJECTS
    return objects["Forever"] if objects is not None else None


def test_object_is_created_with_the_freshness_line():
    game = logged_in()
    obj = broker(game)
    assert obj is not None and obj.type == "data source" and obj.label == "Forever"
    assert STATUS["line"] in str(obj.text)
    assert "XP" not in str(obj.text)


def test_xp_and_objective_only_when_the_bridge_sends_them():
    status = {**STATUS, "xp_per_hour": "12 345", "next_objective": "Quêtes des Tarides"}
    game = logged_in(status=status)
    text = str(broker(game).text)
    assert "12 345" in text and "Quêtes des Tarides" in text


def test_text_follows_a_new_slot():
    game = logged_in()
    newer = {**STATUS, "line": "Données 1.60.1.99999 · à jour"}
    game.stub.addons["ForeverBridge_S001"] = inbox_lua(1791547300, newer, [], [])
    game.lua.globals().ForeverBridge.PollSlot()
    assert "1.60.1.99999" in str(broker(game).text)


def test_click_opens_the_window():
    game = logged_in()
    obj = broker(game)
    obj.OnClick(game.lua.globals().UIParent, "LeftButton")
    frame = game.lua.globals().ForeverBridgeWindow
    assert frame is not None and frame.IsShown(frame)


def test_without_libstub_nothing_and_no_error():
    game = logged_in(prelude=None)
    assert game.lua.globals().LDB_OBJECTS is None
    game.stub.Advance(2, 0.5)
