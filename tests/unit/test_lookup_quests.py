"""Consultation des quêtes (T04d, bloc D) : `forever lookup quests`, `forever quests show|build|diff`,
`forever_lookup(kind="quests")`, chaque sortie avec sa provenance. Fixture : `tests/fixtures/addons/quests/`."""

import json

import pytest
from conftest import FIXTURES, isolated_deps

from forever.cli import main
from forever.provenance import validate_provenance
from forever.quests import lookup_quests

WOW = FIXTURES / "addons" / "quests"


def test_lookup_by_level_and_faction(tmp_path):
    out = lookup_quests(isolated_deps(tmp_path), level=31, faction="alliance", wow_dir=WOW)
    ids = [q["id"] for q in out["quests"]]
    assert 92432 in ids and 92434 not in ids  # 92434 : Horde (Completo)
    assert validate_provenance(out["provenance"]) == []
    assert out["provenance"]["certainty"] == "suppose"


def test_lookup_by_status_and_dungeon(tmp_path):
    deps = isolated_deps(tmp_path)
    new = lookup_quests(deps, status="nouvelle", wow_dir=WOW)
    assert {92432, 96403, 96607} <= {q["id"] for q in new["quests"]}
    rfc = lookup_quests(deps, dungeon="Ragefire Chasm", faction="horde", wow_dir=WOW, limit=50)
    assert {5761, 5723, 5725, 5722} <= {q["id"] for q in rfc["quests"]}
    assert rfc["total"] == len(rfc["quests"])


def test_unknown_status_is_refused(tmp_path):
    from forever.errors import InvalidArgumentError

    with pytest.raises(InvalidArgumentError):
        lookup_quests(isolated_deps(tmp_path), status="retirée", wow_dir=WOW)


def run(capsys, args, tmp_path, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(WOW))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    code = main(args)
    return code, capsys.readouterr().out


def test_cli_show_quest_with_discrepancies(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["quests", "show", "--id", "5761", "--json"], tmp_path, monkeypatch)
    assert code == 0
    doc = json.loads(out)
    quest = doc["quests"][0]
    assert quest["id"] == 5761 and quest["discrepancies"]["level"]["naowh_dj"] == 9
    assert validate_provenance(doc["provenance"]) == []


def test_cli_build_and_diff(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["quests", "build", "--json"], tmp_path, monkeypatch)
    assert code == 0
    built = json.loads(out)
    assert built["count"] > 0 and set(built["statuses"]) <= {
        "nouvelle",
        "retouchée",
        "absente des sources Forever",
        "inchangée",
        "non couverte",
    }
    code, out = run(capsys, ["quests", "diff", "--json"], tmp_path, monkeypatch)
    assert code == 0
    diff = json.loads(out)
    assert any(p["field"] == "level" for p in diff["discrepancies"])
    assert validate_provenance(diff["provenance"]) == []


def test_cli_lookup_quests_text(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["lookup", "quests", "--level", "31", "--faction", "alliance"], tmp_path, monkeypatch)
    assert code == 0 and "An Alarming Request" in out and "Provenance" in out


def test_mcp_lookup_quests(make_deps):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps(wow_dir=WOW))) as client:
            return await client.call_tool("forever_lookup", {"kind": "quests", "level": 31, "faction": "alliance"})

    result = asyncio.run(go())
    assert not result.is_error
    data = result.structured_content
    assert 92432 in [q["id"] for q in data["quests"]]
    assert validate_provenance(data["provenance"]) == []
