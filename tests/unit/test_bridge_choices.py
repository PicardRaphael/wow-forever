"""Questions à choix et feuille de route dans le pont (RX1, bloc E, décisions 243 et 258) : carte d'une question,
réponse appariée exactement et transmise en texte fixe à la conversation, réponse inconnue refusée, bouton
« Feuille de route » visible avec RX1 pour toutes les classes, livraison d'une route à RestedXP par l'emplacement.
Contexte réel `contexts/mage19.txt` ; aucun `claude` réel."""

import json

from conftest import FIXTURES, read_json
from test_bridge_loop import FakeAgent, FakeCapture, band_of, events, make, slot_table
from test_bridge_loop_p06b import SESSION, replies
from test_bridge_profile_gap import context

from forever.bridge.buttons import BUTTONS, DONE_SLICES, visible_buttons
from forever.bridge.choices import ROUTE_CHOICES, answer_text, choice_card, find_answer
from forever.bridge.record import Record

PLAN = read_json(FIXTURES / "rxp" / "plan.json")


def setup_bridge(tmp_path, agent=None):
    agent = agent or FakeAgent()
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, agent)
    state = {"id": 0}

    def send(flags=(), text="Quel talent ?"):
        state["id"] += 1
        capture.band = band_of(Record(SESSION, state["id"], frozenset(flags), context(), text, slot=1))
        bridge.step()
        return replies(addons)[-1]

    def cards():
        bridge.step()
        slot = slot_table(addons, 1)
        return [slot.cards[i] for i in range(1, len(slot.cards or {}) + 1)]

    return bridge, addons, agent, send, cards


def test_choice_payload():
    choice = ROUTE_CHOICES[1]
    card = choice_card(choice)
    assert card["id"] == f"choice-{choice.id}" and card["kind"] == "choice" and card["title"] == choice.prompt
    assert [b["label"] for b in card["buttons"]] == [o.label for o in choice.options]
    assert [b["action"] for b in card["buttons"]] == [f"choice:{choice.id}.{o.key}" for o in choice.options]
    assert find_answer(ROUTE_CHOICES, f"{choice.id}.{choice.options[1].key}") == (choice, choice.options[1])
    assert find_answer(ROUTE_CHOICES, f"{choice.id}.inconnue") is None
    assert answer_text(choice.options[1]) == f"Réponse : {choice.options[1].label}"


def test_route_button_visible_when_rx1_done():
    keys = {b.key for b in BUTTONS if "RX1" in b.requires}
    assert "route" in keys and "route_deliver" not in keys  # CJ1 : plus de bouton séparé (décision 276)
    assert all(b.classes is None for b in BUTTONS if b.key in keys)  # toutes les classes
    assert not keys & {b.key for b in visible_buttons(DONE_SLICES - {"RX1"})}
    assert keys <= {b.key for b in visible_buttons(DONE_SLICES | {"RX1"})}
    assert "RX1" in DONE_SLICES  # première version faite (bloc E)


def test_route_button_publishes_the_choices(tmp_path):
    _bridge, _addons, agent, send, cards = setup_bridge(tmp_path)
    send(flags={"b=route"}, text="Prépare ma feuille de route.")
    assert agent.calls  # la conversation est prévenue (consigne du bouton)
    assert not [c.id for c in cards() if c.id.startswith("choice-")]  # CJ1 : plus de question dans À valider


def test_choice_click_sends_answer(tmp_path):
    _bridge, _addons, agent, send, cards = setup_bridge(tmp_path)
    send(flags={"b=route"}, text="Prépare ma feuille de route.")
    calls = len(agent.calls)
    choice = ROUTE_CHOICES[1]
    send(flags={f"a=choice:{choice.id}.{choice.options[1].key}"}, text="")
    assert len(agent.calls) == calls + 1
    assert agent.calls[-1][0].rstrip().endswith(f"Réponse : {choice.options[1].label}")
    assert f"choice-{choice.id}" not in [c.id for c in cards()]  # question retirée une fois répondue


def test_choice_unknown_key_refused(tmp_path):
    _bridge, _addons, agent, send, _cards = setup_bridge(tmp_path)
    send(flags={"b=route"}, text="Prépare ma feuille de route.")
    calls = len(agent.calls)
    reply = send(flags={"a=choice:route_dungeons.peut-etre"}, text="")
    assert len(agent.calls) == calls and reply.text.startswith("Action refusée")
    refused = [e for e in events(tmp_path) if e.get("event") == "action" and e.get("action") == "choice"]
    assert refused and refused[-1]["result"] == "refusée"
    reply = send(flags={"a=choice:autre_question.oui"}, text="")
    assert len(agent.calls) == calls and reply.text.startswith("Action refusée")


def test_route_deliver_puts_the_guide_in_the_slot(tmp_path):
    from forever.rxp import encode_guide

    bridge, addons, agent, send, _cards = setup_bridge(tmp_path)
    reply = send(flags={"a=route_deliver"}, text="")
    assert "Aucune feuille de route" in reply.text and slot_table(addons, 1).guide is None
    routes = tmp_path / "routes"
    routes.mkdir()
    (routes / f"{PLAN['id']}.json").write_text(json.dumps(PLAN), encoding="utf-8")
    bridge.routes_dir = routes
    calls = len(agent.calls)
    reply = send(flags={"a=route_deliver"}, text="")
    assert len(agent.calls) == calls and "RestedXP" in reply.text
    guide = slot_table(addons, 1).guide
    from forever.route import guide_name

    name = guide_name(PLAN)
    assert guide.name == name and guide.text == encode_guide(PLAN, name=name, group=guide.group) and guide.sha
