"""Vrai point d'entrée stdio (`python -m forever mcp`) : le serveur démarre, liste ses outils et répond.

Valeur de sort attendue (frostbolt, rang 2) : `spells.json` de la version installée, que le serveur lit (le test
vérifie le transport, pas la valeur : une nouvelle version peut la changer, 1.60.1.70291)."""

import asyncio
import os
import sys

from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT, read_json
from mcp import Client, StdioServerParameters

from forever.provenance import validate_provenance


def test_stdio_server(tmp_path):
    env = {**os.environ, "FOREVER_OFFLINE": "1", "FOREVER_CACHE_DIR": str(tmp_path / "cache")}
    params = StdioServerParameters(command=sys.executable, args=["-m", "forever", "mcp"], env=env, cwd=str(REPO_ROOT))

    async def go():
        async with Client(params, read_timeout_seconds=60) as client:
            tools = await client.list_tools()
            result = await client.call_tool("forever_lookup", {"kind": "spell", "name": "frostbolt", "rank": 2})
            return tools, result

    tools, result = asyncio.run(go())
    assert {t.name for t in tools.tools} == {
        "forever_status",
        "forever_lookup",
        "forever_explain_mechanic",
        "forever_sim_leveling",
        "forever_build",
        "forever_player_profile",  # T06b : profil joueur, lecture seule
    }
    assert not result.is_error
    frostbolt_rank_2 = read_json(DATA_DIR / LOCAL_VERSION / "spells.json")["spells"]["frostbolt"]["ranks"][1]
    assert result.structured_content["ranks"][0]["damage_min"] == frostbolt_rank_2[1]  # rank_format : min
    assert validate_provenance(result.structured_content["provenance"]) == []
