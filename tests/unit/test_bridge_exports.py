"""Exports dans le pont (EX1, bloc C) : liens typés `links` d'une réponse (Talents Forever et code Naowh du même
build), `link` gardé pour un addon pas encore rechargé ; bouton « Exports » visible avec EX1 seulement, réponse
rédigée par le pont sans le modèle (agent bouchonné jamais appelé).

Valeurs : contexte réel `tests/fixtures/bridge/contexts/mage19.txt` (talents `nœud:rang` du client), nœuds lus dans
`classes.json` ; résultats d'outils synthétiques (codes factices), aucun chiffre de jeu."""

import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION
from test_bridge_loop import FakeAgent, FakeCapture, band_of, make
from test_bridge_loop_p06b import SESSION, RefusingAgent, replies

from forever.bridge.actions import parse_action
from forever.bridge.agent import AgentResult, parse_stream
from forever.bridge.buttons import DONE_SLICES, button_payload, visible_buttons
from forever.bridge.exports import LABELS, exports_reply, typed_link, typed_links
from forever.bridge.record import Record
from forever.exports.naowh import BUILD_PREFIX, read_naowh_build

TF = "https://talentsforever.com/mage/20/--0530002001-klps-6"
NFB = BUILD_PREFIX + "abcd"
CONTEXT = dict(
    line.split("=", 1)
    for line in (FIXTURES / "bridge" / "contexts" / "mage19.txt").read_text(encoding="utf-8").split("\n")
    if "=" in line
)
CLASSES = json.loads((DATA_DIR / LOCAL_VERSION / "classes.json").read_text(encoding="utf-8"))["classes"]


def stream(tool: str, value: dict) -> list[str]:
    return [
        json.dumps({"type": "system", "session_id": "s1"}),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "tool_use", "id": "t1", "name": f"mcp__forever__{tool}", "input": {}}]
                },
            }
        ),
        json.dumps(
            {
                "type": "user",
                "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": json.dumps(value)}]},
            }
        ),
        json.dumps({"type": "result", "result": "Réponse", "session_id": "s1"}),
    ]


# --- liens typés ----------------------------------------------------------------------------------------------------


def test_build_result_gives_both_links():
    value = {
        "export": {
            "talents_forever": {"status": "ok", "link": TF},
            "naowh": {"status": "ok", "code": NFB},
        }
    }
    assert typed_links(value)["build"] == [typed_link("talents_forever", TF), typed_link("naowh_build", NFB)]
    result = parse_stream(stream("forever_build", value))
    assert result.exports["build"] == [
        {"kind": "talents_forever", "label": LABELS["talents_forever"], "text": TF},
        {"kind": "naowh_build", "label": LABELS["naowh_build"], "text": NFB},
    ]
    assert result.link == TF


def test_blocked_naowh_export_gives_no_naowh_link():
    value = {"export": {"talents_forever": {"status": "ok", "link": TF}, "naowh": {"status": "bloque", "code": None}}}
    assert typed_links(value)["build"] == [typed_link("talents_forever", TF)]


def test_closest_popular_and_build_check_and_export_lookup():
    closest = {"kind": "tf_popular", "closest": {"link": TF, "naowh": {"status": "ordre_genere", "code": NFB}}}
    assert typed_links(closest)["closest"] == [typed_link("talents_forever", TF), typed_link("naowh_build", NFB)]
    check = {"kind": "build_check", "naowh": {"status": "ordre_genere", "code": NFB}}
    assert typed_links(check)["check"] == [typed_link("naowh_build", NFB)]
    made = {"kind": "naowh_build", "status": "ordre_genere", "code": NFB}
    assert typed_links(made)["export"] == [typed_link("naowh_build", NFB)]
    assert typed_links({"kind": "spell"}) == {}


# --- emplacement --------------------------------------------------------------------------------------------------


