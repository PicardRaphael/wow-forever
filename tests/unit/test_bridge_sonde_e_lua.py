"""Retours de la sonde en jeu E du 2026-10-09 (P06a) sous lupa.lua51 : zone copiable déplaçable et ouverte à côté
de la fenêtre (point 3), niveau, classe et race de la cible (point 4, valeurs secrètes comprises), « Nouvelle
conversation » qui vide l'historique affiché et l'archive (point 5) ; secours de bout en bout avec le vrai pont et les
vrais fichiers : pont arrêté, boîte d'envoi, /reload, réponse sans second /reload."""

from datetime import UTC, datetime

import pytest
from test_bridge_addon_lua import Game
from test_bridge_reply_lua import LINK, STATUS, fill, reply
from test_bridge_send_lua import sent, type_and_enter
from test_bridge_window_lua import history, window

from forever.bridge.agent import AgentResult
from forever.bridge.capture import GameWindow
from forever.bridge.install import install_bridge
from forever.bridge.journal import Journal
from forever.bridge.loop import Bridge
from forever.bridge.state import BridgeState

pytest.importorskip("lupa")

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def test_copy_box_is_movable_and_opens_next_to_the_window():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "done", text="Build", provenance="p", link=LINK)])
    type_and_enter(game, "Question")
    game.stub.Advance(4)
    frame = game.lua.globals().ForeverBridgeHistory
    link = next(line for line in history(game) if "[Talents Forever]" in line).split("|H", 1)[1].split("|h", 1)[0]
    frame.scripts.OnHyperlinkClick(frame, link, "[Talents Forever]", "LeftButton")
    copy = game.lua.globals().ForeverBridgeCopy
    assert copy.movable and copy.clamped and "OnDragStart" in list(copy.scripts.keys())
    point = copy.points[1]
    assert game.lua.eval("rawequal")(point.rel, window(game))
    assert (point.point, point.relPoint) == ("TOPLEFT", "TOPRIGHT")


def test_target_level_class_and_race_are_sent():
    game = Game()
    game.stub.player.target = "SHAMAN"
    game.stub.player.target_level = 21
    game.stub.player.target_race = "Tauren"
    game.slash("/fv")
    type_and_enter(game, "Fiche de ma cible ?")
    ctx = sent(game)[1].context
    assert (ctx["target"], ctx["target_level"], ctx["target_race"]) == ("SHAMAN", "21", "Tauren")


def test_hidden_or_secret_target_values():
    game = Game()
    game.stub.player.target = "ROGUE"
    game.stub.player.target_level = -1
    game.stub.player.target_race = "Human"
    game.stub.secret["UnitRace"] = True
    game.slash("/fv")
    type_and_enter(game, "Q")
    ctx = sent(game)[1].context
    assert ctx["target"] == "ROGUE" and ctx["target_level"] == "??"
    assert "target_race" not in ctx


def test_new_conversation_clears_the_window_and_archives():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "done", text="Ancienne réponse", provenance="p")])
    type_and_enter(game, "Ancienne question")
    game.stub.Advance(4)
    assert any("Ancienne réponse" in line for line in history(game))
    game.lua.globals().ForeverBridgeNewButton.scripts.OnClick(game.lua.globals().ForeverBridgeNewButton)
    lines = history(game)
    assert not any("Ancienne" in line for line in lines)
    assert any("Nouvelle conversation" in line for line in lines)
    db = game.lua.globals().ForeverBridgeDB
    assert len(db.history) == 0
    archived = db.archive[1]
    assert [archived[i].text for i in range(1, len(archived) + 1)] == ["Ancienne question", "Ancienne réponse"]


# --- Secours de bout en bout : addon simulé, vrai pont, vrais fichiers -------------------------------------------


def lua_value(v, indent=""):
    """Sauvegarde Lua au format des SavedVariables du jeu (`["clé"] = valeur,`)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    items = v.items() if isinstance(v, dict) else enumerate(v, 1)
    body = "".join(f"{indent}\t[{lua_value(k)}] = {lua_value(x, indent + chr(9))},\n" for k, x in items)
    return "{\n" + body + indent + "}"


def to_python(table):
    if not hasattr(table, "items"):
        return table
    keys = list(table.keys())
    if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
        return [to_python(table[k]) for k in sorted(keys)]
    return {k: to_python(table[k]) for k in keys}


class NoBand:
    window = GameWindow(7, 4242, "WowB.exe", "World of Warcraft")

    def find(self):
        return self.window

    def client(self):
        return None

    def allowed(self):
        return False

    def grab(self, rect):
        raise AssertionError("aucune capture")


def disk_addons(game, addons_dir):
    """Les emplacements chargés à la demande sont lus sur le disque, comme le fait le jeu."""

    def read(name):
        path = addons_dir / str(name) / "Inbox.lua"
        return path.read_text(encoding="utf-8") if path.is_file() else None

    index = game.lua.eval("function(read) return function(_, name) return read(name) end end")(read)
    meta = game.lua.table(__index=index)
    game.lua.globals().setmetatable(game.stub.addons, meta)


def test_fallback_end_to_end_with_the_real_bridge(tmp_path):
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    install_bridge(wow, slots=8)
    addons = wow / "Interface" / "AddOns"
    saved = wow / "WTF" / "Account" / "COMPTE" / "SavedVariables" / "ForeverBridge.lua"

    # 1. Pont arrêté : la question part, trois relevés sans accusé, boîte d'envoi.
    game = Game()
    disk_addons(game, addons)
    game.slash("/fv")
    type_and_enter(game, "Question pendant que le pont est arrêté")
    game.stub.Advance(12)
    assert any("pont injoignable" in line for line in history(game))
    db = to_python(game.lua.globals().ForeverBridgeDB)
    assert [e["id"] for e in db["outbox"]] == [1]

    # 2. /reload : le jeu écrit la sauvegarde ; le pont relancé la lit et publie la réponse.
    saved.parent.mkdir(parents=True)
    saved.write_text("\nForeverBridgeDB = " + lua_value(db) + "\n", encoding="utf-8")
    calls = []

    def agent(prompt, session):
        calls.append(prompt)
        return AgentResult(
            text="Réponse du pont relancé", session_id="s1", provenances=[{"game_version": "v", "certainty": "certain"}]
        )

    bridge = Bridge(
        addons_dir=addons,
        capture=NoBand(),
        agent=agent,
        journal=Journal(tmp_path / "journal", lambda: NOW),
        state=BridgeState.load(tmp_path / "state.json"),
        status=lambda: STATUS,
        outbox_files=lambda: [saved],
        slots=8,
        executor=lambda job: job(),
    )

    # 3. Après le /reload, l'addon relance la consultation ; le pont traite la boîte d'envoi entre-temps.
    again = Game(saved=db)
    disk_addons(again, addons)
    again.lua.execute((addons / "ForeverBridge" / "Inbox.lua").read_text(encoding="utf-8"))
    again.stub.Fire("PLAYER_ENTERING_WORLD", False, True)
    bridge.step()
    assert len(calls) == 1 and "Question pendant que le pont est arrêté" in calls[0]
    again.stub.Advance(4)
    again.slash("/fv")
    assert any("Réponse du pont relancé" in line for line in history(again))
    assert len(again.lua.globals().ForeverBridgeDB.outbox) == 0
