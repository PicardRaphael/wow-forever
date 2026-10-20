"""Réputations du personnage (CJ1, bloc 6b, décision 281 ; étude `docs/research/reputations-forever.md`) :
ForeverBridge lit le panneau de réputation (`C_Reputation`, repli sur l'ancienne API, sous `pcall`, comme Forever
Guide et EllesmereUI) ; il envoie `reputations` (faction, palier, réputation, en entiers) et l'assistant de feuille de
route liste les factions groupées comme dans le jeu, filtrables par groupe, puis le palier visé, sans niveaux ni champ
libre. Tant que la route de réputation n'est pas calculée (bloc 4e), rien n'est envoyé.

Factions, paliers et valeurs inventés pour le test ; libellés des paliers fournis par le client simulé."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_window6_lua import click, g, opened, text, visible

from forever.bridge.codec import decode_band
from forever.bridge.context import reputations_context

pytest.importorskip("lupa")

LABELS = "\n".join(f'FACTION_STANDING_LABEL{i} = "Palier{i}"' for i in range(1, 9))
REPS = (
    LABELS
    + """
factions = {
    { name = "Groupe A", factionID = 900, isHeader = true, isHeaderWithRep = false },
    { name = "Faction Un", factionID = 901, reaction = 4, currentStanding = 120, isHeader = false },
    { name = "Faction Deux", factionID = 902, reaction = 5, currentStanding = 3500, isHeader = false },
    { name = "Groupe B", factionID = 910, isHeader = true, isHeaderWithRep = false },
    { name = "Faction Trois", factionID = 911, reaction = 2, currentStanding = -9000, isHeader = false },
}
C_Reputation = {}
function C_Reputation.GetNumFactions() return #factions end
function C_Reputation.GetFactionDataByIndex(i) return factions[i] end
"""
)
EXPECTED = "901:4:120,902:5:3500,911:2:-9000"
LEGACY = (
    LABELS
    + """
legacy = {
    { "Groupe A", "", 0, 0, 0, 0, false, false, true, false, false, false, false, 900 },
    { "Faction Un", "", 4, 0, 3000, 120, false, true, false, false, false, false, false, 901 },
}
function GetNumFactions() return #legacy end
function GetFactionInfo(i) return unpack(legacy[i]) end
"""
)


def ctx_of(game):
    return game.lua.globals().ForeverBridge_Message.Context()[0]["reputations"]


def test_reputations_in_context():
    assert ctx_of(Game(prelude=REPS)) == EXPECTED
    assert ctx_of(Game(prelude=LEGACY)) == "901:4:120"  # ancienne API : même forme
    assert ctx_of(Game()) is None  # API absente : champ absent, aucune erreur
    broken = (
        "C_Reputation = { GetNumFactions = function() return 2 end, GetFactionDataByIndex = function() error('x') end }"
    )
    assert ctx_of(Game(prelude=broken)) is None


def test_reputations_are_a_context_key():
    from forever.bridge.record import CONTEXT_KEYS

    assert "reputations" in CONTEXT_KEYS
    keys = Game().lua.globals().ForeverBridge_Message.KEYS
    assert "reputations" in [keys[i] for i in range(1, len(keys) + 1)]


def test_reputations_resolved():
    assert reputations_context({"reputations": EXPECTED}) == {901: (4, 120), 902: (5, 3500), 911: (2, -9000)}
    assert reputations_context({}) is None
    assert reputations_context({"reputations": "901:x:1,902:5:3500"}) == {902: (5, 3500)}


def test_assistant_lists_the_factions_by_group_then_the_target_standing():
    game = opened(prelude=REPS)
    click(game, "ForeverBridgeNav_route")
    click(game, "ForeverBridgeRouteType_reputation")
    rows = [text(game, f"ForeverBridgeRepRow{i}") for i in range(1, 6) if visible(game, f"ForeverBridgeRepRow{i}")]
    assert rows[0].startswith("Groupe A") and "Faction Un" in rows[1] and "Palier4" in rows[1]
    assert any("Faction Trois" in r and "Palier2" in r for r in rows)
    click(game, "ForeverBridgeRepGroup")  # filtre : premier groupe seulement
    shown = [text(game, f"ForeverBridgeRepRow{i}") for i in range(1, 6) if visible(game, f"ForeverBridgeRepRow{i}")]
    assert any("Faction Deux" in r for r in shown) and not any("Faction Trois" in r for r in shown)
    click(game, "ForeverBridgeRepRow3")  # Faction Deux, au palier 5
    assert "Faction Deux" in text(game, "ForeverBridgeRepChosen")
    assert text(game, "ForeverBridgeRepTargetValue") == "Palier6"  # palier suivant proposé
    click(game, "ForeverBridgeRepTargetUp")
    assert text(game, "ForeverBridgeRepTargetValue") == "Palier7"
    for _ in range(5):
        click(game, "ForeverBridgeRepTargetUp")
    assert text(game, "ForeverBridgeRepTargetValue") == "Palier8"  # jamais au-delà du dernier palier
    assert "pas encore" in text(game, "ForeverBridgeRouteUnavailable")  # route non calculée avant le bloc 4e
    assert not visible(game, "ForeverBridgeRouteFromValue") and not visible(game, "ForeverBridgeRouteCompute")
    assert decode_band(game.screen_image()) is None


def test_assistant_without_reputation_api_says_so():
    game = opened()
    click(game, "ForeverBridgeNav_route")
    click(game, "ForeverBridgeRouteType_reputation")
    assert "aucune réputation lue" in text(game, "ForeverBridgeRepChosen").lower()
    assert not visible(game, "ForeverBridgeRepRow1")


def test_faction_list_hidden_for_the_other_route_types():
    game = opened(prelude=REPS)
    click(game, "ForeverBridgeNav_route")
    click(game, "ForeverBridgeRouteType_reputation")
    assert visible(game, "ForeverBridgeRepRow1")
    click(game, "ForeverBridgeRouteType_leveling")
    assert not visible(game, "ForeverBridgeRepRow1") and not visible(game, "ForeverBridgeRepTargetValue")


def test_reputation_screen_fits_the_smallest_window():
    """Fenêtre au plus petit (520 × 380, bloc 6a) : la liste, le palier visé et le message tiennent dans l'écran."""
    from test_bridge_window6_lua import resize

    game = opened(prelude=REPS)
    resize(game, 520, 380)
    click(game, "ForeverBridgeNav_route")
    click(game, "ForeverBridgeRouteType_reputation")
    screen = g(game, "ForeverBridgeScreen_route")
    width, height = 520 - 150 - 14, 380 - 52 - 16  # fenêtre moins barre latérale, en-tête et marges (Screens.lua)
    for name in ("ForeverBridgeRepRow5", "ForeverBridgeRepChosen", "ForeverBridgeRepTargetUp",
                 "ForeverBridgeRouteUnavailable", "ForeverBridgeRepNext"):  # fmt: skip
        widget = g(game, name)
        point = widget.points[1]
        assert game.lua.eval("rawequal")(point.rel, screen), name
        assert point.x + widget.GetWidth(widget) <= width, name
        assert -point.y + (widget.GetHeight(widget) or 0) <= height, name
