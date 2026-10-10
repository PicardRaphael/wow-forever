"""ForeverBridge en P06b (bloc A, décision 235), vrai Lua sous lupa.lua51 avec le client simulé : liens par Maj+clic
(accroches `hooksecurefunc`), liens et infobulles envoyés dans `links`, équipement complet, messages en parties
montrés en carrousel puis réassemblés par le pont, zone de collage de l'export SimulationCraft, cartes « À valider »
avec second clic de confirmation, aucune fonction interdite. Personnage, liens et infobulles du client simulé :
valeurs synthétiques (aucune règle de jeu)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

from forever.bridge.codec import Decoded, decode_band
from forever.bridge.fragments import MAX_MESSAGE, FragmentBuffer, parse_fragment
from forever.bridge.items import parse_gear, parse_links
from forever.bridge.record import Record, parse_payload
from forever.bridge.slots import inbox_lua

pytest.importorskip("lupa")

SWORD = "|cff1eff00|Hitem:7909:1883:0:0:0:0:-12:1234567:19:::::|h[Sword of the Bear]|h|r"
FROSTBOLT = "|cff71d5ff|Hspell:116:0|h[Frostbolt]|h|r"
QUEST = "|cffffff00|Hquest:1234:20|h[The Test Quest]|h|r"
SWORD_TIP = ["Sword of the Bear", "Binds when equipped", "Main Hand", "Requires Level 19"]
CARD_UPDATE = {
    "id": "measures-70338",
    "kind": "update",
    "title": "Mesures à valider",
    "lines": ["PNJ changés : Hogger", "Builds changés : aucun"],
    "buttons": [
        {"key": "approve", "label": "Valider", "action": "approve:measures-70338", "confirm": True},
        {"key": "reject", "label": "Refuser", "action": "reject:measures-70338", "confirm": True},
        {"key": "explain", "label": "Expliquer", "explain": True},
    ],
}
CARD_NETWORK = {
    "id": "network-70338",
    "kind": "update",
    "title": "Attente réseau",
    "lines": ["attente réseau : se lève seule au prochain passage réussi"],
    "buttons": [{"key": "explain", "label": "Expliquer", "explain": True}],
}


def waiting_slots(game, upto=40):
    """Emplacements d'attente (jamais publiés) : chargés sans rien apporter, la réserve ne s'épuise pas."""
    for index in range(1, upto + 1):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(0, {}, [], [])


def tooltip(game, body, lines):
    game.stub.tooltips[body] = game.lua.table(*lines)


def read_band(game):
    decoded = decode_band(game.screen_image())
    return decoded.payload if isinstance(decoded, Decoded) else None


def collect(game, limit=60) -> tuple[Record, set[int]]:
    """Message lu sur la bande comme le pont le lit : une bande, ou des parties réassemblées au fil du carrousel."""
    buffer = FragmentBuffer()
    shown: set[int] = set()
    for _ in range(limit):
        payload = read_band(game)
        if payload is not None:
            fragment = parse_fragment(payload)
            if fragment is None:
                return parse_payload(payload), shown
            shown.add(fragment.index)
            full = buffer.add(fragment)
            if full is not None:
                return parse_payload(full), shown
        game.stub.Advance(0.25, 0.05)
    raise AssertionError(f"message incomplet : parties vues {sorted(shown)}")


def shown_part(game):
    payload = read_band(game)
    if payload is None:
        return None
    fragment = parse_fragment(payload)
    return fragment.index if fragment else 0


def heavy(game, *, nodes=51, name_len=60, pieces=19):
    lua = game.lua
    player = game.stub.player
    player.nodes = lua.table_from({1: lua.table(*[10000 + i for i in range(nodes)])})
    player.ranks = lua.table_from({10000 + i: 3 for i in range(nodes)})
    player.gear = lua.table_from(
        {
            slot: f"|cffffffff|Hitem:{20000 + slot}:1883:0:0:0:0:-12:1234567:19:::::|h[{'N' * name_len}]|h|r"
            for slot in range(1, pieces + 1)
        }
    )


# --- 1. Maj+clic ----------------------------------------------------------------------------------------------------


def test_shift_click_inserts_the_link_when_our_input_has_focus():
    game = Game()
    game.slash("/fv")
    lua = game.lua.globals()
    box = lua.ForeverBridgeInput
    box.SetFocus(box)
    lua.ChatFrameUtil.InsertLink(SWORD)
    assert box.GetText(box) == SWORD
    lua.ChatEdit_InsertLink(FROSTBOLT)
    assert box.GetText(box) == SWORD + FROSTBOLT
    box.ClearFocus(box)
    lua.ChatEdit_InsertLink(QUEST)
    assert box.GetText(box) == SWORD + FROSTBOLT


def test_a_click_that_goes_through_both_hooks_inserts_once():
    prelude = "Stub.chained_insert = true"
    game = Game(prelude=prelude)
    game.slash("/fv")
    lua = game.lua.globals()
    box = lua.ForeverBridgeInput
    box.SetFocus(box)
    lua.ChatFrameUtil.InsertLink(SWORD)
    assert box.GetText(box) == SWORD


def test_missing_hooks_are_not_an_error():
    game = Game(prelude="ChatFrameUtil = nil; ChatEdit_InsertLink = nil")
    game.slash("/fv")
    type_and_enter(game, "Question")
    assert read_band(game) is not None
    assert list(game.stub.forbidden.values()) == []


# --- 2. Liens et infobulles -----------------------------------------------------------------------------------------


def test_links_are_named_in_the_question_and_sent_with_their_tooltip():
    game = Game()
    tooltip(game, "item:7909:1883:0:0:0:0:-12:1234567:19:::::", SWORD_TIP)
    tooltip(game, "spell:116:0", ["Frostbolt", "|cffffffffLaunches|r a bolt of frost.", "x" * 200])
    game.slash("/fv")
    type_and_enter(game, f"Compare {SWORD} et {FROSTBOLT} ?")
    record, _ = collect(game)
    assert record.text == "Compare [Sword of the Bear] et [Frostbolt] ?"
    links = parse_links(record.context["links"])
    assert [(link.kind, link.body, link.name) for link in links] == [
        ("item", "item:7909:1883:0:0:0:0:-12:1234567:19", "Sword of the Bear"),
        ("spell", "spell:116", "Frostbolt"),
    ]
    assert list(links[0].tooltip) == SWORD_TIP
    assert links[1].tooltip[:2] == ("Frostbolt", "Launches a bolt of frost.")
    assert links[1].tooltip[2] == "x" * 120


def test_tooltips_are_cut_and_at_most_eight_links_are_sent():
    game = Game()
    waiting_slots(game)
    bodies = [f"item:{30000 + i}" for i in range(9)]
    for body in bodies:
        tooltip(game, body, [f"ligne {n} " + "y" * 150 for n in range(40)])
    game.slash("/fv")
    text = " ".join(f"|cffffffff|H{body}|h[Objet {i}]|h|r" for i, body in enumerate(bodies))
    type_and_enter(game, text)
    record, _ = collect(game)
    links = parse_links(record.context["links"])
    assert [link.body for link in links] == bodies[:8]
    assert all(len(link.tooltip) == 30 and all(len(line) <= 120 for line in link.tooltip) for link in links)
    assert record.text == " ".join(f"[Objet {i}]" for i in range(9))


def test_unreadable_tooltip_leaves_the_link_without_lines():
    game = Game()
    game.stub.failing["C_TooltipInfo.GetHyperlink"] = True
    game.slash("/fv")
    type_and_enter(game, f"Et {QUEST} ?")
    record, _ = collect(game)
    (link,) = parse_links(record.context["links"])
    assert (link.kind, link.body, link.name, link.tooltip) == ("quest", "quest:1234:20", "The Test Quest", ())


def test_input_accepts_a_thousand_letters():
    game = Game()
    game.slash("/fv")
    assert game.lua.globals().ForeverBridgeInput.maxLetters == 1000


# --- 3. Équipement complet ------------------------------------------------------------------------------------------


def test_gear_carries_the_full_item_string():
    game = Game()
    game.stub.player.gear[16] = SWORD
    game.slash("/fv")
    type_and_enter(game, "Question")
    record, _ = collect(game)
    pieces, bad = parse_gear(record.context["gear"])
    assert bad == []
    sword = next(p for p in pieces if p.slot == 16)
    assert sword.chain == "7909:1883:0:0:0:0:-12:1234567:19" and sword.item.suffix == -12
    assert sword.name == "Sword of the Bear"
    assert ":-12:" in record.context["gear"]


# --- 4. Message trop gros : parties ---------------------------------------------------------------------------------


def test_heavy_message_goes_in_parts_with_nothing_removed_but_names():
    game = Game()
    waiting_slots(game)
    heavy(game)
    bodies = [f"item:{40000 + i}" for i in range(8)]
    for body in bodies:
        tooltip(game, body, ["z" * 100] * 30)
    game.slash("/fv")
    question = "é" * 200 + " " + " ".join(f"|cffffffff|H{body}|h[O{i}]|h|r" for i, body in enumerate(bodies))
    type_and_enter(game, question)
    record, shown = collect(game)
    assert len(shown) > 2
    assert record.text.startswith("é" * 200) and record.text.endswith("[O7]")
    assert len(record.context["talents"].split(",")) == 51
    pieces, _ = parse_gear(record.context["gear"])
    assert [p.slot for p in pieces] == list(range(1, 20)) and all(p.item.suffix == -12 for p in pieces)
    assert len(parse_links(record.context["links"])) == 8


# --- 5. Carrousel ---------------------------------------------------------------------------------------------------


def session(game):
    return game.lua.globals().ForeverBridgeDB.session


def put(game, index, replies):
    game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(1791547200, {"slots": 40}, replies, [])


def bulky_question(game):
    """Question avec trois liens d'infobulle longue : trois parties."""
    bodies = [f"item:{50000 + i}" for i in range(3)]
    for body in bodies:
        tooltip(game, body, ["t" * 50] * 30)
    return "Compare " + " ".join(f"|cffffffff|H{body}|h[B{i}]|h|r" for i, body in enumerate(bodies))


