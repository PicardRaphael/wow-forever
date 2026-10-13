"""Suites de l'essai en jeu du panneau « À valider » et du bouton « Mettre à jour » (décision 240), sous lupa.lua51 :

- panneau de droite fermé par une croix en haut, par un second clic sur « À valider », en plus d'Échap ;
- bouton « Masquer » sur chaque carte : la carte quitte le panneau et les compteurs sans rien valider ni refuser, et
  reste masquée (même après `/reload`) tant que son empreinte ne change pas ;
- avancement d'une mise à jour : après « Mettre à jour », la ligne d'état s'anime, nomme l'étape et compte le temps
  écoulé pendant tout le passage ; relevés de la réserve rapprochés dès le clic, puis espacés ; phrase de fin du pont
  écrite une fois.

Cartes et états synthétiques (aucune règle de jeu)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import card_button, click, collect, waiting_slots
from test_bridge_reply_lua import status_text
from test_bridge_window_lua import history

from forever.bridge.buttons import button_payload, visible_buttons
from forever.bridge.codec import decode_band
from forever.bridge.slots import inbox_lua, status_lua

pytest.importorskip("lupa")

EPOCH = 1791547200  # Stub.epoch : time() du client simulé à l'instant 0
HEAD = "Données 1.60.1.70338 · client 1.60.1.70338 · à jour"
HIDE = {"key": "hide", "label": "Masquer", "hide": True}


def card(ident, stamp, count="approvable"):
    buttons = [
        {"key": "approve", "label": "Valider", "action": f"approve:{ident}", "confirm": True},
        {"key": "reject", "label": "Refuser", "action": f"reject:{ident}", "confirm": True},
    ] if count == "approvable" else []  # fmt: skip
    return {"id": ident, "kind": "update", "title": f"Carte {ident}", "lines": ["ligne"], "count": count,
            "stamp": stamp, "buttons": [*buttons, {"key": "explain", "label": "Expliquer", "explain": True}, HIDE]}  # fmt: skip


def status(**extra):
    return {"line": HEAD + " · 1 à valider · 1 en attente", "line_head": HEAD, "line_tail": "", "slots": 80, **extra}


class Publisher:
    """Publie un emplacement à la fois, comme le pont : chaque relevé charge l'emplacement suivant."""

    def __init__(self, game):
        self.game = game
        self.index = 0

    def __call__(self, cards, state=None):
        self.index += 1
        self.game.stub.addons[f"ForeverBridge_S{self.index:03d}"] = inbox_lua(EPOCH, state or status(), [], [], cards)
        self.game.lua.globals().ForeverBridge.PollSlot()


def opened(cards):
    game = Game()
    game.slash("/fv")
    publish = Publisher(game)
    publish(cards)
    lua = game.lua.globals()
    click(lua.ForeverBridgeCardsButton)
    return game, publish, lua


def shown(widget):
    return widget is not None and widget.IsVisible(widget)


def cards_label(lua):
    button = lua.ForeverBridgeCardsButton
    return str(button.GetText(button)) if button.IsShown(button) else None


# --- 5. fermer le panneau -------------------------------------------------------------------------------------


def test_the_cross_closes_the_panel():
    _, _, lua = opened([card("a", "s1")])
    cross = lua.ForeverBridgePanelClose
    assert cross is not None and cross.template == "UIPanelCloseButton" and shown(cross)
    point = cross.points[1]
    assert point.point == "TOPRIGHT"
    click(cross)
    assert not shown(lua.ForeverBridgePanel)


def test_a_second_click_on_the_cards_button_closes_the_panel():
    _, _, lua = opened([card("a", "s1")])
    assert shown(lua.ForeverBridgePanel)
    click(lua.ForeverBridgeCardsButton)
    assert not shown(lua.ForeverBridgePanel)
    click(lua.ForeverBridgeCardsButton)
    assert shown(lua.ForeverBridgePanel)


# --- 6. Masquer -----------------------------------------------------------------------------------------------


def test_hide_removes_the_card_without_any_action():
    game, _, lua = opened([card("a", "s1"), card("b", "s2", count="waiting")])
    assert cards_label(lua) == "À valider (2)"
    before = len(game.stub.loadlog)
    click(card_button(game, 1, "hide"))
    assert cards_label(lua) == "À valider (1)"
    assert str(lua.ForeverBridgeCard1Text.GetText(lua.ForeverBridgeCard1Text)).find("Carte b") >= 0
    assert dict(lua.ForeverBridgeDB.hidden) == {"a": "s1"}
    assert decode_band(game.screen_image()) is None  # rien d'envoyé au pont : ni Valider ni Refuser
    assert len(game.stub.loadlog) == before


