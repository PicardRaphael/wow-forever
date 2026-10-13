"""Consultation des donjons (DJ1, bloc F) : `forever dungeon list|info|item|report` et
`forever_lookup(kind="dungeons" | "dungeon" | "dungeon_item")`, provenance complète (versions des addons comprises),
taux absent rendu « inconnu », écarts entre sources listés.

Fixtures : `tests/fixtures/addons/dungeons/` (addons synthétiques) ; données : version du dépôt. Aucun réseau."""

import json

import mcp  # noqa: F401 : boucle asyncio du client MCP sous Windows (tests/conftest.py, piège T06b)
from conftest import FIXTURES

from forever.cli import main
from forever.provenance import validate_provenance

WOW = FIXTURES / "addons" / "dungeons"


def run(capsys, args, tmp_path, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(WOW))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    code = main(args)
    return code, capsys.readouterr().out


def test_dungeon_list_by_level(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["dungeon", "list", "--level", "15", "--json"], tmp_path, monkeypatch)
    assert code == 0
    doc = json.loads(out)
    ids = {d["id"] for d in doc["dungeons"]}
    assert "389" in ids and "2998" not in ids
    assert validate_provenance(doc["provenance"]) == []


def test_dungeon_info_has_provenance_and_addon_versions(capsys, tmp_path, monkeypatch):
    code, out = run(
        capsys,
        ["dungeon", "info", "Ragefire Chasm", "--class", "mage", "--level", "14", "--json"],
        tmp_path,
        monkeypatch,
    )
    assert code == 0
    doc = json.loads(out)
    assert doc["dungeon"]["id"] == "389"
    assert validate_provenance(doc["provenance"]) == []
    assumptions = " ".join(doc["provenance"]["assumptions"])
    assert "Naowh Forever, Dungeon Journal 1.1.11" in assumptions and "ForeverDungeonJournal 1.6.2" in assumptions
    assert any(s["source"] == "naowh_dj" and s["version"] == "1.1.11" for s in doc["sources"])


def test_dungeon_item_where(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["dungeon", "item", "14149", "--json"], tmp_path, monkeypatch)
    assert code == 0
    doc = json.loads(out)
    (hit,) = doc["hits"]
    assert hit["boss"] == "Taragaman the Hungerer" and hit["source"] == "relevé" and hit["certainty"] == "certain"
    code, out = run(capsys, ["dungeon", "item", "14148", "--json"], tmp_path, monkeypatch)
    (hit,) = json.loads(out)["hits"]
    assert hit["source"] == "fojji" and hit["version"] == "3.3.5"  # sans relevé : source et version de l'addon
    assert validate_provenance(doc["provenance"]) == []


def test_unknown_rate_shown_as_unknown(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["dungeon", "info", "Ruins of Lordaeron"], tmp_path, monkeypatch)
    assert code == 0 and "Witherfang" in out and "inconnu" in out and "Provenance" in out


def test_discrepancies_are_listed_in_text(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["dungeon", "info", "2998"], tmp_path, monkeypatch)
    assert code == 0 and "Écarts" in out and "fojji" in out


def test_dungeon_report_is_markdown(capsys, tmp_path, monkeypatch):
    code, out = run(capsys, ["dungeon", "report"], tmp_path, monkeypatch)
    assert code == 0 and out.startswith("# Donjons de Forever")


def test_unknown_dungeon_says_what_to_do(capsys, tmp_path, monkeypatch):
    code, _ = run(capsys, ["dungeon", "info", "Atlantide"], tmp_path, monkeypatch)
    assert code != 0


def test_lookup_dungeons_kind(make_deps):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps(wow_dir=WOW))) as client:
            listed = await client.call_tool("forever_lookup", {"kind": "dungeons", "level": 15})
            one = await client.call_tool("forever_lookup", {"kind": "dungeon", "name": "Ragefire Chasm"})
            item = await client.call_tool("forever_lookup", {"kind": "dungeon_item", "name": "14149"})
            return listed, one, item

    listed, one, item = asyncio.run(go())
    assert not listed.is_error and not one.is_error and not item.is_error
    assert "389" in {d["id"] for d in listed.structured_content["dungeons"]}
    assert one.structured_content["dungeon"]["name"] == "Ragefire Chasm"
    assert item.structured_content["hits"][0]["dungeon"] == "389"
    for result in (listed, one, item):
        assert validate_provenance(result.structured_content["provenance"]) == []