def test_carousel_shows_each_part_then_only_the_missing_ones():
    game = Game()
    waiting_slots(game)
    game.slash("/fv")
    put(game, 1, [{"session": session(game), "id": 1, "status": "parts", "got": [1, 3], "total": 3}])
    put(game, 2, [{"session": session(game), "id": 1, "status": "working", "since": 0}])
    type_and_enter(game, bulky_question(game))
    assert parse_fragment(read_band(game)).total == 3
    seen = []
    for _ in range(4):
        seen.append(shown_part(game))
        game.stub.Advance(0.5, 0.05)
    assert seen == [1, 2, 3, 1]  # premier relevé à 2 s : parties 1 et 3 reçues
    game.stub.Advance(0.1, 0.05)
    after = []
    for _ in range(3):
        after.append(shown_part(game))
        game.stub.Advance(0.5, 0.05)
    assert after == [2, 2, 2]
    game.stub.Advance(0.6, 0.05)  # deuxième relevé à 4 s : accusé
    assert read_band(game) is None


def test_three_polls_without_a_new_part_go_to_the_outbox():
    game = Game()
    game.slash("/fv")
    for index in range(1, 11):
        put(game, index, [{"session": session(game), "id": 1, "status": "parts", "got": [1], "total": 2}])
    type_and_enter(game, "é" * 1000 + "fin")
    assert parse_fragment(read_band(game)) is not None
    game.stub.Advance(11.0, 0.1)  # relevés à 2 (partie nouvelle), 4, 8
    assert read_band(game) is not None
    game.stub.Advance(1.2, 0.1)  # relevé à 12 : troisième sans partie nouvelle
    assert read_band(game) is None
    entry = game.lua.globals().ForeverBridgeDB.outbox[1]
    assert entry.id == 1 and entry.text == "é" * 1000 + "fin"
    assert any("pont injoignable" in line for line in history(game))


