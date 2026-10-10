"""Retours de la sonde en jeu G du 2026-10-10 (P06b) sur les relevés réels anonymisés (`contexts/mage19_sonde_g*.txt`,
`simc/mage19_sonde_g.txt`) : objets fabriqués (champ de l'artisan dans le lien) lus avec leur enchantement, liens
aux couleurs `|cn…:` de Forever affichés en liens dans l'historique, fenêtre de collage déplaçable et position
gardée, aide de `/fv` affichée une seule fois (puis sur demande)."""

import pytest
from conftest import FIXTURES

from forever.bridge.context import ContextData, resolve
from forever.bridge.items import parse_gear, parse_item_string, parse_links
from forever.simc import checksum_ok

CONTEXTS = FIXTURES / "bridge" / "contexts"


def context(name):
    out = {}
    # split("\n") et non splitlines() : splitlines() coupe aussi aux séparateurs 0x1C et 0x1D de `links`
    for line in (CONTEXTS / name).read_text(encoding="utf-8").split("\n"):
        key, _, value = line.partition("=")
        out[key] = value
    return out


# --- 5. Objets fabriqués ----------------------------------------------------------------------------------------------


def test_crafted_item_string_keeps_item_and_enchant():
    item = parse_item_string("2582:41:::::::19:1482::::::::Player-0000-00000001")
    assert (item.item, item.enchant, item.link_level, item.crafter) == (2582, 41, 19, "Player-0000-00000001")
    tuned = parse_item_string("1769::::::::19:1482::1::1:28:5249")
    assert (tuned.item, tuned.enchant, tuned.crafter) == (1769, 0, None)


@pytest.mark.parametrize("name", ["mage19_sonde_g.txt", "mage19_sonde_g_liens.txt", "mage19_sonde_g_simc.txt"])
def test_real_gear_has_no_bad_piece(name):
    pieces, bad = parse_gear(context(name)["gear"])
    assert bad == []
    assert [p.slot for p in pieces] == [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 18]
    by_slot = {p.slot: p for p in pieces}
    assert (by_slot[5].item.item, by_slot[5].item.enchant) == (2582, 41)
    assert (by_slot[15].item.item, by_slot[15].item.enchant) == (2580, 65)
    assert {s for s, p in by_slot.items() if p.item.crafter} == {5, 6, 15, 18}


def test_real_context_resolves_without_item_defect():
    data = ContextData(talents={}, level_cap=None, races={})
    r = resolve(data, context("mage19_sonde_g.txt"))
    assert not [d for d in r.defects if d.kind == "objet"]
    assert ("5", 2582, "Green Woolen Vest") in r.gear


def test_real_links_and_tooltips():
    links = parse_links(context("mage19_sonde_g_liens.txt")["links"])
    assert [(link.kind, link.body, link.name) for link in links] == [
        ("item", "item:3301::::::::19:1482", "Sharp Canine"),
        ("item", "item:14364::::::::19:1482", "Mystic's Slippers"),
    ]
    assert links[1].tooltip[:2] == ("Mystic's Slippers", "Binds when equipped")


def test_real_simc_export_is_anonymized_and_its_checksum_holds():
    text = (FIXTURES / "simc" / "mage19_sonde_g.txt").read_text(encoding="utf-8")
    assert checksum_ok(text) is True
    assert 'mage="Personnage"' in text and "server=royaume" in text


# --- 6. Liens dans l'historique ---------------------------------------------------------------------------------------

lupa = pytest.importorskip("lupa")

CANINE = "|cnIQ0:|Hitem:3301::::::::19:1482|h[Sharp Canine]|h|r"
SLIPPERS = "|cnIQ2:|Hitem:14364::::::::19:1482|h[Mystic's Slippers]|h|r"


def test_forever_colored_links_are_named_and_shown_as_links():
    from test_bridge_addon_lua import Game
    from test_bridge_p06b_lua import collect
    from test_bridge_send_lua import type_and_enter
    from test_bridge_window_lua import history

    game = Game()
    game.slash("/fv")
    type_and_enter(game, CANINE + SLIPPERS + " ?")
    record, _ = collect(game)
    assert record.text == "[Sharp Canine][Mystic's Slippers] ?"
    assert [link.body for link in parse_links(record.context["links"])] == [
        "item:3301::::::::19:1482",
        "item:14364::::::::19:1482",
    ]
    (line,) = [entry for entry in history(game) if "Sharp Canine" in entry]
    assert CANINE in line and SLIPPERS in line and "||" not in line
    saved = game.lua.globals().ForeverBridgeDB.history
    again = Game(saved={"schema": 1, "session": "abc", "next_id": 2,
                        "history": [dict(saved[1].items())]})  # fmt: skip
    again.slash("/fv")
    assert any(CANINE in entry and "||" not in entry for entry in history(again))


def test_a_typed_pipe_stays_escaped_next_to_a_link():
    from test_bridge_addon_lua import Game
    from test_bridge_send_lua import type_and_enter
    from test_bridge_window_lua import history

    game = Game()
    game.slash("/fv")
    type_and_enter(game, CANINE + " ou a||b")
    (line,) = [entry for entry in history(game) if "Sharp Canine" in entry]
    assert CANINE in line and "a||||b" in line


# --- 7. Fenêtre de collage déplaçable -----------------------------------------------------------------------------------


def test_paste_window_moves_by_its_title_and_keeps_its_place():
    """Remplacé à la sonde H (décision 238) : la zone de collage n'est plus une fenêtre à part ; elle est dans le
    panneau d'action unique, collé à droite de la fenêtre principale, qui se déplace et garde sa place."""
    from test_bridge_addon_lua import Game
    from test_bridge_window_lua import window

    game = Game()
    game.slash("/fv")
    lua = game.lua.globals()
    lua.ForeverBridge.OpenPaste()
    panel, box = lua.ForeverBridgePanel, lua.ForeverBridgePasteBox
    assert panel.IsVisible(panel) and box.IsVisible(box)
    point = panel.points[1]
    assert game.lua.eval("rawequal")(point.rel, window(game)) and (point.point, point.relPoint) == (
        "TOPLEFT",
        "TOPRIGHT",
    )
    assert window(game).movable


# --- 8. Aide de /fv -----------------------------------------------------------------------------------------------------

HELP_FIRST = "/fv : ouvrir ou fermer cette fenêtre"


def test_help_is_shown_once_ever_then_on_demand():
    from test_bridge_addon_lua import Game
    from test_bridge_window_lua import history

    game = Game()
    game.slash("/fv")
    assert sum(HELP_FIRST in line for line in history(game)) == 1
    assert game.lua.globals().ForeverBridgeDB.help_shown is True
    again = Game(saved={"schema": 1, "session": "abc", "next_id": 1, "help_shown": True})
    again.slash("/fv")
    assert sum(HELP_FIRST in line for line in history(again)) == 0
    again.slash("/fv aide")
    assert sum(HELP_FIRST in line for line in history(again)) == 1
