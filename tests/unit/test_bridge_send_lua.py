"""Envoi depuis la fenêtre (P06a, bloc B) sous lupa.lua51 : zone de saisie (Entrée envoie, Maj+Entrée passe à la
ligne), « Nouvelle conversation », barre de boutons d'après l'état écrit par le pont, contexte du personnage (sous
pcall et issecretvalue), allègement du message, bande décodée par le pont. Personnage du client simulé : valeurs
synthétiques (aucune règle de jeu)."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_window_lua import history

from forever.bridge.buttons import button_payload, visible_buttons
from forever.bridge.codec import MAX_PAYLOAD, Decoded, decode_band
from forever.bridge.record import Record, build_payload, parse_payload
from forever.bridge.slots import status_lua

pytest.importorskip("lupa")

MAGE_TALENTS = "Quel est mon prochain talent, avec le lien Talents Forever ?"


def with_buttons(game):
    game.lua.execute(status_lua({}, button_payload(visible_buttons())))
    return game


def sent(game) -> tuple[int, Record]:
    decoded = decode_band(game.screen_image())
    assert isinstance(decoded, Decoded), decoded
    return decoded.message_id, parse_payload(decoded.payload)


def type_and_enter(game, text, shift=False):
    lua = game.lua.globals()
    box = lua.ForeverBridgeInput
    box.SetText(box, text)
    game.stub.shift = shift
    box.scripts.OnEnterPressed(box)
    game.stub.shift = False
    return box


def bar(game) -> list[str]:
    lua = game.lua.globals()
    keys = ("talents", "leveling", "pets", "pvp", "gear", "update")
    out = []
    for key in keys:
        button = lua["ForeverBridgeButton_" + key]
        if button is not None and button.IsShown(button):
            out.append(key)
    return out


def click(game, name):
    button = game.lua.globals()[name]
    button.scripts.OnClick(button)


def test_enter_sends_the_question_with_its_context():
    game = Game(screen=(2560, 1440))
    game.slash("/fv")
    box = type_and_enter(game, "Quel talent au niveau 20 ?")
    assert box.GetText(box) == ""
    message_id, record = sent(game)
    db = game.lua.globals().ForeverBridgeDB
    assert message_id == 1 and record.message_id == 1 and db.next_id == 2
    assert record.session == db.session and record.slot == 1
    assert record.text == "Quel talent au niveau 20 ?" and record.flags == frozenset()
    ctx = record.context
    assert (ctx["name"], ctx["realm"], ctx["level"], ctx["class"], ctx["race"]) == (
        "Jen", "Forever", "19", "MAGE", "Human",
    )  # fmt: skip
    assert (ctx["faction"], ctx["zone"], ctx["subzone"], ctx["map"]) == (
        "Alliance", "Westfall", "Sentinel Hill", "1436",
    )  # fmt: skip
    assert ctx["talents"] == "101:2,102:3,140:1"
    assert ctx["gear"] == "1:12345:Hat of Testing;5:23456:Robe of Testing"
    assert ctx["client"] == "1.60.1.70291" and "target" not in ctx
    assert any("Vous" in line and "Quel talent au niveau 20 ?" in line for line in history(game))
    assert list(game.stub.printed.values()) == []


def test_shift_enter_adds_a_line_and_escape_clears_focus():
    game = Game()
    game.slash("/fv")
    box = type_and_enter(game, "ligne 1", shift=True)
    assert box.GetText(box) == "ligne 1\n"
    assert decode_band(game.screen_image()) is None
    box.SetFocus(box)
    box.scripts.OnEscapePressed(box)
    assert not box.HasFocus(box)
    assert box.maxLetters == 255 and box.multiLine
    type_and_enter(game, "   ")
    assert decode_band(game.screen_image()) is None


def test_send_button_and_ids_follow_each_other():
    game = Game()
    game.slash("/fv")
    lua = game.lua.globals()
    lua.ForeverBridgeInput.SetText(lua.ForeverBridgeInput, "Première")
    click(game, "ForeverBridgeSendButton")
    assert sent(game)[1].text == "Première"
    type_and_enter(game, "Seconde")
    message_id, record = sent(game)
    assert message_id == 2 and record.text == "Seconde"


def test_new_conversation_flags_only_the_next_message():
    game = Game()
    game.slash("/fv")
    click(game, "ForeverBridgeNewButton")
    assert any("Nouvelle conversation" in line for line in history(game))
    type_and_enter(game, "Un")
    assert sent(game)[1].flags == frozenset({"n"})
    type_and_enter(game, "Deux")
    assert sent(game)[1].flags == frozenset()


def test_band_is_provisional_until_block_e():
    game = Game()
    game.slash("/fv")
    type_and_enter(game, "Question")
    game.stub.Advance(29)
    assert decode_band(game.screen_image()) is not None
    game.stub.Advance(2)
    assert decode_band(game.screen_image()) is None
    assert any("bloc E" in line for line in history(game))


def test_no_buttons_before_the_bridge_writes_its_state():
    game = Game()
    game.slash("/fv")
    assert bar(game) == []


def test_buttons_for_a_mage():
    game = with_buttons(Game())
    game.slash("/fv")
    assert bar(game) == ["talents", "leveling", "pvp"]
    click(game, "ForeverBridgeButton_talents")
    _, record = sent(game)
    assert record.text == MAGE_TALENTS and record.flags == frozenset({"b=talents"})


def test_buttons_for_a_hunter():
    game = Game()
    game.stub.player.__setitem__("class", "HUNTER")
    with_buttons(game)
    game.slash("/fv")
    assert bar(game) == ["talents", "pets", "pvp"]
    click(game, "ForeverBridgeButton_talents")
    _, record = sent(game)
    assert "build populaire" in record.text and record.context["class"] == "HUNTER"
    click(game, "ForeverBridgeButton_pets")
    assert sent(game)[1].text == "Où apprivoiser le prochain rang utile près de moi ?"


def test_pvp_needs_a_player_target():
    game = with_buttons(Game())
    game.slash("/fv")
    click(game, "ForeverBridgeButton_pvp")
    assert decode_band(game.screen_image()) is None
    assert any("joueur en cible" in line for line in history(game))
    game.stub.player.target = "ROGUE"
    click(game, "ForeverBridgeButton_pvp")
    _, record = sent(game)
    assert record.text == "Fiche de la classe de ma cible" and record.context["target"] == "ROGUE"
    assert record.flags == frozenset({"b=pvp"})


def test_failing_or_secret_apis_leave_keys_out():
    game = Game()
    for name in ("C_Traits.GetNodeInfo", "GetInventoryItemLink"):
        game.stub.failing[name] = True
    game.stub.secret["UnitRace"] = True
    game.stub.secret["GetRealZoneText"] = True
    game.slash("/fv")
    type_and_enter(game, "Question")
    ctx = sent(game)[1].context
    assert "race" not in ctx and "zone" not in ctx and "gear" not in ctx
    assert ctx.get("talents", "") == "" and ctx["level"] == "19"


def heavy_player(game, nodes, name_len, pieces=19):
    player = game.stub.player
    lua = game.lua
    node_list = lua.table(*[10000 + i for i in range(nodes)])
    player.nodes = lua.table_from({1: node_list})
    player.ranks = lua.table_from({10000 + i: 3 for i in range(nodes)})
    gear = {
        slot: f"|cffffffff|Hitem:{20000 + slot}::::::::19:::::|h[{'N' * name_len}]|h|r" for slot in range(1, pieces + 1)
    }
    player.gear = lua.table_from(gear)


def test_long_item_names_are_cut_first():
    game = Game()
    heavy_player(game, nodes=51, name_len=60)
    game.slash("/fv")
    question = "é" * 255
    type_and_enter(game, question)
    _, record = sent(game)
    assert record.text == question
    assert len(build_payload(record)) <= MAX_PAYLOAD
    names = [piece.split(":", 2)[2] for piece in record.context["gear"].split(";")]
    assert len(names) == 19 and all(0 < len(n) <= 20 for n in names)
    assert record.context["subzone"] == "Sentinel Hill"


def test_gear_goes_last_and_the_question_is_never_cut():
    game = Game()
    heavy_player(game, nodes=130, name_len=60)
    game.slash("/fv")
    question = "é" * 255
    type_and_enter(game, question)
    _, record = sent(game)
    assert record.text == question and len(build_payload(record)) <= MAX_PAYLOAD
    ctx = record.context
    assert "talents" in ctx and "gear" not in ctx and "subzone" not in ctx
    ids_only = ";".join(f"{slot}:{20000 + slot}" for slot in range(1, 20))
    with_ids = Record(
        record.session, record.message_id, record.flags, {**ctx, "gear": ids_only}, record.text, record.slot
    )
    assert len(build_payload(with_ids)) > MAX_PAYLOAD  # précondition : il fallait bien retirer l'équipement


def test_no_forbidden_call_while_sending():
    game = with_buttons(Game())
    game.slash("/fv")
    type_and_enter(game, "Question")
    click(game, "ForeverBridgeButton_talents")
    click(game, "ForeverBridgeNewButton")
    game.stub.Advance(40)
    assert list(game.stub.forbidden.values()) == []
    assert list(game.stub.printed.values()) == []


def test_realistic_french_question_is_sent_with_the_full_context():
    """Demande de l'utilisateur du 2026-10-09 : question en français, accents compris, contexte complet sans
    allègement (51 rangs de talents, 17 pièces d'équipement aux noms de longueur courante)."""
    from test_bridge_record import FRENCH_QUESTION

    game = Game()
    heavy_player(game, nodes=51, name_len=30, pieces=17)
    game.slash("/fv")
    type_and_enter(game, FRENCH_QUESTION)
    _, record = sent(game)
    assert record.text == FRENCH_QUESTION
    names = [piece.split(":", 2)[2] for piece in record.context["gear"].split(";")]
    assert len(names) == 17 and all(len(n) == 30 for n in names)
    assert record.context["subzone"] == "Sentinel Hill" and len(record.context["talents"].split(",")) == 51


def test_cell_size_of_messages_is_set_by_fv_case():
    """Plan, R2 : `/fv case N` règle la taille de case des messages (1 à 4), gardée dans ForeverBridgeDB.cell."""
    from forever.bridge.codec import detect_cell_px

    game = Game()
    game.slash("/fv case 2")
    assert game.lua.globals().ForeverBridgeDB.cell == 2
    type_and_enter(game, "Question")
    assert detect_cell_px(game.screen_image()) == 2
    game.slash("/fv case 9")
    assert game.lua.globals().ForeverBridgeDB.cell == 2
    assert any("case" in line and "1, 2, 3 ou 4" in line for line in history(game))
    assert list(game.stub.printed.values()) == []
