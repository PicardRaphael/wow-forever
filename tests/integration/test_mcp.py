"""Serveur MCP en mémoire (critère 4) : outils listés, résultats structurés, provenance, erreurs."""

import asyncio

import pytest
from conftest import LOCAL_VERSION, FakeHttp
from mcp import Client

from forever.mcp_server import build_server
from forever.provenance import validate_provenance

# La boucle asyncio de Windows ouvre une paire de sockets locale : autorisée, tout autre hôte reste bloqué.
pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])


def call(deps, coro_fn):
    async def go():
        async with Client(build_server(deps)) as client:
            return await coro_fn(client)

    return asyncio.run(go())


def test_list_tools(make_deps):
    tools = call(make_deps(), lambda c: c.list_tools()).tools
    assert {t.name for t in tools} == {"forever_status", "forever_lookup"}
    for t in tools:
        assert t.output_schema is not None
        assert t.description


def test_lookup_frostbolt_rank_2(make_deps):
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", {"kind": "spell", "name": "frostbolt", "rank": 2}))
    assert not r.is_error
    data = r.structured_content
    rank = data["ranks"][0]
    assert (rank["damage_min"], rank["damage_max"], rank["cast_time_s"], rank["mana"]) == (34, 38, 1.8, 35)
    assert validate_provenance(data["provenance"]) == []
    assert data["provenance"]["game_version"] == LOCAL_VERSION


def test_status(make_deps):
    r = call(make_deps(http=FakeHttp.fixture("builds_fresh.json")), lambda c: c.call_tool("forever_status", {}))
    assert not r.is_error
    data = r.structured_content
    assert data["freshness"]["freshness"] == "fresh"
    assert validate_provenance(data["provenance"]) == []


def test_status_offline(make_deps):
    http = FakeHttp.fixture("builds_fresh.json")
    r = call(make_deps(http=http), lambda c: c.call_tool("forever_status", {"offline": True}))
    assert http.calls == []
    assert r.structured_content["freshness"]["freshness"] == "unknown"


def test_unknown_spell_is_structured_error(make_deps):
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", {"kind": "spell", "name": "frostbollt"}))
    assert r.is_error
    data = r.structured_content
    assert data["error"]["code"] == "unknown_spell"
    assert "frostbolt" in data["error"]["suggestions"]
    assert validate_provenance(data["provenance"]) == []
    assert r.content and "frostbolt" in r.content[0].text


def test_unsupported_kind(make_deps):
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", {"kind": "talent", "name": "iceLance"}))
    assert r.is_error
    assert r.structured_content["error"]["code"] == "unsupported_kind"
    assert validate_provenance(r.structured_content["provenance"]) == []
