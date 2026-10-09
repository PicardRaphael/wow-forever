"""Égalités de build (P06a, sonde en jeu E du 2026-10-09, point 2) : en jeu, le bouton Talents donnait Elemental
Precision 3 et Frostbite 2, la CLI (préréglage complet) Elemental Precision 2 et Frostbite 3 ; les deux sont à égalité
statistique. La CLI et le MCP partent du même préréglage par défaut (même question, même résultat), l'égalité est
signalée (`alternative.tie`) avec un lien Talents Forever pour l'autre option, et la race s'écrit sans souci de casse
(le premier appel de la conversation « jeu » avait échoué sur « orc »)."""

import asyncio
import json

import pytest
from mcp import Client

from forever.bridge.prompt import SYSTEM_PROMPT
from forever.build import build_report
from forever.cli import build_parser, main
from forever.mcp_server import build_server

pytestmark = pytest.mark.slow


def test_cli_and_mcp_share_the_default_preset():
    args = build_parser().parse_args(["build", "leveling", "--level", "20"])
    assert args.preset == "rapide"


def test_tie_is_flagged_with_both_options(make_deps):
    rep = build_report(make_deps(), "leveling", 20, race="orc", sensitivity=False)
    assert rep["race"] == "Orc"
    alt = rep["alternative"]
    assert alt["talents"] is not None and alt["gap"]["significant"] is False
    assert alt["tie"] is True


def test_same_question_same_result_cli_and_mcp(capsys, make_deps):
    deps = make_deps()
    assert main(["build", "leveling", "--level", "20", "--race", "Orc", "--json"], deps) == 0
    cli = json.loads(capsys.readouterr()[0])

    async def call():
        async with Client(build_server(deps)) as client:
            result = await client.call_tool("forever_build", {"context": "leveling", "level": 20, "race": "Orc"})
            return json.loads(result.content[0].text)

    mcp = asyncio.run(call())
    assert cli["talents"] == mcp["talents"] and cli["alternative"]["talents"] == mcp["alternative"]["talents"]
    assert cli["alternative"]["tie"] is True and mcp["alternative"]["tie"] is True
    tf = mcp["alternative"]["export"]
    assert tf["status"] in {"ok", "absent"} and "link" in tf


def test_text_output_says_it_is_a_tie(capsys, make_deps):
    assert main(["build", "leveling", "--level", "20", "--race", "Orc"], make_deps()) == 0
    out = capsys.readouterr()[0]
    assert "égalité statistique" in out


def test_prompt_asks_to_present_both_options():
    assert "égalité statistique" in SYSTEM_PROMPT and "alternative.tie" in SYSTEM_PROMPT
