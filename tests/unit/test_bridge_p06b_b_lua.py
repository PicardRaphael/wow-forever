"""ForeverBridge en P06b, bloc B (décision 235), sous lupa.lua51 : bouton « Mettre à jour » (message `a=update` sans
texte), relevés de la réserve toutes les 30 s pendant un passage de `forever update` (fenêtre ouverte, 20 au plus),
ligne « Mise à jour terminée » écrite une seule fois par passage terminé."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import collect, waiting_slots
from test_bridge_window_lua import history

from forever.bridge.buttons import button_payload, visible_buttons
from forever.bridge.slots import inbox_lua, status_lua

pytest.importorskip("lupa")

STATUS = {"line": "Données 1.60.1.70338 · client 1.60.1.70338 · à jour", "slots": 60}


def loads(game):
    return [round(float(e[2]), 1) for e in game.stub.loadlog.values() if str(e[1]).startswith("ForeverBridge_S")]


def test_update_button_sends_an_action_without_text():
    game = Game()
    waiting_slots(game)
    game.lua.execute(status_lua(STATUS, button_payload(visible_buttons()), 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    button = game.lua.globals().ForeverBridgeButton_update
    assert button is not None and button.IsShown(button)
    button.scripts.OnClick(button)
    record, _ = collect(game)
    assert record.flags == frozenset({"a=update"}) and record.text == ""
    assert any("Mettre à jour" in line for line in history(game))


def running(step="clone"):
    return {**STATUS, "update": {"running": True, "step": step}}


def test_polls_every_thirty_seconds_during_a_pass():
    game = Game()
    for index in range(1, 61):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(1791547200, running(), [], [])
    game.lua.execute(status_lua(running(), [], 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    game.stub.Advance(30 * 25, 1.0)
    times = loads(game)
    assert len(times) == 22  # 20 relevés à 30 s, puis toutes les 60 s (décision 240)
    assert times[:3] == pytest.approx([30, 60, 90], abs=1.1)


def test_no_pass_no_extra_polls():
    game = Game()
    game.lua.execute(status_lua(STATUS, [], 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    game.stub.Advance(300, 1.0)
    assert loads(game) == []


def finished(at, written=1, approvable=2):
    return {**STATUS, "update": {"running": False, "last": {"finished_at": at, "written": written,
                                                            "approvable": approvable}}}  # fmt: skip


def test_finished_line_is_written_once_per_pass():
    game = Game()
    game.lua.execute(status_lua(running(), [], 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    for index in range(1, 4):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(
            1791547200, finished("2026-10-10T12:05:00Z"), [], []
        )
    game.stub.Advance(95, 1.0)
    done = [line for line in history(game) if "Mise à jour terminée" in line]
    assert done == ["Mise à jour terminée : 1 écrit(s), 2 à valider"]
    game.stub.addons["ForeverBridge_S002"] = inbox_lua(1791547200, finished("2026-10-10T13:00:00Z", 0, 0), [], [])
    game.lua.globals().ForeverBridge.PollSlot()
    done = [line for line in history(game) if "Mise à jour terminée" in line]
    assert done[-1] == "Mise à jour terminée : 0 écrit(s), 0 à valider" and len(done) == 2


def test_an_old_pass_seen_at_login_is_not_announced():
    game = Game()
    game.lua.execute(status_lua(finished("2026-10-10T12:05:00Z"), [], 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    assert not any("Mise à jour terminée" in line for line in history(game))
