"""Livraison en jeu d'un guide RestedXP (RX1, bloc D, ForeverBridge 0.3.0) : un emplacement publié par le pont porte
`guide = {name, group, text, sha}` ; le Lua l'importe hors combat par `RXPGuides.ImportGuide` sous `pcall`, demande
la régénération du menu (`RXP:ScheduleTask`) s'il le peut, garde l'issue dans `ForeverBridgeDB.guides[sha]` et
l'écrit dans la fenêtre. Vrai Lua sous lupa.lua51, client simulé `tests/fixtures/bridge/wow_stub.lua` ; faux
RestedXP écrit ici (aucun code de RestedXP)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_window_lua import history

from forever.bridge.slots import inbox_lua

pytest.importorskip("lupa")

NOW = 1791547200
GUIDE = {
    "name": "Fixture Route",
    "group": "Forever Routes",
    "text": "#forever\n#name Fixture Route\nstep\n",
    "sha": "abc123",
}
FAKE_RXP = """
rxp_calls = {}
rxp_tasks = 0
RXPGuides = {
    ImportGuide = function(text)
        rxp_calls[#rxp_calls + 1] = text
        if rxp_fail then error("guide refusé") end
        return { name = "Fixture Route" }
    end,
}
RXP = { RXPFrame = { GenerateMenuTable = function() end } }
function RXP.ScheduleTask(self, task)
    if self == RXP and task == RXP.RXPFrame.GenerateMenuTable then rxp_tasks = rxp_tasks + 1 end
end
"""


def deliver(game, guide=GUIDE, index=1):
    game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(NOW, {"slots": 40}, [], [], guide=guide)
    game.lua.globals().ForeverBridge.PollSlot()


def calls(game):
    got = game.lua.globals().rxp_calls
    return [got[i] for i in range(1, len(got) + 1)] if got is not None else []


def status(game, sha=GUIDE["sha"]):
    guides = game.lua.globals().ForeverBridgeDB.guides
    return guides[sha] if guides is not None else None


def test_inbox_carries_the_guide():
    text = inbox_lua(NOW, {}, [], [], guide=GUIDE)
    assert "guide = {" in text and 'sha = "abc123"' in text
    assert "guide" not in inbox_lua(NOW, {}, [], [])


def test_import_guide_called_under_pcall():
    game = Game(prelude=FAKE_RXP)
    deliver(game)
    assert calls(game) == [GUIDE["text"]]
    assert int(game.lua.globals().rxp_tasks) == 1
    assert status(game) == "livré"
    assert any("livré" in line and GUIDE["name"] in line for line in game.printed() + history(game))


def test_same_guide_imported_once():
    game = Game(prelude=FAKE_RXP)
    deliver(game, index=1)
    deliver(game, index=2)
    assert calls(game) == [GUIDE["text"]]


def test_import_guide_absent():
    game = Game()
    deliver(game)
    assert status(game) == "absent"
    assert any("RestedXP absent" in line for line in game.printed() + history(game))


def test_import_error_reported():
    game = Game(prelude=FAKE_RXP + "\nrxp_fail = true\n")
    deliver(game)
    assert status(game) == "erreur"
    assert int(game.lua.globals().rxp_tasks) == 0


def test_import_deferred_in_combat():
    game = Game(prelude=FAKE_RXP)
    game.stub.combat = True
    deliver(game)
    assert calls(game) == [] and status(game) is None
    game.stub.combat = False
    game.stub.Fire("PLAYER_REGEN_ENABLED")
    assert calls(game) == [GUIDE["text"]] and status(game) == "livré"


def test_unpublished_slot_never_imports():
    game = Game(prelude=FAKE_RXP)
    game.stub.addons["ForeverBridge_S001"] = inbox_lua(0, {}, [], [], guide=GUIDE)
    game.lua.globals().ForeverBridge.PollSlot()
    assert calls(game) == []
