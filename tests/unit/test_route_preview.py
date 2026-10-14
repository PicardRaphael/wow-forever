"""Aperçu d'une feuille de route et outil MCP `forever_route` (RX1, bloc E). Plan de fixture
`tests/fixtures/rxp/plan.json` ; outil sur les addons synthétiques de `tests/fixtures/addons/dungeons/`."""

import asyncio

from conftest import FIXTURES, read_json
from mcp import Client

from forever.mcp_server import build_server
from forever.provenance import validate_provenance
from forever.route import PREVIEW_FIELDS, route_preview

PLAN = read_json(FIXTURES / "rxp" / "plan.json")
WOW = FIXTURES / "addons" / "dungeons"


def test_preview_fields():
    plan = {
        **PLAN,
        "hours": 1.5,
        "xp_h": 2000.0,
        "rewards": [{"quest": 111, "item": 9001, "name": "Fixture Blade"}],
        "reminders": [{"text": "rappel de fixture"}],
    }
    preview = route_preview(plan)
    assert set(preview) == set(PREVIEW_FIELDS)
    assert preview["levels"] == PLAN["levels"] and preview["hours"] == 1.5 and preview["xp_h"] == 2000.0
    dungeon = next(s for s in PLAN["stops"] if s["kind"] == "dungeon")
    assert preview["dungeons"] == [{"name": dungeon["name"], "level": dungeon["level"]}]
    assert preview["rewards"] == plan["rewards"] and preview["bonuses"] == ["rappel de fixture"]
    assert preview["certainty"] == PLAN["certainty"] and preview["stops"] == len(PLAN["stops"])


def test_mcp_forever_route(make_deps, tmp_path):
    deps = make_deps(wow_dir=WOW, offline=True)

    async def go():
        async with Client(build_server(deps)) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            planned = await client.call_tool(
                "forever_route",
                {"action": "plan", "class_name": "hunter", "faction": "horde", "start_level": 1, "end_level": 3},
            )
            plan_id = planned.structured_content["id"]
            shown = await client.call_tool("forever_route", {"action": "show", "plan_id": plan_id})
            return tools, planned, shown

    tools, planned, shown = asyncio.run(go())
    assert "forever_route" in tools
    assert not planned.is_error and not shown.is_error
    doc = planned.structured_content
    assert validate_provenance(doc["provenance"]) == []
    assert set(doc["preview"]) == set(PREVIEW_FIELDS) and doc["preview"]["levels"]["to"] == 3
    assert shown.structured_content["id"] == doc["id"]
