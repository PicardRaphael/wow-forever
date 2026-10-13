"""Consultation des bonus d'XP (T04f, bloc C) : `forever lookup xp_bonuses` et `forever_lookup(kind="xp_bonuses")`,
chaque bonus avec sa valeur, sa durée, son cumul, son accès, sa source et sa certitude, provenance complète."""

import asyncio
import json

from conftest import DATA_DIR, LOCAL_VERSION, read_json
from mcp import Client

from forever.cli import main
from forever.mcp_server import build_server
from forever.provenance import validate_provenance

CERTAINTIES = {"certain", "probable", "suppose"}


def doc():
    return read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")


def lookup(capsys, *args):
    code = main(["lookup", "xp_bonuses", *args, "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_cli_lists_every_bonus_with_source_and_certainty(capsys):
    code, out = lookup(capsys)
    assert code == 0 and validate_provenance(out["provenance"]) == []
    assert {b["spell_id"] for b in out["bonuses"]} == {a["spell_id"] for a in doc()["auras"]}
    for b in out["bonuses"]:
        assert b["access"] in {"item", "legacy", "food", "camp", "none"}
        assert b["certainty"] in CERTAINTIES and b["source"]
        assert "duration_s" in b and b["max_stacks"] >= 1 and b["effects"]
        assert b["applied"] is (b["access"] != "none")
    assert out["sleeping_bag"]["name"] == doc()["sleeping_bag"]["name"]
    assert out["food"]["count"] == len(doc()["food"])
    assert out["camp"]["tent"]["threshold_pct_of_level"] == doc()["camp"]["tent"]["threshold_pct_of_level"]


def test_cli_filters_by_access(capsys):
    code, out = lookup(capsys, "--access", "none")
    assert code == 0 and out["bonuses"] and all(b["access"] == "none" for b in out["bonuses"])


def test_cli_text_names_the_bonuses(capsys):
    assert main(["lookup", "xp_bonuses"]) == 0
    text = capsys.readouterr().out
    assert "Well-Rested" in text and "jamais appliqué" in text


def test_mcp_lookup_xp_bonuses(make_deps):
    async def go():
        async with Client(build_server(make_deps())) as client:
            ok = await client.call_tool("forever_lookup", {"kind": "xp_bonuses"})
            bad = await client.call_tool("forever_lookup", {"kind": "item"})
            return ok, bad

    ok, bad = asyncio.run(go())
    assert not ok.is_error and validate_provenance(ok.structured_content["provenance"]) == []
    assert ok.structured_content["bonuses"]
    assert "xp_bonuses" in json.dumps(bad.structured_content["error"], ensure_ascii=False)
