"""CJ1, bloc 2 (décisions 276 et 277) : conversation de la feuille de route. La question en cours part avec la réponse,
sous le message, avec ses boutons (une à la fois), plus jamais en carte de « À valider » ; sous l'aperçu, « Valider et
livrer » livre d'office dans RestedXP la route du personnage sous un nom stable (« Forever · <personnage> · a-b »),
et la réponse dit où la trouver ; le modèle reçoit le nombre et le titre des cartes « À valider » réellement publiées.

Contexte réel `contexts/mage19.txt` ; aucun `claude` réel ; plan de fixture `tests/fixtures/rxp/plan.json`."""

import json

from conftest import FIXTURES, read_json
from test_bridge_choices import setup_bridge
from test_bridge_loop import slot_table

from forever.bridge.choices import ROUTE_CHOICES
from forever.route import guide_name

PLAN = read_json(FIXTURES / "rxp" / "plan.json")


def _buttons(reply):
    choices = reply.choices
    assert choices is not None
    return [choices.buttons[i] for i in range(1, len(choices.buttons) + 1)]


def test_stable_guide_name():
    mine = {**PLAN, "request": {**PLAN.get("request", {}), "character": "Bob"}}
    lv = PLAN["levels"]
    assert guide_name(mine) == f"Forever · Bob · {lv['from']}-{lv['to']}"
    anonymous = {**PLAN, "request": {k: v for k, v in PLAN.get("request", {}).items() if k != "character"}}
    assert guide_name(anonymous) == f"Forever · {PLAN['class'].capitalize()} · {lv['from']}-{lv['to']}"


def test_route_question_comes_under_the_reply_one_at_a_time(tmp_path):
    _bridge, _addons, _agent, send, cards = setup_bridge(tmp_path)
    reply = send(flags={"b=route"}, text="Prépare ma feuille de route.")
    assert not [c for c in cards() if str(c.id).startswith("choice-")]
    buttons = _buttons(reply)
    first = ROUTE_CHOICES[0]
    assert reply.choices.prompt == first.prompt
    actions = [b.action for b in buttons]
    assert [f"choice:{first.id}.{o.key}" for o in first.options] == [a for a in actions if a.startswith("choice:")]
    assert "route_deliver" in actions  # « Valider et livrer » sous l'aperçu
    labels = [b.label for b in buttons]
    assert "Valider et livrer" in labels


def test_after_the_last_answer_only_validation_remains(tmp_path):
    _bridge, _addons, _agent, send, _cards = setup_bridge(tmp_path)
    send(flags={"b=route"}, text="Prépare ma feuille de route.")
    first = ROUTE_CHOICES[0]
    reply = send(flags={f"a=choice:{first.id}.{first.options[-1].key}"}, text="")
    actions = [b.action for b in _buttons(reply)]
    assert actions == ["route_deliver"] or not any(a.startswith(f"choice:{first.id}.") for a in actions)


def test_validation_delivers_the_route_of_the_character_and_says_where(tmp_path):
    import os

    from test_bridge_profile_gap import context

    bridge, addons, agent, send, _cards = setup_bridge(tmp_path)
    routes = tmp_path / "routes"
    routes.mkdir()
    name = context()["name"]  # personnage du contexte réel
    mine = {**PLAN, "id": "mine0000001", "request": {**PLAN.get("request", {}), "character": name}}
    other = {**PLAN, "id": "other000001", "request": {**PLAN.get("request", {}), "character": "Autre"}}
    (routes / "mine0000001.json").write_text(json.dumps(mine), encoding="utf-8")
    (routes / "other000001.json").write_text(json.dumps(other), encoding="utf-8")
    os.utime(routes / "other000001.json", (2_000_000_000, 2_000_000_000))  # plus récent, autre personnage
    bridge.routes_dir = routes
    calls = len(agent.calls)
    reply = send(flags={"a=route_deliver"}, text="")
    assert len(agent.calls) == calls  # livrée par le pont, sans le modèle
    guide = slot_table(addons, 1).guide
    assert "mine000" in guide.text and guide.name == guide_name(mine) == f"Forever · {name} · " + (
        f"{PLAN['levels']['from']}-{PLAN['levels']['to']}"
    )
    assert guide.name in reply.text and "Forever Routes" in reply.text and "RestedXP" in reply.text


def test_the_model_is_told_the_published_cards(tmp_path):
    _bridge, _addons, agent, send, _cards = setup_bridge(tmp_path)
    send(text="Quoi de neuf ?")
    assert "À valider" in agent.calls[-1][0]


def test_answer_buttons_under_the_reply_send_the_action():
    import pytest

    pytest.importorskip("lupa")
    from test_bridge_addon_lua import Game
    from test_bridge_p06b_g_lua import EPOCH, status
    from test_bridge_p06b_lua import click, collect
    from test_bridge_reply_lua import reply
    from test_bridge_send_lua import type_and_enter

    from forever.bridge.slots import inbox_lua

    first = ROUTE_CHOICES[0]
    choices = {
        "prompt": first.prompt,
        "buttons": [
            *({"label": o.label, "action": f"choice:{first.id}.{o.key}"} for o in first.options),
            {"label": "Valider et livrer", "action": "route_deliver"},
        ],
    }
    game = Game()
    game.slash("/fv")
    done = reply(game, "done", text="## Aperçu\n- 1 à 6", choices=choices)
    game.stub.addons["ForeverBridge_S001"] = inbox_lua(EPOCH, status(), [reply(game, "working")], [], [])
    for index in range(2, 30):
        game.stub.addons[f"ForeverBridge_S{index:03d}"] = inbox_lua(EPOCH, status(), [done], [], [])
    type_and_enter(game, "Prépare ma feuille de route.")
    collect(game)
    game.stub.Advance(60)
    lua = game.lua.globals()
    bar = lua.ForeverBridgeAnswers
    assert bar is not None and bar.IsShown(bar)
    button = lua.ForeverBridgeAnswer1
    assert button.GetText(button) == first.options[0].label
    validate = lua[f"ForeverBridgeAnswer{len(first.options) + 1}"]
    assert validate.GetText(validate) == "Valider et livrer"
    click(validate)
    record, _ = collect(game)
    assert record.flags == frozenset({"a=route_deliver"}) and record.text == ""
    assert not bar.IsShown(bar)  # une réponse donnée : la rangée disparaît
