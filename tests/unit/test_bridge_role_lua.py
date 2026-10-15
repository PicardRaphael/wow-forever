"""Rôle du personnage et bascule de profil EllesmereUI dans ForeverBridge 0.4.0 (EX1, bloc F, décision 267), sous
lupa.lua51 : `/fb role` garde le rôle par personnage et l'envoie dans le contexte ; la bascule appelle
`EllesmereUI.SwitchProfile` hors combat (différée au `PLAYER_REGEN_ENABLED` en combat), seulement si le profil
« <personnage> - <rôle> » existe, jamais si la bascule automatique d'EllesmereUI est active pour le personnage
(EUI2 : signalé une fois, rien fait), sans erreur si EllesmereUI est absent, et sans aucune écriture de
`EllesmereUIDB`. L'API d'EllesmereUI est bouchonnée (noms de fonctions relevés dans EllesmereUI 9.5.4)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import collect, waiting_slots
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

pytest.importorskip("lupa")

ELLESMERE = """
EUI = { calls = {}, active = "Default", order = { "Default", "Jen - DPS" }, spec = nil, writes = {} }
EUI.profiles = { ["Default"] = {}, ["Jen - DPS"] = {}, ["Hunt"] = {} }
EllesmereUI = {}
function EllesmereUI.SwitchProfile(name) EUI.calls[#EUI.calls + 1] = name; EUI.active = name end
function EllesmereUI.GetActiveProfileName() return EUI.active end
function EllesmereUI.GetProfileList() return EUI.order, EUI.profiles end
function EllesmereUI.GetSpecProfile(specID) return EUI.spec end
local function readonly(t)
    local proxy = {}
    return setmetatable(proxy, {
        __index = function(_, k) local v = t[k]; if type(v) == "table" then return readonly(v) end; return v end,
        __newindex = function(_, k) EUI.writes[#EUI.writes + 1] = tostring(k); error("écriture interdite") end,
    })
end
EllesmereUIDB = readonly({ lastSpecByChar = { ["Jen - Forever"] = 9001 }, specProfiles = {}, profiles = EUI.profiles })
"""


def game_with_ellesmere(**kwargs):
    game = Game(prelude=ELLESMERE, **kwargs)
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    game.slash("/fb eui on")  # CJ1 (décision 274) : bascule seulement après /fb eui on
    return game


def calls(game):
    return list(game.lua.globals().EUI.calls.values())


def writes(game):
    return list(game.lua.globals().EUI.writes.values())


def test_role_is_kept_per_character_and_sent_in_the_context():
    game = Game()
    waiting_slots(game)
    game.slash("/fv")
    game.slash("/fb role dps")
    assert game.lua.globals().ForeverBridgeDB.roles["Jen - Forever"] == "dps"
    type_and_enter(game, "Question")
    record, _ = collect(game)
    assert record.context["role"] == "dps"


def test_role_not_held_by_the_class_is_refused():
    game = Game()
    game.slash("/fv")
    game.slash("/fb role tank")
    roles = game.lua.globals().ForeverBridgeDB.roles
    assert roles is None or roles["Jen - Forever"] is None
    assert any("tank" in line and "Mage" in line for line in history(game))


def test_role_without_argument_shows_the_current_one():
    game = Game()
    game.slash("/fv")
    game.slash("/fb role dps")
    game.slash("/fb role")
    assert any("dps" in line for line in history(game)[-2:])


def test_switch_out_of_combat_with_the_profile_name():
    game = game_with_ellesmere()
    game.slash("/fb role dps")
    assert calls(game) == ["Jen - DPS"]
    game.slash("/fb role dps")
    assert calls(game) == ["Jen - DPS"]  # déjà actif : aucun nouvel appel
    assert writes(game) == []


def test_switch_waits_for_the_end_of_combat():
    game = game_with_ellesmere()
    game.stub.combat = True
    game.slash("/fb role dps")
    assert calls(game) == []
    game.stub.combat = False
    game.stub.Fire("PLAYER_REGEN_ENABLED")
    assert calls(game) == ["Jen - DPS"]


def test_missing_profile_is_never_switched_to():
    game = game_with_ellesmere()
    game.lua.execute('EUI.order = { "Default" }; EUI.profiles["Jen - DPS"] = nil')
    game.slash("/fb role dps")
    assert calls(game) == []
    assert any("Jen - DPS" in line and "import" in line for line in history(game))


def test_ellesmere_automatic_switch_wins_and_is_reported_once():
    game = game_with_ellesmere()
    game.lua.execute('EUI.spec = "Hunt"')
    game.slash("/fb role dps")
    game.slash("/fb role dps")
    assert calls(game) == []
    notes = [line for line in history(game) if "automatique" in line and "EllesmereUI" in line]
    assert len(notes) == 1
    assert writes(game) == []


def test_without_ellesmere_nothing_fails():
    game = Game()
    game.slash("/fv")
    game.slash("/fb role dps")
    game.stub.Fire("PLAYER_ENTERING_WORLD", False, True)
    game.stub.Advance(10, 0.5)
    assert game.lua.globals().ForeverBridgeDB.roles["Jen - Forever"] == "dps"


def test_saved_role_switches_after_login_with_a_delay():
    game = Game(prelude=ELLESMERE, saved={"roles": {"Jen - Forever": "dps"}, "eui": True})
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    assert calls(game) == []
    game.stub.Advance(10, 0.5)
    assert calls(game) == ["Jen - DPS"]
    assert writes(game) == []
