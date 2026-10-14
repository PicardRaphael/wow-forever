"""Questions à choix et mention « voir À valider » côté jeu (RX1, bloc E, ForeverBridge 0.3.0) : vrai Lua sous
lupa.lua51, client simulé `tests/fixtures/bridge/wow_stub.lua`."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_g_lua import EPOCH, card, opened, status
from test_bridge_p06b_lua import card_button, click, collect, with_cards
from test_bridge_reply_lua import reply
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

from forever.bridge.choices import ROUTE_CHOICES, choice_card
from forever.bridge.slots import inbox_lua

pytest.importorskip("lupa")

MENTION = "Écart avec ton profil : voir À valider"
TEXT = f"## Réponse\n- prochain talent\n\n{MENTION}"


def test_choice_click_sends_the_action():
    game = Game()
    game.slash("/fv")
    choice = ROUTE_CHOICES[0]
    with_cards(game, [choice_card(choice)])
    click(game.lua.globals().ForeverBridgeCardsButton)
    option = choice.options[2]
    click(card_button(game, 1, option.key))
    record, _ = collect(game)
    assert record.flags == frozenset({f"a=choice:{choice.id}.{option.key}"}) and record.text == ""


def _answer(game, cards, first):
    """Réponse finale publiée dans les emplacements suivants, avec les cartes `cards`."""
    done = reply(game, "done", text=TEXT)
    game.stub.addons[f"ForeverBridge_S{first:03d}"] = inbox_lua(EPOCH, status(), [reply(game, "working")], [], cards)
    for index in range(first + 1, first + 30):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(EPOCH, status(), [done], [], cards)
    type_and_enter(game, "Question")
    game.stub.Advance(60)
    return "\n".join(history(game))


def test_no_pending_mention_without_visible_card():
    game = Game()
    game.slash("/fv")
    assert MENTION not in _answer(game, [], 1)
    game = Game()
    game.slash("/fv")
    assert MENTION in _answer(game, [card("a", "s1")], 1)


def test_hidden_card_does_not_count_as_visible():
    shown_card = card("a", "s1")
    game, _, _ = opened([shown_card])
    click(card_button(game, 1, "hide"))
    assert MENTION not in _answer(game, [shown_card], 2)
