"""Bloc 4d (décision 282) : la route d'équipement donnée directement. « Feuille de route de ces objets »
(`a=gear_route:<N>`) calcule une feuille de route de leveling depuis mon niveau qui **inclut** les quêtes qui donnent
les objets visés et les donjons de leurs boss ; la réponse en donne l'aperçu compact et les objets qu'elle rapporte,
avec « Valider et livrer » dessous ; la livraison passe par `route_deliver`, sous le nom stable « Forever · <perso> ·
équipement ».

Valeurs : choix d'équipement, contexte et plan fabriqués ici ; l'optimiseur réel est remplacé par un plan fabriqué
pour le test de bout en bout du pont. Aucun chiffre de jeu ici."""

import json

from test_bridge_choices import setup_bridge
from test_bridge_loop import slot_table

from forever.bridge import gear_level
from forever.route import guide_name

LEVEL = 10
DOC = {
    "picks": [
        {"slot": "Hands", "item": 980001, "name": "Quest Gloves", "source": "quest_reward",
         "quest_detail": {"id": 980101, "giver": "Fixture Giver", "zone": "Fixture Vale", "x": 1.0, "y": 2.0, "after": []}},
        {"slot": "Neck", "item": 980002, "name": "Boss Choker", "source": "boss_drop",
         "dungeon_detail": {"dungeon": "Fixture Depths", "boss": "Fixture Boss", "rate": 0.3}},
        {"slot": "Back", "item": 980003, "name": "Drop Cape", "source": "world_drop", "drop_levels": [8, 12]},
    ],
}  # fmt: skip
WHO = {
    "class_name": "Mage",
    "faction": "alliance",
    "level": 4,
    "race": "Gnome",
    "name": "Go",
    "start_at": (9001, 30.0, 70.0),
}


def test_route_request_includes_the_quests_and_dungeons_of_the_items():
    request = gear_level.gear_route_request(DOC, WHO, LEVEL)
    assert request.include == (980101,) and request.dungeons == ("Fixture Depths",)
    assert (request.start_level, request.end_level) == (4, LEVEL)
    assert request.race == "Gnome" and request.character == "Go" and request.start_at == (9001, 30.0, 70.0)
    assert request.purpose == "équipement"


def test_gear_route_has_a_stable_name():
    plan = {
        "class": "mage",
        "levels": {"from": 4, "to": LEVEL},
        "request": {"character": "Go", "purpose": "équipement"},
    }
    assert guide_name(plan) == "Forever · Go · équipement"


def test_gear_route_button_end_to_end(tmp_path, make_deps, monkeypatch):
    deps = make_deps(offline=True)
    routes = tmp_path / "routes"
    routes.mkdir()
    plan = {
        "id": "gear0000001", "class": "mage", "faction": "alliance", "levels": {"from": 4, "to": LEVEL, "reached": LEVEL},
        "feasible": True, "hours": 1.5, "xp_h": 1000.0, "certainty": "suppose",
        "stops": [{"kind": "accept", "ref": 980101, "name": "Fixture Errand", "text": "prends Fixture Errand",
                   "zone": "Fixture Vale", "x": 1.0, "y": 2.0, "level": 4, "xp": 0.0, "seconds": 1.0, "travel_s": 0.0,
                   "certainty": "suppose", "map": 9001}],
        "steps": [], "rewards": [], "reminders": [], "warnings": [], "dungeons": [],
        "request": {"character": "Go", "purpose": "équipement", "race": "Gnome"},
        "basis": {"kind": "notre calcul"}, "provenance": {"game_version": "x", "certainty": "suppose"},
    }  # fmt: skip
    asked = []

    def fake_plan(deps_, request, **_kwargs):
        asked.append(request)
        made = {**plan, "request": {**plan["request"], "character": request.character}}  # personnage du contexte
        (routes / "gear0000001.json").write_text(json.dumps(made), encoding="utf-8")
        return made

    monkeypatch.setattr(gear_level, "plan_route", fake_plan)
    monkeypatch.setattr(gear_level, "_leveling", lambda deps_, context, level, to_level=None: dict(DOC))
    (tmp_path / "bridge").mkdir()
    bridge, addons, agent, send, _cards = setup_bridge(tmp_path / "bridge")
    bridge.routes_dir = routes
    bridge.gear_router = lambda context, level: gear_level.gear_route_reply(deps, context, level)
    before = len(agent.calls)
    reply = send(flags={f"a=gear_route:{LEVEL}"}, text="")
    assert len(agent.calls) == before and asked and asked[0].include == (980101,)
    assert "Fixture Vale" in reply.text and "Quest Gloves" in reply.text and "Boss Choker" in reply.text
    actions = [reply.choices.buttons[i].action for i in range(1, len(reply.choices.buttons) + 1)]
    assert actions == ["route_deliver"]
    send(flags={"a=route_deliver"}, text="")
    assert slot_table(addons, 1).guide.name == f"Forever · {asked[0].character} · équipement"


def test_imposed_quests_keep_our_calculation(make_deps):
    """Une route qui impose des quêtes (route d'équipement) garde notre calcul : la base adaptée de RestedXP ne
    connaît pas ces quêtes."""
    from types import SimpleNamespace

    from forever.compare import delivered_route
    from forever.route import RouteRequest

    found = SimpleNamespace(result="notre route")
    request = RouteRequest("mage", "alliance", 1, 10, include=(980101,), race="Gnome", purpose="équipement")
    result, basis = delivered_route(make_deps(offline=True), None, request, found)
    assert result == "notre route" and basis["kind"] == "calcul" and "imposées" in basis["verdict"]


def test_reply_says_which_quests_are_in_the_route(tmp_path, make_deps, monkeypatch):
    deps = make_deps(offline=True)
    plan = {"id": "g", "class": "mage", "levels": {"from": 4, "to": LEVEL}, "hours": 1.0, "xp_h": 100.0,
            "certainty": "suppose", "stops": [], "rewards": [], "reminders": [], "warnings": [],
            "request": {"character": "Go", "purpose": "équipement"}, "basis": {"kind": "calcul"}, "provenance": {}}  # fmt: skip
    monkeypatch.setattr(gear_level, "plan_route", lambda deps_, request, **_k: plan)
    monkeypatch.setattr(gear_level, "_leveling", lambda deps_, context, level, to_level=None: dict(DOC))
    monkeypatch.setattr(gear_level, "_who", lambda deps_, context: dict(WHO))
    text, _ = gear_level.gear_route_reply(deps, {}, LEVEL)
    gloves = next(line for line in text.splitlines() if "Quest Gloves" in line)
    assert "pas dans cette route" in gloves and "dans la route" not in gloves.replace("pas dans cette route", "")
