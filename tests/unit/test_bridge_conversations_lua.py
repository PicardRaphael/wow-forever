"""Plusieurs conversations de jeu (CJ1, bloc 6b, idées du 2026-10-16, point 4) : créer, nommer, passer de l'une à
l'autre, effacer ; chacune garde son historique (ForeverBridgeDB) et sa session (drapeau `c=<id>` lu par le pont).
La conversation par défaut (« Jeu ») et l'onglet Addons restent ce qu'ils étaient : jamais de drapeau `c=` pour la
première, `c=addons` pour le second. Menu de l'onglet Jeu et commandes `/fb conv`.

Client simulé ; questions et réponses inventées (aucune règle de jeu)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_reply_lua import fill, reply
from test_bridge_send_lua import sent, type_and_enter
from test_bridge_window6_lua import click, text, visible
from test_bridge_window_lua import history

from forever.bridge.codec import decode_band

pytest.importorskip("lupa")


def db(game):
    return game.lua.globals().ForeverBridgeDB


def entries(game, key):
    table = db(game)[key]
    return [] if table is None else [str(table[i].text) for i in range(1, len(table) + 1)]


def opened():
    game = Game()
    game.slash("/fv")
    return game


def test_new_conversation_has_its_own_history_and_flag():
    game = opened()
    type_and_enter(game, "Question du fil principal")
    _, record = sent(game)
    assert not any(f.startswith("c=") for f in record.flags)
    game.stub.Advance(12)  # boîte d'envoi : la bande se libère
    game.slash("/fb conv new Donjons")
    assert text(game, "ForeverBridgeTabGame") == "Donjons"
    assert not any("Question du fil principal" in line for line in history(game))
    type_and_enter(game, "Question des donjons")
    _, record = sent(game)
    conv = next(f for f in record.flags if f.startswith("c="))
    assert conv != "c=addons" and conv[2:].isalnum()
    assert entries(game, "history_" + conv[2:]) == ["Question des donjons"]
    assert entries(game, "history") == ["Question du fil principal"]


def test_switch_back_and_forth_keeps_each_history():
    game = opened()
    game.slash("/fb conv new Raid")
    type_and_enter(game, "Question du raid")
    game.stub.Advance(12)
    game.slash("/fb conv 1")
    assert text(game, "ForeverBridgeTabGame") == "Jeu"
    assert not any("Question du raid" in line for line in history(game))
    type_and_enter(game, "Question du fil principal")
    _, record = sent(game)
    assert not any(f.startswith("c=") for f in record.flags)
    game.slash("/fb conv 2")
    assert any("Question du raid" in line for line in history(game))


def test_reply_goes_to_the_conversation_it_was_asked_in():
    game = opened()
    game.slash("/fb conv new Métiers")
    fill(game, [reply(game, "done", text="Réponse des métiers", provenance="p")])
    type_and_enter(game, "Question des métiers")
    game.slash("/fb conv 1")  # le joueur change de conversation avant la réponse
    game.stub.Advance(10)
    assert not any("Réponse des métiers" in line for line in history(game))
    game.slash("/fb conv 2")
    assert any("Réponse des métiers" in line for line in history(game))


def test_rename_by_command_and_by_the_menu():
    game = opened()
    game.slash("/fb conv new Brouillon")
    game.slash("/fb conv nom Leveling 30")
    assert text(game, "ForeverBridgeTabGame") == "Leveling 30"
    click(game, "ForeverBridgeConvToggle")
    assert visible(game, "ForeverBridgeConvMenu")
    click(game, "ForeverBridgeConvRename")
    type_and_enter(game, "Quêtes de classe")  # le nom part dans le titre, pas au pont
    assert decode_band(game.screen_image()) is None
    assert text(game, "ForeverBridgeTabGame") == "Quêtes de classe"
    names = db(game).conversations
    assert [str(names[i].name) for i in range(1, len(names) + 1)] == ["Jeu", "Quêtes de classe"]


def test_menu_lists_and_switches_conversations():
    game = opened()
    game.slash("/fb conv new Un")
    game.slash("/fb conv new Deux")
    click(game, "ForeverBridgeConvToggle")
    labels = [text(game, f"ForeverBridgeConvItem{i}") for i in range(1, 4)]
    assert labels[0] == "Jeu" and labels[1] == "Un" and labels[2].startswith("Deux")  # courante marquée
    click(game, "ForeverBridgeConvItem2")
    assert text(game, "ForeverBridgeTabGame") == "Un" and not visible(game, "ForeverBridgeConvMenu")
    click(game, "ForeverBridgeConvToggle")
    click(game, "ForeverBridgeConvNew")
    assert text(game, "ForeverBridgeTabGame").startswith("Conversation")


def test_delete_asks_for_a_second_click_and_never_removes_the_default():
    game = opened()
    game.slash("/fb conv new Jetable")
    type_and_enter(game, "À effacer")
    game.stub.Advance(12)
    click(game, "ForeverBridgeConvToggle")
    click(game, "ForeverBridgeConvDelete")
    assert "Confirmer" in text(game, "ForeverBridgeConvDelete")  # premier clic : rien d'effacé
    assert len(db(game).conversations) == 2
    click(game, "ForeverBridgeConvDelete")
    assert len(db(game).conversations) == 1 and text(game, "ForeverBridgeTabGame") == "Jeu"
    assert all(not str(k).startswith("history_c") for k in db(game))  # clés de la table Lua
    type_and_enter(game, "Question principale")
    game.stub.Advance(12)
    game.slash("/fb conv effacer")  # conversation par défaut : historique vidé, fil repris de zéro, jamais retirée
    game.slash("/fb conv effacer")
    assert len(db(game).conversations) == 1 and entries(game, "history") == []
    type_and_enter(game, "Nouveau départ")
    _, record = sent(game)
    assert "n" in record.flags


def test_conv_command_lists_the_conversations():
    game = opened()
    game.slash("/fb conv new Donjons")
    game.slash("/fb conv")
    lines = history(game)
    assert any("1. Jeu" in line for line in lines) and any("2. Donjons" in line for line in lines)
