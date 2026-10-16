"""Bloc 4c (essai CJ-6 du 2026-10-15) : un objet nommé par le pont (`[[item:<id>:<qualité>|<nom>]]`) s'affiche dans
l'historique comme un vrai lien d'objet du jeu (couleur de sa qualité), avec son infobulle au survol et le clic du jeu
(Maj+clic l'insère dans la saisie) ; le reste de la réponse reste neutralisé. Sous lupa.lua51, client simulé.

Objets synthétiques (aucune règle de jeu)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_reply_lua import fill, reply
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

pytest.importorskip("lupa")

PRELUDE = """
Seen = { tooltip = {}, itemref = {} }
GameTooltip = {}
function GameTooltip:SetOwner(owner, anchor) Seen.tooltip.owner = anchor end
function GameTooltip:SetHyperlink(link) Seen.tooltip.link = link end
function GameTooltip:Show() Seen.tooltip.shown = true end
function GameTooltip:Hide() Seen.tooltip.shown = false end
function SetItemRef(link, text, button) table.insert(Seen.itemref, link) end
"""


def answered(game, text):
    game.slash("/fv")
    fill(game, [reply(game, "done", text=text, provenance="p")])
    type_and_enter(game, "Mon équipement au niveau 10")
    game.stub.Advance(4)


def test_item_markup_becomes_a_game_link_with_tooltip_and_click():
    game = Game(prelude=PRELUDE)
    answered(game, "- Mains : [[item:930004:3|Fixture Gloves]] (niveau requis 9 ; marchand) a|b")
    (line,) = [line for line in history(game) if "Fixture Gloves" in line]
    assert "|Hitem:930004" in line and "|h[Fixture Gloves]|h" in line and "a||b" in line
    frame = game.lua.globals().ForeverBridgeHistory
    link = line.split("|H", 1)[1].split("|h", 1)[0]
    frame.scripts.OnHyperlinkEnter(frame, link, "[Fixture Gloves]")
    seen = game.lua.globals().Seen
    assert seen.tooltip.link == link and seen.tooltip.shown
    frame.scripts.OnHyperlinkLeave(frame)
    assert not seen.tooltip.shown
    frame.scripts.OnHyperlinkClick(frame, link, "[Fixture Gloves]", "LeftButton")
    assert seen.itemref[1] == link


def test_bad_markup_stays_plain_text():
    game = Game(prelude=PRELUDE)
    answered(game, "- Mains : [[item:abc:3|Pas un objet]]")
    (line,) = [line for line in history(game) if "Pas un objet" in line]
    assert "|Hitem:" not in line


def test_unnamed_item_takes_its_name_from_the_game():
    game = Game(
        prelude=PRELUDE + 'C_Item = C_Item or {}\nfunction C_Item.GetItemNameByID(id) return "Fixture Choker" end\n'
    )
    answered(game, "- Cou : [[item:970202:3|970202]] (donjon ouvert au niveau 8)")
    (line,) = [line for line in history(game) if "|Hitem:970202" in line]
    assert "[Fixture Choker]" in line