def test_a_hidden_card_stays_hidden_until_it_changes():
    game, publish, lua = opened([card("a", "s1"), card("b", "s2", count="waiting")])
    click(card_button(game, 1, "hide"))
    publish([card("a", "s1"), card("b", "s2", count="waiting")])
    assert cards_label(lua) == "À valider (1)"
    publish([card("a", "s1-changée"), card("b", "s2", count="waiting")])
    assert cards_label(lua) == "À valider (2)"


def test_hiding_the_last_card_closes_the_panel_and_the_button():
    game, _, lua = opened([card("a", "s1")])
    click(card_button(game, 1, "hide"))
    assert cards_label(lua) is None
    assert not shown(lua.ForeverBridgePanel)


def test_hidden_cards_survive_a_reload():
    game = Game(saved={"session": "abcd", "next_id": 3, "hidden": {"a": "s1"}})
    game.slash("/fv")
    Publisher(game)([card("a", "s1"), card("b", "s2", count="waiting")])
    assert cards_label(game.lua.globals()) == "À valider (1)"


def test_status_counts_leave_out_hidden_cards():
    game, _, _ = opened([card("a", "s1"), card("b", "s2", count="waiting")])
    assert "1 à valider · 1 en attente" in status_text(game)
    click(card_button(game, 1, "hide"))
    text = status_text(game)
    assert "à valider" not in text and "1 en attente" in text and text.startswith(HEAD)


# --- 4. avancement --------------------------------------------------------------------------------------------


def start(game):
    game.lua.execute(status_lua(status(), button_payload(visible_buttons()), EPOCH))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    button = game.lua.globals().ForeverBridgeButton_update
    click(button)
    record, _ = collect(game)
    assert record.flags == frozenset({"a=update"})


def running(started, stage="vérification des données"):
    return status(update={"running": True, "step": "journaux", "stage": stage, "started": started})


def finished(text="Mise à jour terminée en 4 min : rien de nouveau", at="2026-10-11T09:04:00Z"):
    return status(update={"running": False, "last": {"finished_at": at, "written": 0, "approvable": 0,
                                                     "text": text}})  # fmt: skip


def test_progress_is_shown_right_after_the_click_and_animates():
    game = Game()
    waiting_slots(game, 80)
    start(game)
    first = status_text(game)
    assert "Mise à jour en cours" in first and "lancement" in first
    texts = set()
    for _ in range(4):
        game.stub.Advance(0.5, 0.5)
        texts.add(status_text(game))
    assert len(texts) > 1  # animation et temps qui avance


def test_progress_names_the_stage_and_the_elapsed_time():
    game = Game()
    waiting_slots(game, 80)
    start(game)
    now = int(game.lua.eval("time()"))
    game.stub.addons["ForeverBridge_S002"] = inbox_lua(EPOCH, running(now - 192), [], [])
    game.stub.addons["ForeverBridge_S003"] = inbox_lua(EPOCH, running(now - 192), [], [])
    game.stub.Advance(31, 0.5)
    text = status_text(game)
    assert "vérification des données" in text
    assert "3 min" in text


def test_the_end_sentence_is_written_once_and_the_progress_stops():
    game = Game()
    waiting_slots(game, 80)
    start(game)
    now = int(game.lua.eval("time()"))
    for index in range(2, 5):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(EPOCH, running(now), [], [])
    for index in range(5, 9):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(EPOCH, finished(), [], [])
    game.stub.Advance(30 * 7, 1.0)
    done = [line for line in history(game) if "Mise à jour terminée" in line]
    assert done == ["Mise à jour terminée en 4 min : rien de nouveau"]
    assert "Mise à jour en cours" not in status_text(game)


def loads(game):
    return [round(float(e[2]), 1) for e in game.stub.loadlog.values() if str(e[1]).startswith("ForeverBridge_S")]


def test_polls_follow_the_whole_pass_then_slow_down():
    game = Game()
    for index in range(1, 151):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(EPOCH, running(EPOCH), [], [])
    game.lua.execute(status_lua(running(EPOCH), [], EPOCH))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    game.stub.Advance(30 * 20 + 60 * 5 + 1, 1.0)
    times = loads(game)
    assert len(times) == 25
    assert times[:2] == pytest.approx([30, 60], abs=1.1)
    assert times[20] - times[19] == pytest.approx(60, abs=1.1)
    game.stub.Advance(3000, 5.0)  # avant le relevé au repos qui suit le plafond
    assert len(loads(game)) == 70  # plafond d'une heure de relevés rapprochés


def test_polls_start_right_after_the_click_even_before_the_pass_is_seen():
    game = Game()
    waiting_slots(game, 80)
    start(game)
    before = len(loads(game))
    game.stub.Advance(95, 1.0)
    assert len(loads(game)) - before >= 3
