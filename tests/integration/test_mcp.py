"""Serveur MCP en mémoire (critère 4) : outils listés, résultats structurés, provenance, erreurs.

Valeurs de sort attendues (frostbolt, rang 2) : seed/forever-mage/data/1.60.1.70009/spells.json ;
mécanique A5 : docs/MECHANICS_REGISTRY.yaml."""

import asyncio

from conftest import FIXTURES, LOCAL_VERSION, FakeHttp, corrupt_manifest, tamper
from mcp import Client

from forever.manifest import compute_manifest
from forever.mcp_server import build_server
from forever.provenance import validate_provenance


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
        "forever_build",
        "forever_player_profile",  # T06b : profil joueur, lecture seule
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
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", {"kind": "item", "name": "iceLance"}))
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


def test_sim_leveling_armor_and_rules(make_deps):
    """T04c : `armor` et `rules` sont des paramètres de build du simulateur ; Mage Armor sous son niveau refusée."""
    args = {"level": 40, "n": 10, "armor": "mage", "rules": "forever"}
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", args))
    assert not r.is_error and r.structured_content["options"]["armor"] == "mage"
    args = {"level": 30, "n": 10, "armor": "mage"}
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", args))
    assert r.is_error and r.structured_content["error"]["code"] == "invalid_argument"
    assert validate_provenance(r.structured_content["provenance"]) == []


def test_sim_leveling_arcane_rotation(make_deps):
    """T04c : rotation arcane, `ab_stacks` et `ab_dump` paramètres de build ; cumuls hors plage refusés."""
    talents = {"arcaneFocus": 5, "arcaneSubtlety": 2, "magicAbsorption": 2, "arcaneResilience": 1, "arcaneBlast": 1}
    args = {"level": 24, "n": 10, "rotation": "arcane", "talents": talents, "ab_stacks": 2, "ab_dump": "fireball"}
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", args))
    assert not r.is_error and r.structured_content["options"]["ab_stacks"] == 2
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", {**args, "ab_stacks": 9}))
    assert r.is_error and r.structured_content["error"]["code"] == "invalid_argument"


def test_lookup_zones(make_deps):
    """T04c : domaine `zones` de forever_lookup (Questie lu sur disque, provenance, certitude suppose)."""
    questie = str(FIXTURES / "questie" / "11.38.0")
    args = {"kind": "zones", "level": 12, "faction": "horde", "questie": questie}
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", args))
    assert not r.is_error and r.structured_content["zones"][0]["name"] == "The Barrens"
    assert validate_provenance(r.structured_content["provenance"]) == []
    r = call(make_deps(), lambda c: c.call_tool("forever_lookup", {**args, "questie": questie + "-absent"}))
    assert r.is_error and r.structured_content["error"]["code"] == "invalid_argument"


def test_sim_leveling_low_level_penalty(make_deps):
    """T04e : `low_level_penalty` paramètre de forever_sim_leveling ; False refusé avec rules seed."""
    args = {"level": 12, "n": 10, "low_level_penalty": False}
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", args))
    assert not r.is_error and r.structured_content["options"]["low_level_penalty"] is False
    r = call(make_deps(), lambda c: c.call_tool("forever_sim_leveling", {**args, "rules": "seed"}))
    assert r.is_error and r.structured_content["error"]["code"] == "invalid_argument"
    assert validate_provenance(r.structured_content["provenance"]) == []
