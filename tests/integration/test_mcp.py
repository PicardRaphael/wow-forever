"""Serveur MCP en mémoire (critère 4) : outils listés, résultats structurés, provenance, erreurs.

Valeurs de sort attendues (frostbolt, rang 2) : seed/forever-mage/data/1.60.1.70009/spells.json ;
mécanique A5 : docs/MECHANICS_REGISTRY.yaml."""

import asyncio

import pytest
from conftest import LOCAL_VERSION, FakeHttp, corrupt_manifest, tamper
from mcp import Client

from forever.manifest import compute_manifest
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
    assert {t.name for t in tools} == {
        "forever_status",
        "forever_lookup",
        "forever_explain_mechanic",
        "forever_sim_leveling",
    }
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


def test_lookup_with_corrupt_manifest_is_integrity_error(make_deps, data_copy):
    corrupt_manifest(data_copy)
    args = {"kind": "spell", "name": "frostbolt", "rank": 2}
    r = call(make_deps(data_dir=data_copy), lambda c: c.call_tool("forever_lookup", args))
    assert r.is_error
    assert r.structured_content["error"]["code"] == "data_integrity"
    assert validate_provenance(r.structured_content["provenance"]) == []


def test_status_with_corrupt_manifest(make_deps, data_copy):
    corrupt_manifest(data_copy)
    r = call(make_deps(data_dir=data_copy), lambda c: c.call_tool("forever_status", {"offline": True}))
    assert not r.is_error
    integrity = r.structured_content["integrity"]
    assert integrity["ok"] is False and integrity["manifest_error"]
    assert validate_provenance(r.structured_content["provenance"]) == []


def test_lookup_with_tampered_data_shows_disk_fingerprint(make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    real = compute_manifest(data_copy)["versions"][LOCAL_VERSION]["data_sha"]
    args = {"kind": "spell", "name": "frostbolt", "rank": 2}
    r = call(make_deps(data_dir=data_copy), lambda c: c.call_tool("forever_lookup", args))
    assert r.is_error
    assert r.structured_content["error"]["code"] == "data_integrity"
    assert r.structured_content["provenance"]["data_sha"] == real


def test_unsupported_kind(make_deps):
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", {"kind": "talent", "name": "iceLance"}))
    assert r.is_error
    assert r.structured_content["error"]["code"] == "unsupported_kind"
    assert validate_provenance(r.structured_content["provenance"]) == []


def test_explain_mechanic(make_deps):
    r = call(make_deps(), lambda c: c.call_tool("forever_explain_mechanic", {"mechanic_id": "A5"}))
    assert not r.is_error
    data = r.structured_content
    assert data["id"] == "A5" and data["certainty"] == "probable"
    assert data["formula"]
    assert "forever/engine/crit.py::crit_chance" in data["implementations"]
    assert validate_provenance(data["provenance"]) == []


def test_explain_unknown_mechanic_is_structured_error(make_deps):
    r = call(make_deps(), lambda c: c.call_tool("forever_explain_mechanic", {"mechanic_id": "Z9"}))
    assert r.is_error
    assert r.structured_content["error"]["code"] == "unknown_mechanic"
    assert validate_provenance(r.structured_content["provenance"]) == []


def test_sim_leveling(make_deps):
    args = {"level": 12, "talents": {"improvedFrostbolt": 3}, "n": 50}
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", args))
    assert not r.is_error
    data = r.structured_content
    assert data["mob_hp"]["value"] == 272 and data["mob_hp"]["certainty"] == "certain"
    assert data["monte_carlo"]["total"] > data["monte_carlo"]["combat"] > 0 and data["analytic"]["total"] > 0
    assert validate_provenance(data["provenance"]) == [] and data["provenance"]["certainty"] == "suppose"


def test_sim_leveling_illegal_build_is_structured_error(make_deps):
    args = {"level": 12, "talents": {"improvedFrostbolt": 5}}
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", args))
    assert r.is_error and r.structured_content["error"]["code"] == "invalid_argument"
    assert validate_provenance(r.structured_content["provenance"]) == []
