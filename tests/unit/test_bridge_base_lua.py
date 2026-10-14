"""Profil de base EllesmereUI par personnage dans ForeverBridge (EX1, suite, décision 269), sous lupa.lua51 :
`/fb base <profil>` garde le choix par personnage (ForeverBridgeDB.bases) et l'envoie dans le contexte (`eui_base`) ;
un profil absent de la liste d'EllesmereUI est refusé avec la liste ; sans argument, le choix courant et la liste
sont affichés ; aucune écriture de `EllesmereUIDB`. API d'EllesmereUI bouchonnée (celle de `test_bridge_role_lua`)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import collect, waiting_slots
from test_bridge_role_lua import game_with_ellesmere, writes
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

pytest.importorskip("lupa")


def test_base_is_kept_per_character_and_sent_in_the_context():
    game = game_with_ellesmere()
    waiting_slots(game)
    game.slash("/fb base Hunt")
    assert game.lua.globals().ForeverBridgeDB.bases["Jen - Forever"] == "Hunt"
    type_and_enter(game, "Question")
    record, _ = collect(game)
    assert record.context["eui_base"] == "Hunt"
    assert writes(game) == []


def test_base_with_spaces_is_kept_whole():
    game = Game()
    game.slash("/fv")
    game.slash("/fb base Mon profil")
    assert game.lua.globals().ForeverBridgeDB.bases["Jen - Forever"] == "Mon profil"


def test_unknown_base_is_refused_with_the_list():
    game = game_with_ellesmere()
    game.slash("/fb base Inconnu")
    bases = game.lua.globals().ForeverBridgeDB.bases
    assert bases is None or bases["Jen - Forever"] is None
    assert any("Inconnu" in line and "Hunt" in line for line in history(game))


def test_without_argument_shows_the_choice_and_the_profiles():
    game = game_with_ellesmere()
    game.slash("/fb base Hunt")
    game.slash("/fb base")
    shown = "\n".join(history(game)[-3:])
    assert "Hunt" in shown and "Default" in shown


def test_without_ellesmere_the_choice_is_still_kept():
    game = Game()
    game.slash("/fv")
    game.slash("/fb base Mage")
    assert game.lua.globals().ForeverBridgeDB.bases["Jen - Forever"] == "Mage"
