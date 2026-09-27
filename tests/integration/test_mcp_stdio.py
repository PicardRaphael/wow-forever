"""Vrai point d'entrée stdio (`python -m forever mcp`) : le serveur démarre, liste ses outils et répond."""

import asyncio
import os
import sys

import pytest
from conftest import REPO_ROOT
from mcp import Client, StdioServerParameters

from forever.provenance import validate_provenance

pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])


def test_stdio_server(tmp_path):
    env = {**os.environ, "FOREVER_OFFLINE": "1", "FOREVER_CACHE_DIR": str(tmp_path / "cache")}
    params = StdioServerParameters(command=sys.executable, args=["-m", "forever", "mcp"], env=env, cwd=str(REPO_ROOT))

    async def go():
        async with Client(params, read_timeout_seconds=60) as client:
            tools = await client.list_tools()
            result = await client.call_tool("forever_lookup", {"kind": "spell", "name": "frostbolt", "rank": 2})
            return tools, result

    tools, result = asyncio.run(go())
    assert {t.name for t in tools.tools} == {"forever_status", "forever_lookup"}
    assert not result.is_error
    assert result.structured_content["ranks"][0]["damage_min"] == 34
    assert validate_provenance(result.structured_content["provenance"]) == []
