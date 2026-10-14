"""Suites de la relecture de RX1 (blocs C à E) : RestedXP sans objet `RXP`, guide « absent » relivrable, erreurs de
`forever_route` avec provenance, livraison d'un plan illisible sans arrêt du pont, plan du personnage du contexte,
quête imposée jamais retirée, question « seul ou en groupe » retirée tant qu'elle ne change rien."""

import asyncio
import json

import pytest
from conftest import FIXTURES, read_json
from mcp import Client
from test_bridge_addon_lua import Game
from test_bridge_choices import setup_bridge
from test_bridge_guide_lua import GUIDE, calls, deliver, status
from test_bridge_loop import slot_table
from test_engine_route import CAP, make_world, start_state

from forever.bridge.choices import ROUTE_CHOICES
from forever.mcp_server import build_server
from forever.optimize.route import plan
from forever.provenance import validate_provenance

PLAN = read_json(FIXTURES / "rxp" / "plan.json")
ONLY_IMPORT = """
rxp_calls = {}
RXPGuides = { ImportGuide = function(text) rxp_calls[#rxp_calls + 1] = text; return { name = "x" } end }
"""


def test_import_without_rxp_object():
    pytest.importorskip("lupa")
    game = Game(prelude=ONLY_IMPORT)
    deliver(game)
    assert calls(game) == [GUIDE["text"]] and status(game) == "livré"


def test_forever_route_errors_carry_provenance(make_deps):
    async def go():
        async with Client(build_server(make_deps(offline=True))) as client:
            return await client.call_tool("forever_route", {"action": "show", "plan_id": "inconnu"})

    result = asyncio.run(go())
    assert result.is_error or "error" in (result.structured_content or {})
    doc = result.structured_content or {}
    assert validate_provenance(doc.get("provenance") or {}) == []


def test_unreadable_plan_does_not_stop_the_bridge(tmp_path):
    bridge, addons, agent, send, cards = setup_bridge(tmp_path)
    routes = tmp_path / "routes"
    routes.mkdir()
    (routes / "abc.json").write_text("{tronqué", encoding="utf-8")
    bridge.routes_dir = routes
    reply = send(flags={"a=route_deliver"}, text="")
    assert "illisible" in reply.text and slot_table(addons, 1).guide is None
    del agent, cards


def test_deliver_takes_the_plan_of_the_character(tmp_path):
    import os

    bridge, addons, _agent, send, _cards = setup_bridge(tmp_path)
    routes = tmp_path / "routes"
    routes.mkdir()
    mine = {**PLAN, "id": "mine0000001", "class": "mage", "faction": "horde"}
    other = {**PLAN, "id": "other000001", "class": "warrior", "faction": "alliance"}
    (routes / "mine0000001.json").write_text(json.dumps(mine), encoding="utf-8")
    (routes / "other000001.json").write_text(json.dumps(other), encoding="utf-8")
    os.utime(routes / "other000001.json", (2_000_000_000, 2_000_000_000))  # le plus récent, d'un autre personnage
    bridge.routes_dir = routes
    send(flags={"a=route_deliver"}, text="")
    assert "mine000" in slot_table(addons, 1).guide.text


def test_included_quest_is_kept(game_data):
    world, _ = make_world(game_data, include=(110,))
    p = plan(game_data, world, start_state(), end_level=5, cap=CAP)
    assert 110 in {s.ref for s in p.stops if s.kind == "accept"}


def test_group_question_is_not_published():
    assert "route_group" not in {c.id for c in ROUTE_CHOICES}