# --- 6. Zone de collage ---------------------------------------------------------------------------------------------


def paste(game, text):
    lua = game.lua.globals()
    lua.ForeverBridge.OpenPaste()
    box = lua.ForeverBridgePasteBox
    assert box.IsVisible(box) and box.multiLine and not box.maxLetters
    box.SetText(box, text)
    send = lua.ForeverBridgePasteSend
    send.scripts.OnClick(send)
    return box


def test_paste_sends_the_export_in_parts():
    game = Game()
    waiting_slots(game)
    game.slash("/fv")
    lua = game.lua.globals()
    opener = lua.ForeverBridgePasteButton
    assert opener is not None and opener.IsShown(opener)
    export = "\n".join(f"# ligne {n:05d} " + "s" * 60 for n in range(200))[:15000]
    paste(game, export)
    record, shown = collect(game)
    assert record.flags == frozenset({"k=simc"}) and record.text == export
    assert len(shown) == 9
    assert any("export SimulationCraft" in line for line in history(game))
    assert not any("s" * 60 in line for line in history(game))


def test_too_long_export_is_refused():
    game = Game()
    game.slash("/fv")
    before = int(game.lua.globals().ForeverBridgeDB.next_id)
    box = paste(game, "a" * (MAX_MESSAGE + 1))
    assert read_band(game) is None
    assert int(game.lua.globals().ForeverBridgeDB.next_id) == before
    assert any("export trop long : utilisez /simc nobags" in line for line in history(game))
    assert box.GetText(box) == "a" * (MAX_MESSAGE + 1)