def test_reply_carries_typed_links_and_keeps_link(tmp_path):
    links = [typed_link("talents_forever", TF), typed_link("naowh_build", NFB)]
    agent = FakeAgent(
        [AgentResult(text="Build", session_id="s1", link=TF, links={"build": TF}, exports={"build": links})]
    )
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, agent)
    capture.band = band_of(Record(SESSION, 1, frozenset(), CONTEXT, "Quel talent ?", slot=1))
    bridge.step()
    reply = replies(addons)[-1]
    assert reply.link == TF
    got = [(reply.links[i].kind, reply.links[i].label, reply.links[i].text) for i in range(1, len(reply.links) + 1)]
    assert got == [(e["kind"], e["label"], e["text"]) for e in links]
    assert bridge.last_exports == links


def test_reply_without_typed_links_has_no_links_field(tmp_path):
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, FakeAgent())
    capture.band = band_of(Record(SESSION, 1, frozenset(), CONTEXT, "Bonjour", slot=1))
    bridge.step()
    assert replies(addons)[-1].links is None


# --- bouton Exports ------------------------------------------------------------------------------------------------


def test_exports_button_visible_with_ex1_only():
    assert "EX1" in DONE_SLICES
    assert "exports" in [b.key for b in visible_buttons()]
    assert "exports" not in [b.key for b in visible_buttons(DONE_SLICES - {"EX1"})]
    (entry,) = [e for e in button_payload(visible_buttons()) if e["key"] == "exports"]
    assert entry["action"] == "exports" and entry["label"] == "Exports"
    assert parse_action("a=exports") == ("exports", None)
    assert parse_action("a=exports:x") is None


def test_exports_action_never_calls_the_agent(tmp_path):
    seen = {}
    links = [typed_link("naowh_build", NFB)]

    def exporter(context, last):
        seen["context"], seen["last"] = dict(context), list(last)
        return "Exports du personnage", links

    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, RefusingAgent())
    bridge.exporter = exporter
    bridge.last_exports = [typed_link("talents_forever", TF)]
    capture.band = band_of(Record(SESSION, 1, frozenset({"a=exports"}), CONTEXT, "", slot=1))
    bridge.step()
    reply = replies(addons)[-1]
    assert reply.status == "done" and reply.text == "Exports du personnage"
    assert reply.links[1].text == NFB
    assert seen["context"]["class"] == "MAGE" and seen["last"] == [typed_link("talents_forever", TF)]


def test_exports_action_without_exporter_is_refused(tmp_path):
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, RefusingAgent())
    capture.band = band_of(Record(SESSION, 1, frozenset({"a=exports"}), CONTEXT, "", slot=1))
    bridge.step()
    assert "Action refusée" in replies(addons)[-1].text


# --- réponse du bouton Exports ---------------------------------------------------------------------------------------


@pytest.fixture
def deps(make_deps):
    return make_deps()


def test_exports_reply_gives_the_current_build_and_the_last_links(deps):
    last = [typed_link("talents_forever", TF), typed_link("naowh_build", NFB)]
    text, links = exports_reply(deps, CONTEXT, last)
    kinds = [link["kind"] for link in links]
    assert kinds.count("naowh_build") == 2 and "talents_forever" in kinds
    current = links[0]
    assert current["kind"] == "naowh_build" and current["label"] != LABELS["naowh_build"]
    build = read_naowh_build(current["text"])
    assert build.class_id == CLASSES["Mage"]["id"]
    ranks = [int(part.split(":")[1]) for part in CONTEXT["talents"].split(",")]
    assert len(build.points) == sum(ranks)
    assert "Naowh" in text and "ordre généré" in text
    assert links[1:] == last


def test_exports_reply_says_what_is_missing(deps):
    text, links = exports_reply(deps, {**CONTEXT, "talents": ""}, [])
    assert links == [] and "aucun talent" in text


def test_exports_reply_needs_the_character(deps):
    text, links = exports_reply(deps, {}, [])
    assert links == [] and "personnage" in text
