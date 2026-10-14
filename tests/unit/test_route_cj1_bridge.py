"""CJ1, bloc 1 (décision 277) : la position, la race et le nom du personnage vont du jeu jusqu'à la route.

ForeverBridge envoie la carte et les coordonnées du joueur (en pourcentage de la carte) ; le pont les garde dans le
contexte relié et les passe à `forever_route` avec la race et le nom du personnage (ses quêtes faites sont lues au
profil) ; l'outil MCP et la CLI les acceptent.

Valeurs : contexte synthétique (carte et coordonnées fabriquées), client simulé de `tests/fixtures/bridge/`."""

import asyncio

import pytest
from conftest import FIXTURES
from mcp import Client

from forever.bridge.context import load_context_data, resolve
from forever.bridge.plans import button_plan
from forever.mcp_server import build_server

WOW = FIXTURES / "addons" / "dungeons"


def _ctx(**extra):
    base = {
        "name": "Bob",
        "realm": "Forever",
        "class": "MAGE",
        "level": "1",
        "race": "Gnome",
        "faction": "Alliance",
        "zone": "Fixture Vale",
        "map": "9001",
        "x": "29.8",
        "y": "71.2",
    }
    return {**base, **extra}


def test_resolved_context_keeps_map_and_position(make_deps):
    data = load_context_data(make_deps())
    r = resolve(data, _ctx())
    assert (r.map, r.x, r.y, r.name) == (9001, 29.8, 71.2, "Bob")
    r = resolve(data, _ctx(x="abc", y=""))
    assert r.map == 9001 and r.x is None and r.y is None


def test_route_button_passes_race_position_and_character(make_deps):
    data = load_context_data(make_deps())
    plan = button_plan("route", resolve(data, _ctx()), data.level_cap)
    args = plan.calls[0].args
    assert args["race"] == "Gnome" and args["character"] == "Bob"
    assert (args["start_map"], args["start_x"], args["start_y"]) == (9001, 29.8, 71.2)
    plan = button_plan("route", resolve(data, _ctx(map="", x="", y="")), data.level_cap)
    assert "start_map" not in plan.calls[0].args


def test_mcp_forever_route_accepts_race_position_and_character(make_deps):
    deps = make_deps(wow_dir=WOW, offline=True)

    async def go():
        async with Client(build_server(deps)) as client:
            tool = next(t for t in (await client.list_tools()).tools if t.name == "forever_route")
            planned = await client.call_tool(
                "forever_route",
                {
                    "action": "plan",
                    "class_name": "hunter",
                    "faction": "horde",
                    "start_level": 1,
                    "end_level": 3,
                    "race": "Orc",
                    "character": "Bob",
                },
            )
            return tool, planned

    tool, planned = asyncio.run(go())
    props = tool.input_schema["properties"]
    assert {"race", "start_map", "start_x", "start_y", "character"} <= set(props)
    assert not planned.is_error
    assert planned.structured_content["request"]["race"] == "Orc"


def test_addon_sends_the_player_position():
    pytest.importorskip("lupa")
    from test_bridge_addon_lua import Game
    from test_bridge_send_lua import sent, type_and_enter

    game = Game(screen=(2560, 1440))
    game.lua.execute("Stub.player.pos = { x = 0.298, y = 0.712 }")
    game.slash("/fv")
    type_and_enter(game, "Où suis-je ?")
    _, record = sent(game)
    assert record.context["x"] == "29.8" and record.context["y"] == "71.2"
    assert record.context["map"] == str(game.lua.eval("Stub.player.map"))
