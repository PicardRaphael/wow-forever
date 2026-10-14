"""Liens d'export dans ForeverBridge 0.4.0 (EX1, bloc C), sous lupa.lua51 : une réponse qui porte des liens typés
(`links`) les imprime chacun, cliquables, et chaque clic ouvre la boîte de copie du panneau avec **sa** chaîne ;
`/fb exports` réimprime les liens d'export de la session ; un emplacement ancien (seulement `link`) imprime toujours
`[Talents Forever]` ; le bouton « Exports » envoie l'action `a=exports` sans texte. Chaînes synthétiques."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_p06b_lua import collect, waiting_slots
from test_bridge_reply_lua import STATUS, fill, reply
from test_bridge_send_lua import type_and_enter
from test_bridge_window_lua import history

from forever.bridge.buttons import button_payload, visible_buttons
from forever.bridge.slots import status_lua

pytest.importorskip("lupa")

TF = "https://talentsforever.com/mage/20/--0530002001-klps-6"
NFB = "!NFB1!abcdEFGH0123()"
LINKS = [
    {"kind": "talents_forever", "label": "Talents Forever", "text": TF},
    {"kind": "naowh_build", "label": "Naowh : build", "text": NFB},
]


def link_of(line: str) -> str:
    return line.split("|H", 1)[1].split("|h", 1)[0]


def click(game, line: str) -> str:
    frame = game.lua.globals().ForeverBridgeHistory
    frame.scripts.OnHyperlinkClick(frame, link_of(line), "", "LeftButton")
    box = game.lua.globals().ForeverBridgeCopyBox
    assert box.IsVisible(box)
    return str(box.GetText(box))


def answered(game, **extra):
    game.slash("/fv")
    fill(game, [reply(game, "done", text="Build", provenance="p", **extra)])
    type_and_enter(game, "Question")
    game.stub.Advance(4)


def test_each_typed_link_is_printed_and_copies_its_own_text():
    game = Game()
    answered(game, link=TF, links=LINKS)
    lines = history(game)
    tf = [line for line in lines if "[Talents Forever]" in line]
    nfb = [line for line in lines if "[Naowh : build]" in line]
    assert len(tf) == 1 and len(nfb) == 1
    assert "|Hforeverbridge:copy:" in tf[0] and "|Hforeverbridge:copy:" in nfb[0]
    assert click(game, nfb[0]) == NFB
    assert click(game, tf[0]) == TF


def test_old_slot_with_link_only_still_prints_talents_forever():
    game = Game()
    answered(game, link=TF)
    (line,) = [line for line in history(game) if "[Talents Forever]" in line]
    assert click(game, line) == TF
    assert not [line for line in history(game) if "[Naowh" in line]


def test_fb_exports_reprints_the_session_links():
    game = Game()
    game.slash("/fv")
    game.slash("/fb exports")
    assert any("aucun export" in line for line in history(game))
    answered(game, link=TF, links=LINKS)
    before = len(history(game))
    game.slash("/fb exports")
    again = history(game)[before:]
    nfb = [line for line in again if "[Naowh : build]" in line]
    assert len(nfb) == 1 and any("[Talents Forever]" in line for line in again)
    assert click(game, nfb[0]) == NFB


def test_links_are_kept_in_the_history():
    game = Game()
    answered(game, link=TF, links=LINKS)
    db = game.lua.globals().ForeverBridgeDB
    entries = [e for e in db.history.values() if e.role == "assistant"]
    kept = entries[-1].links
    assert [kept[i].text for i in range(1, len(kept) + 1)] == [TF, NFB]


def test_exports_button_sends_an_action_without_text():
    game = Game()
    waiting_slots(game)
    game.lua.execute(status_lua(STATUS, button_payload(visible_buttons()), 1791547200))
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    button = game.lua.globals().ForeverBridgeButton_exports
    assert button is not None and button.IsShown(button)
    button.scripts.OnClick(button)
    record, _ = collect(game)
    assert record.flags == frozenset({"a=exports"}) and record.text == ""
