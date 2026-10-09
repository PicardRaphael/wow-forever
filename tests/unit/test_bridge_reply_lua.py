"""Réponses dans la fenêtre (P06a, bloc E, décision 212 amendée le 2026-10-09), sous lupa.lua51 : consultation de
la réserve à intervalles après un envoi (3, 7, 11 … 27, 30, 40 … 190 s), accusé (`working`) qui retire la bande,
réponse mise en forme avec sa provenance et son lien copiable, trois relevés sans accusé → boîte d'envoi, réserve
presque vide → /reload proposé, réserve vide → réponse au /reload, entrée d'une autre session ignorée, aucune
ouverture automatique, historique gardé. Les emplacements simulés sont écrits par `inbox_lua` du pont : ce que le pont
écrit est ce que l'addon lit."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history, window

from forever.bridge.buttons import button_payload, visible_buttons
from forever.bridge.codec import decode_band
from forever.bridge.slots import inbox_lua

pytest.importorskip("lupa")

STATUS = {"version": "1.60.1.70245", "freshness": "fresh", "line": "Données 1.60.1.70245 · à jour", "slots": 30}
SCHEDULE = [3, 7, 11, 15, 19, 23, 27, 30, *range(40, 191, 10)]
LINK = "https://talents-forever.example/mage/20/x"


def session(game):
    return game.lua.globals().ForeverBridgeDB.session


def reply(game, status, message_id=1, **extra):
    return {"session": session(game), "id": message_id, "status": status, "since": 0, **extra}


def put(game, index, replies, status=STATUS, buttons=()):
    game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(1791547200, status, replies, list(buttons))


def fill(game, replies, upto=30, status=STATUS):
    for index in range(1, upto + 1):
        put(game, index, replies, status)


def loads(game):
    return [
        (str(e[1]), round(float(e[2]), 1))
        for e in game.stub.loadlog.values()
        if str(e[1]).startswith("ForeverBridge_S")
    ]


def band_shown(game):
    return decode_band(game.screen_image()) is not None


def status_text(game):
    line = game.lua.globals().ForeverBridgeStatusLine
    return str(line.GetText(line) or "")


def test_poll_schedule_until_the_ceiling():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "working")])
    type_and_enter(game, "Question")
    game.stub.Advance(200, 0.1)
    times = [t for _, t in loads(game)]
    assert times == pytest.approx(SCHEDULE, abs=0.15)
    assert [name for name, _ in loads(game)][:3] == ["ForeverBridge_S001", "ForeverBridge_S002", "ForeverBridge_S003"]
    assert any("toujours en cours" in line and "/reload" in line for line in history(game))


def test_acknowledgement_hides_the_band_and_shows_progress():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "working")])
    type_and_enter(game, "Question")
    game.stub.Advance(3.1)
    assert not band_shown(game)
    assert "réponse en cours" in status_text(game)


def test_done_reply_is_formatted_and_polling_stops():
    game = Game()
    game.slash("/fv")
    put(game, 1, [reply(game, "working")])
    done = reply(
        game, "done", text="## Prochain talent\n- **Improved Frostbolt** au niveau 20\nTexte | simple",
        provenance="Données 1.60.1.70245 · probable", link=LINK,
    )  # fmt: skip
    for index in range(2, 31):
        put(game, index, [done])
    type_and_enter(game, "Question")
    game.stub.Advance(60)
    lines = history(game)
    assert [name for name, _ in loads(game)] == ["ForeverBridge_S001", "ForeverBridge_S002"]
    assert any("Forever" in line for line in lines)
    assert any("|cffffd100Prochain talent|r" in line for line in lines)
    assert any("•" in line and "|cffffffffImproved Frostbolt|r" in line for line in lines)
    assert any("Texte || simple" in line for line in lines)
    assert any("Données 1.60.1.70245 · probable" in line for line in lines)
    link_line = next(line for line in lines if "[Talents Forever]" in line)
    assert "|Hforeverbridge:copy:" in link_line
    assert "réponse en cours" not in status_text(game)


def test_link_opens_the_copy_box():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "done", text="Build", provenance="p", link=LINK)])
    type_and_enter(game, "Question")
    game.stub.Advance(4)
    link_line = next(line for line in history(game) if "[Talents Forever]" in line)
    link = link_line.split("|H", 1)[1].split("|h", 1)[0]
    frame = game.lua.globals().ForeverBridgeHistory
    frame.scripts.OnHyperlinkClick(frame, link, "[Talents Forever]", "LeftButton")
    box = game.lua.globals().ForeverBridgeCopyBox
    assert box.GetText(box) == LINK and box.highlighted and box.IsVisible(box)


def test_three_polls_without_acknowledgement_go_to_the_outbox():
    game = Game()
    game.slash("/fv")
    fill(game, [])
    type_and_enter(game, "Question perdue")
    game.stub.Advance(11.2)
    assert not band_shown(game)
    outbox = game.lua.globals().ForeverBridgeDB.outbox
    entry = outbox[1]
    assert entry.id == 1 and entry.text == "Question perdue" and "class=MAGE" in entry.context
    assert any("pont injoignable" in line and "/reload" in line for line in history(game))
    game.stub.Advance(60)
    assert len(loads(game)) == 3


def test_reply_of_another_session_is_ignored():
    game = Game()
    game.slash("/fv")
    fill(game, [{"session": "autre", "id": 1, "status": "done", "text": "pas pour moi", "provenance": "p"}])
    type_and_enter(game, "Question")
    game.stub.Advance(12)
    assert not any("pas pour moi" in line for line in history(game))


def test_reserve_almost_empty_proposes_reload():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "working")], status={**STATUS, "slots": 12})
    type_and_enter(game, "Question")
    game.stub.Advance(3.1)
    assert "/reload" not in status_text(game)
    game.stub.Advance(4)
    assert "10 emplacements" in status_text(game) and "/reload" in status_text(game)


def test_reserve_empty_then_reply_after_reload():
    game = Game()
    game.slash("/fv")
    put(game, 1, [reply(game, "working")])
    type_and_enter(game, "Question")
    game.stub.Advance(8)
    assert any("réserve" in line and "/reload" in line for line in history(game))
    saved_session = session(game)
    db = game.lua.globals().ForeverBridgeDB
    saved = {"schema": 1, "session": saved_session, "next_id": int(db.next_id), "waiting": {1: 1}}
    again = Game(saved=saved)
    again.lua.execute(inbox_lua(1791547300, STATUS, [{"session": saved_session, "id": 1, "status": "done",
                                                      "text": "Réponse arrivée", "provenance": "p"}], []))  # fmt: skip
    again.stub.Fire("PLAYER_ENTERING_WORLD", False, True)
    again.slash("/fv")
    assert any("Réponse arrivée" in line for line in history(again))


def test_no_automatic_opening():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "done", text="Réponse", provenance="p")])
    type_and_enter(game, "Question")
    game.slash("/fv")
    assert not window(game).IsShown(window(game))
    game.stub.combat = True
    game.stub.Advance(10)
    assert not window(game).IsShown(window(game))
    game.stub.combat = False
    game.slash("/fv")
    assert any("Réponse" in line for line in history(game))
    assert list(game.stub.printed.values()) == []


def test_status_line_and_buttons_come_from_the_slot():
    game = Game()
    game.slash("/fv")
    for index in range(1, 31):
        put(game, index, [reply(game, "working")], buttons=button_payload(visible_buttons()))
    type_and_enter(game, "Question")
    game.stub.Advance(3.1)
    text = status_text(game)
    assert "Données 1.60.1.70245 · à jour" in text and "pont vu" in text
    talents = game.lua.globals()["ForeverBridgeButton_talents"]
    assert talents is not None and talents.IsShown(talents)


def test_history_is_kept_across_sessions():
    game = Game()
    game.slash("/fv")
    fill(game, [reply(game, "done", text="Réponse gardée", provenance="p")])
    type_and_enter(game, "Question gardée")
    game.stub.Advance(4)
    db = game.lua.globals().ForeverBridgeDB
    entries = [db.history[i] for i in range(1, len(db.history) + 1)]
    assert [e.role for e in entries] == ["user", "assistant"]
    saved = {
        "schema": 1,
        "session": session(game),
        "next_id": 2,
        "history": [{"role": e.role, "text": e.text} for e in entries],
    }
    again = Game(saved=saved)
    again.slash("/fv")
    lines = history(again)
    assert any("Question gardée" in line for line in lines) and any("Réponse gardée" in line for line in lines)


def test_after_reload_pending_messages_are_polled_again():
    """Secours /reload : la boîte d'envoi est lue par le pont au rechargement ; l'addon relance la consultation et
    récupère la réponse dans la réserve, sans second /reload."""
    game = Game(saved={"schema": 1, "session": "6ac884ce31ab", "next_id": 6,
                       "outbox": [{"id": 5, "text": "Question gardée", "flags": "", "slot": 4, "context": ""}]})  # fmt: skip
    game.stub.addons["ForeverBridge_S001"] = inbox_lua(1791547200, STATUS, [
        {"session": "6ac884ce31ab", "id": 5, "status": "done", "text": "Réponse après /reload", "provenance": "p"}
    ], [])  # fmt: skip
    game.stub.Fire("PLAYER_ENTERING_WORLD", False, True)
    game.stub.Advance(4)
    assert [name for name, _ in loads(game)] == ["ForeverBridge_S001"]
    assert len(game.lua.globals().ForeverBridgeDB.outbox) == 0
    game.slash("/fv")
    assert any("Réponse après /reload" in line for line in history(game))


def test_waiting_files_never_erase_the_bridge_state():
    """À la connexion, Status.lua écrit par le pont donne l'état et les boutons ; un Inbox.lua ou un emplacement
    d'attente (jamais publié, `now = 0`) ne les efface pas."""
    from forever.bridge.slots import status_lua

    game = Game()
    game.lua.execute(status_lua(STATUS, button_payload(visible_buttons()), 1791547200))
    game.lua.execute(inbox_lua(0, {}, [], []))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    assert "Données 1.60.1.70245 · à jour" in status_text(game) and "pont vu" in status_text(game)
    talents = game.lua.globals()["ForeverBridgeButton_talents"]
    assert talents is not None and talents.IsShown(talents)
    put(game, 1, [], status={})
    game.stub.addons["ForeverBridge_S001"] = inbox_lua(0, {}, [], [])
    type_and_enter(game, "Question")
    game.stub.Advance(3.1)
    assert "Données 1.60.1.70245 · à jour" in status_text(game)
    assert talents.IsShown(talents)
