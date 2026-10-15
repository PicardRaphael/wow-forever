"""CJ1, bloc 4 (décision 276) : équipement de leveling lu dans GearQuest Forever (meilleur choix de chaque emplacement
pour le niveau et le camp, avec ce que l'addon dit pour l'obtenir) ; « est-ce une amélioration ? » (score de l'objet
par les poids, face à l'objet porté au même emplacement ; « non calculé » sans statistiques) ; commande
`forever gear` et outil MCP `forever_gear`, provenance complète, aucun texte d'addon recopié dans le dépôt.

Valeurs : addons fabriqués `tests/fixtures/addons/gear/` ; données de la version du dépôt. Aucun chiffre de jeu ici."""

import asyncio
import json
import shutil

from conftest import FIXTURES
from mcp import Client

from forever.cli import main
from forever.gear import is_upgrade, leveling_gear
from forever.mcp_server import build_server
from forever.provenance import validate_provenance

ADDONS = FIXTURES / "addons" / "gear"
WEIGHTS = {"int": 1.0, "sp": 2.0, "scrit": 20.0, "shit": 30.0}


def test_leveling_gear_best_pick_per_slot_for_level_and_faction():
    picks = leveling_gear(ADDONS, "MAGE", level=20, faction="alliance")
    head = next(p for p in picks if p["slot"] == "Head")
    assert head["item"] == 900001 and head["name"] == "Fixture Hood" and head["zone"] == "Fixture Vale"
    assert not any(p["slot"] == "Finger" for p in picks)  # choix de la Horde seulement
    assert leveling_gear(ADDONS, "MAGE", level=30, faction="alliance") == []


def test_upgrade_compares_with_the_equipped_item_of_the_slot():
    better = is_upgrade(ADDONS, item=900001, equipped=[900002], weights=WEIGHTS)
    assert better["verdict"] == "amélioration" and better["delta"] > 0 and better["slot"] == 1
    worse = is_upgrade(ADDONS, item=900002, equipped=[900001], weights=WEIGHTS)
    assert worse["verdict"] == "pas mieux" and worse["delta"] < 0
    free = is_upgrade(ADDONS, item=900003, equipped=[], weights=WEIGHTS)
    assert free["verdict"] == "amélioration" and free["equipped"] is None
    unknown = is_upgrade(ADDONS, item=900007, equipped=[], weights=WEIGHTS)
    assert unknown["verdict"] == "non calculé"


def _wow(tmp_path):
    root = tmp_path / "wow"
    shutil.copytree(ADDONS, root / "Interface" / "AddOns")
    return root


def test_gear_cli_weights_and_bis(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(_wow(tmp_path)))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    assert main(["gear", "weights", "--level", "20", "--race", "Gnome", "--spec", "frost-mage", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert validate_provenance(doc["provenance"]) == []
    assert doc["naowh"].startswith("NFSW1:frost-mage:") and doc["pawn"].startswith("( Pawn: v1:")
    argv = ["gear", "bis", "--class", "Mage", "--spec", "fire-mage", "--faction", "alliance", "--level", "20"]
    assert main([*argv, "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert validate_provenance(doc["provenance"]) == [] and doc["export"].startswith("!NBIS1!")
    assert doc["slots"]["1"] == 900001 or doc["slots"].get(1) == 900001


def test_mcp_forever_gear(make_deps, tmp_path):
    deps = make_deps(wow_dir=_wow(tmp_path), offline=True)

    async def go():
        async with Client(build_server(deps)) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            leveling = await client.call_tool(
                "forever_gear",
                {"action": "leveling", "class_name": "Mage", "level": 20, "faction": "alliance"},
            )
            upgrade = await client.call_tool(
                "forever_gear",
                {"action": "upgrade", "class_name": "Warrior", "item": 900006, "equipped": []},
            )
            return tools, leveling, upgrade

    tools, leveling, upgrade = asyncio.run(go())
    assert "forever_gear" in tools and not leveling.is_error and not upgrade.is_error
    assert validate_provenance(leveling.structured_content["provenance"]) == []
    assert leveling.structured_content["picks"][0]["item"] == 900001
    assert upgrade.structured_content["verdict"] == "amélioration"
    assert upgrade.structured_content["weights_source"].startswith("Forever Companion")
