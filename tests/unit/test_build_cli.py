"""`forever build <contexte> --level N` et l'outil MCP `forever_build` (T05, bloc I2 ; décision 86) : JSON et texte,
provenance, rubriques du texte, erreurs d'argument, même résultat par la CLI et le MCP, aucun appel réseau."""

import asyncio
import json

import pytest
from conftest import FakeHttp
from mcp import Client

from forever.cli import main
from forever.mcp_server import build_server
from forever.provenance import validate_provenance

# La boucle asyncio de Windows ouvre une paire de sockets locale : autorisée, tout autre hôte reste bloqué.
pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])
ARGV = ["build", "leveling", "--level", "14", "--preset", "rapide"]
SECTIONS = ("Raisons", "Alternative", "Stabilité", "Sensibilité", "Respec", "Angles morts", "Hypothèses")


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def test_json_output(capsys, make_deps):
    http = FakeHttp.failing()
    code, out, _ = run(capsys, [*ARGV, "--json"], make_deps(http=http))
    assert code == 0
    payload = json.loads(out)
    validate_provenance(payload["provenance"])
    assert [s["level"] for s in payload["order"]] == list(range(10, 15))
    assert http.calls == []  # aucun réseau


def test_text_output_has_every_section(capsys, make_deps):
    code, out, _ = run(capsys, [*ARGV, "--sensitivity", "on"], make_deps())
    assert code == 0
    assert out.startswith("Build leveling niveau 14")
    for section in SECTIONS:
        assert section in out, section
    assert "Provenance" in out


def test_options_reach_the_report(capsys, make_deps):
    argv = [
        "build",
        "leveling",
        "--level",
        "12",
        "--preset",
        "rapide",
        "--talented-bonus",
        "2",
        "--sensitivity",
        "off",
        "--current",
        "wandSpecialization=2",
        "--respecs",
        "3",
        "--sp",
        "20",
        "--crit",
        "0.1",
        "--json",
    ]
    code, out, _ = run(capsys, argv, make_deps())
    assert code == 0, out
    payload = json.loads(out)
    assert sum(payload["talents"].values()) == 5  # 3 points du niveau 12 + 2 du bonus
    assert payload["sensitivity"] == []
    assert payload["respec"]["cost_gold"] == 15  # quatrième réinitialisation (respec.json)
    text = " ; ".join(payload["assumptions"])
    assert "puissance des sorts 20" in text and "Talented" in text


def test_argument_errors(capsys, make_deps):
    code, _, err = run(capsys, ["build", "arena", "--level", "20"], make_deps())
    assert code == 2 and "arena" in err
    code, _, err = run(capsys, ["build", "raid", "--level", "61", "--preset", "rapide"], make_deps())
    assert code == 2 and "61" in err
    code, _, err = run(capsys, ["build", "leveling", "--level", "20", "--current", "iceLance=1"], make_deps())
    assert code == 2 and "illégal" in err


def test_mcp_returns_the_cli_json(capsys, make_deps):
    deps = make_deps()
    code, out, _ = run(capsys, [*ARGV, "--json"], deps)
    assert code == 0

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_build", {"context": "leveling", "level": 14, "preset": "rapide"})

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content == json.loads(out)


def test_mcp_default_preset_is_fast(make_deps):
    async def go():
        async with Client(build_server(make_deps())) as client:
            tools = await client.list_tools()
            return {t.name: t for t in tools.tools}

    tools = asyncio.run(go())
    assert "forever_build" in tools and tools["forever_build"].output_schema is not None
    schema = tools["forever_build"].input_schema["properties"]
    assert schema["preset"]["default"] == "rapide" and schema["talented_bonus"]["default"] == 0
