"""Essai CJ-6 du 2026-10-15, défauts 1 et 4, sous lupa.lua51 :

1. les boutons d'une réponse (« Valider et livrer »…) ont leur propre rangée sous l'historique, qui se raccourcit
   d'autant : jamais dessinés sur du texte ; ils suivent le défilement (montrés quand la dernière réponse est en vue,
   retirés quand le joueur remonte l'historique) ;
4. un bouton « Effacer » visible dans l'en-tête vide l'historique affiché et repart d'une nouvelle conversation ; les
   anciens messages restent archivés dans la sauvegarde, sans s'afficher.

Réponses synthétiques (aucune règle de jeu)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_reply_lua import fill, reply
from test_bridge_send_lua import sent, type_and_enter
from test_bridge_window_lua import history

pytest.importorskip("lupa")

CHOICES = {"prompt": "", "buttons": [{"label": "Valider et livrer", "action": "route_deliver"}]}


def g(game, name):
    return game.lua.globals()[name]


def bottom(frame) -> float:
    (point,) = [p for p in frame.points.values() if p.point == "BOTTOMRIGHT"]
    return point.y


def answered(game):
    fill(game, [reply(game, "done", text="Aperçu\nligne 2\nligne 3", provenance="p", choices=CHOICES)])
    type_and_enter(game, "Prépare ma feuille de route")
    game.stub.Advance(4)


def test_answer_row_sits_under_the_history_never_on_its_text():
    game = Game()
    game.slash("/fv")
    hist = g(game, "ForeverBridgeHistory")
    before = bottom(hist)
    answered(game)
    bar = g(game, "ForeverBridgeAnswers")
    assert bar.IsVisible(bar)
    point = bar.points[1]
    assert point.point == "TOPLEFT" and point.relPoint == "BOTTOMLEFT" and point.y <= 0
    assert game.lua.eval("rawequal")(point.rel, hist)  # sous l'historique, pas dedans
    assert bottom(hist) - before >= bar.GetHeight(bar)  # l'historique s'est raccourci de la rangée
    button = g(game, "ForeverBridgeAnswer1")
    button.scripts.OnClick(button)
    assert not bar.IsShown(bar) and bottom(hist) == before  # réponse donnée : la place revient au texte


def test_answer_row_follows_the_scrolling():
    game = Game()
    game.slash("/fv")
    answered(game)
    hist, bar = g(game, "ForeverBridgeHistory"), g(game, "ForeverBridgeAnswers")
    hist.scripts.OnMouseWheel(hist, 1)  # le joueur remonte : la dernière réponse sort de la vue
    assert not bar.IsShown(bar)
    hist.scripts.OnMouseWheel(hist, -1)  # retour en bas : la rangée revient sous la réponse
    assert bar.IsShown(bar)


def test_clear_button_empties_the_history_and_starts_a_new_conversation():
    game = Game()
    game.slash("/fv")
    answered(game)
    assert any("Aperçu" in line for line in history(game))
    clear = g(game, "ForeverBridgeClearButton")
    assert clear is not None and clear.IsVisible(clear) and clear.GetText(clear) == "Effacer"
    clear.scripts.OnClick(clear)
    assert not any("Aperçu" in line or "Prépare" in line for line in history(game))
    assert not g(game, "ForeverBridgeAnswers").IsShown(g(game, "ForeverBridgeAnswers"))
    archive = game.lua.globals().ForeverBridgeDB.archive
    assert archive is not None and any("Prépare" in str(e.text) for e in archive[1].values())
    game.slash("/fv")
    game.slash("/fv")  # fenêtre rouverte : les anciens messages ne reviennent pas
    assert not any("Aperçu" in line for line in history(game))
    type_and_enter(game, "Nouvelle question")
    assert "n" in sent(game)[1].flags
