"""ForeverBridge en P06b, bloc F (décision 235), sous lupa.lua51 : onglets « Jeu » et « Addons » (Addons seulement
quand le pont publie une conversation « addons » configurée), historiques séparés, message de l'onglet Addons avec
le drapeau `c=addons`, relevés prolongés jusqu'à 610 s pour cette conversation (délai de 600 s)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import collect, waiting_slots
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

from forever.bridge.slots import inbox_lua, status_lua

pytest.importorskip("lupa")

STATUS = {"line": "Données", "slots": 200}
ADDONS = {**STATUS, "addons": {"configured": True, "name": "RaphCompletionist"}}


def tab(game, name):
    return game.lua.globals()[f"ForeverBridgeTab{name}"]


def shown(widget):
    return widget is not None and widget.IsShown(widget)


def with_status(status):
    game = Game()
    game.lua.execute(status_lua(status, [], 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    return game


def test_addons_tab_only_when_configured():
    assert not shown(tab(with_status(STATUS), "Addons"))
    game = with_status(ADDONS)
    assert shown(tab(game, "Game")) and shown(tab(game, "Addons"))
    assert "RaphCompletionist" in tab(game, "Addons").GetText(tab(game, "Addons"))


def test_addons_messages_carry_their_flag_and_their_own_history():
    game = with_status(ADDONS)
    waiting_slots(game, 60)
    type_and_enter(game, "Question du jeu")
    collect(game)
    click = tab(game, "Addons").scripts.OnClick
    click(tab(game, "Addons"))
    assert not any("Question du jeu" in line for line in history(game))
    game.stub.Advance(1.0)
    type_and_enter(game, "Corrige le chargement de RaphCompletionist")
    record, _ = collect(game)
    assert record.flags == frozenset({"c=addons"})
    db = game.lua.globals().ForeverBridgeDB
    assert db.history_addons[1].text == "Corrige le chargement de RaphCompletionist"
    assert db.history[1].text == "Question du jeu"
    tab(game, "Game").scripts.OnClick(tab(game, "Game"))
    assert any("Question du jeu" in line for line in history(game))
    assert not any("RaphCompletionist" in line and "Vous" in line for line in history(game))


def test_addons_reply_lands_in_the_addons_history():
    game = with_status(ADDONS)
    tab(game, "Addons").scripts.OnClick(tab(game, "Addons"))
    session = game.lua.globals().ForeverBridgeDB.session
    done = {"session": session, "id": 1, "status": "done", "text": "Corrigé. Tapez /reload pour essayer."}
    for index in range(1, 61):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(1791547200, ADDONS, [done], [])
    type_and_enter(game, "Corrige")
    game.stub.Advance(5, 0.1)
    assert any("Tapez /reload pour essayer" in line for line in history(game))
    db = game.lua.globals().ForeverBridgeDB
    assert db.history_addons[2].text == "Corrigé. Tapez /reload pour essayer."
    assert len(db.history or {}) == 0


def test_addons_polls_go_on_until_610_seconds():
    game = with_status(ADDONS)
    session = game.lua.globals().ForeverBridgeDB.session
    working = {"session": session, "id": 1, "status": "working", "since": 0}
    for index in range(1, 80):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(1791547200, ADDONS, [working], [])
    tab(game, "Addons").scripts.OnClick(tab(game, "Addons"))
    type_and_enter(game, "Corrige")
    game.stub.Advance(640, 1.0)
    times = [round(float(e[2])) for e in game.stub.loadlog.values() if str(e[1]).startswith("ForeverBridge_S")]
    assert times[-1] == 610 and 190 in times and 220 in times
    assert any("toujours en cours" in line for line in history(game))