# --- 8. Cartes « À valider » ----------------------------------------------------------------------------------------


def with_cards(game, cards):
    game.stub.addons["ForeverBridge_S001"] = inbox_lua(1791547200, {"slots": 40}, [], [], cards)
    game.lua.globals().ForeverBridge.PollSlot()


def card_button(game, index, key):
    return game.lua.globals()[f"ForeverBridgeCard{index}_{key}"]


def click(button):
    button.scripts.OnClick(button)


def test_cards_are_rendered_with_their_buttons():
    game = Game()
    game.slash("/fv")
    with_cards(game, [CARD_UPDATE, CARD_NETWORK])
    lua = game.lua.globals()
    opener = lua.ForeverBridgeCardsButton
    assert opener.IsShown(opener) and "À valider (2)" in opener.GetText(opener)
    click(opener)
    text = lua.ForeverBridgeCard1Text
    assert "Mesures à valider" in text.GetText(text) and "PNJ changés : Hogger" in text.GetText(text)
    assert card_button(game, 1, "approve").IsShown(card_button(game, 1, "approve"))
    assert card_button(game, 2, "explain").IsShown(card_button(game, 2, "explain"))
    approve2 = card_button(game, 2, "approve")
    assert approve2 is None or not approve2.IsShown(approve2)


def test_static_status_carries_cards_after_a_reload():
    from forever.bridge.slots import status_lua

    game = Game()
    game.lua.execute(status_lua({"line": "Données"}, [], 1791547200, [CARD_NETWORK]))
    game.stub.Fire("PLAYER_ENTERING_WORLD", False, True)
    game.slash("/fv")
    opener = game.lua.globals().ForeverBridgeCardsButton
    assert "À valider (1)" in opener.GetText(opener)


def test_approve_needs_a_second_click_within_five_seconds():
    game = Game()
    waiting_slots(game)
    game.slash("/fv")
    with_cards(game, [CARD_UPDATE])
    click(game.lua.globals().ForeverBridgeCardsButton)
    approve = card_button(game, 1, "approve")
    click(approve)
    assert approve.GetText(approve) == "Confirmer" and read_band(game) is None
    game.stub.Advance(6.0, 0.1)
    assert approve.GetText(approve) == "Valider"
    click(approve)
    assert read_band(game) is None
    game.stub.Advance(1.0, 0.1)
    click(approve)
    record, _ = collect(game)
    assert record.flags == frozenset({"a=approve:measures-70338"}) and record.text == ""


def test_reject_and_explain():
    game = Game()
    waiting_slots(game)
    game.slash("/fv")
    with_cards(game, [CARD_UPDATE])
    click(game.lua.globals().ForeverBridgeCardsButton)
    reject = card_button(game, 1, "reject")
    click(reject)
    click(reject)
    record, _ = collect(game)
    assert record.flags == frozenset({"a=reject:measures-70338"})
    game.stub.Advance(1.0)
    click(card_button(game, 1, "explain"))
    record, _ = collect(game)
    assert record.message_id == 2
    assert record.flags == frozenset({"b=explain"})
    assert record.text.startswith("Explique cette mise à jour en attente, simplement")
    assert "Mesures à valider" in record.text and "PNJ changés : Hogger" in record.text


# --- 11. Règles -----------------------------------------------------------------------------------------------------


def test_no_forbidden_call_in_the_new_paths():
    game = Game()
    waiting_slots(game)
    tooltip(game, "spell:116:0", ["Frostbolt"])
    game.slash("/fv")
    lua = game.lua.globals()
    box = lua.ForeverBridgeInput
    box.SetFocus(box)
    lua.ChatEdit_InsertLink(FROSTBOLT)
    type_and_enter(game, box.GetText(box))
    with_cards(game, [CARD_UPDATE])
    click(lua.ForeverBridgeCardsButton)
    click(card_button(game, 1, "approve"))
    click(card_button(game, 1, "approve"))
    paste(game, "export")
    game.stub.Advance(30, 0.25)
    assert list(game.stub.forbidden.values()) == []
    assert list(game.stub.printed.values()) == []
    assert not any(str(event).startswith("COMBAT_LOG") for event in game.stub.registered)
