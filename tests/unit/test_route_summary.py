"""Essai CJ-6 du 2026-10-15, défaut 2 : l'aperçu de route était « trop long pour être ouvert » dans la conversation
(plan complet rendu par `forever_route` : arrêts, étapes, texte du guide RestedXP). L'outil rend désormais un résumé
compact par défaut (durée, XP par heure, zones dans l'ordre, donjons, quêtes de classe, récompenses notables, cinq
premiers arrêts, base utilisée, provenance) ; la route complète reste sur le disque pour la livraison ; `detail=True`
rend le plan entier.

Valeurs : plan fabriqué à partir de `tests/fixtures/rxp/plan.json`, grossi ici (arrêts répétés, guide de 900 lignes) ;
fixture du client simulé pour l'outil MCP. Aucun chiffre de jeu ici."""

import asyncio
import copy
import json

from conftest import FIXTURES, read_json
from mcp import Client

from forever.mcp_server import build_server
from forever.route import route_summary

PLAN = read_json(FIXTURES / "rxp" / "plan.json")
MAX_SUMMARY = 8000  # caractères du résumé sérialisé : bien sous la limite d'un résultat d'outil de Claude Code
WALK = [s for s in PLAN["stops"] if s["kind"] not in ("dungeon", "dungeon_repeat")]  # arrêts hors donjon


def big_plan():
    plan = copy.deepcopy(PLAN)
    zones = ["Fixture Vale", "Fixture Hills", "Fixture Vale", "Fixture Coast"]
    stops = []
    for i in range(120):
        stop = dict(WALK[i % len(WALK)])
        stop.update(zone=zones[(i // 30) % len(zones)], text=f"arrêt {i}", seconds=1.0, travel_s=0.5)
        stops.append(stop)
    stops[3].update(kind="accept", name="Fixture Class Call", class_quest=True)
    stops[7].update(kind="dungeon", name="Fixture Depths", level=8)
    plan.update(
        stops=stops,
        steps=[{"text": f"étape {i}"} for i in range(400)],
        hours=3.1,
        xp_h=2900.0,
        rewards=[{"quest": 101, "item": 9001, "name": "Fixture Gloves"}],
        reminders=[{"text": "pose le sac de couchage"}],
        warnings=[f"quête {i} écartée" for i in range(60)],
        request={
            "class_name": "mage",
            "faction": "alliance",
            "race": "Gnome",
            "character": "Go",
            "done": list(range(300)),
        },
        basis={
            "kind": "adapted",
            "guides": ["RXP Gnome"],
            "verdict": "acceptée",
            "attribution": "RestedXP Guides",
            "body": "\n".join(f"ligne {i} du guide" for i in range(900)),
            "additions": [1],
            "accepted": True,
        },
        provenance={"game_version": "x", "certainty": "probable"},
    )
    return plan


def test_summary_is_compact_and_says_what_the_player_needs():
    plan = big_plan()
    summary = route_summary(plan)
    assert len(json.dumps(summary, ensure_ascii=False)) < MAX_SUMMARY
    assert len(json.dumps(plan, ensure_ascii=False)) > 4 * MAX_SUMMARY  # le plan complet, lui, est long
    assert summary["id"] == plan["id"] and summary["hours"] == 3.1 and summary["xp_h"] == 2900.0
    assert summary["zones"] == ["Fixture Vale", "Fixture Hills", "Fixture Coast"]  # ordre de première visite
    assert summary["dungeons"] == [{"name": "Fixture Depths", "level": 8}]
    assert summary["class_quests"] == ["Fixture Class Call"]
    assert summary["rewards"] == plan["rewards"] and summary["stops_total"] == 120
    assert [s["text"] for s in summary["first_stops"]] == [f"arrêt {i}" for i in range(5)]
    assert summary["basis"]["kind"] == "adapted" and "body" not in summary["basis"]
    assert "stops" not in summary and "steps" not in summary
    assert summary["request"]["race"] == "Gnome" and "done" not in summary["request"]
    assert summary["provenance"] == plan["provenance"]
    assert "disque" in summary["full_route"]


def test_mcp_route_is_compact_by_default_and_full_on_demand(make_deps):
    deps = make_deps(wow_dir=FIXTURES / "addons" / "dungeons", offline=True)
    args = {"action": "plan", "class_name": "hunter", "faction": "horde", "start_level": 1, "end_level": 3,
            "race": "Orc", "character": "Bob"}  # fmt: skip

    async def go():
        async with Client(build_server(deps)) as client:
            compact = await client.call_tool("forever_route", args)
            full = await client.call_tool("forever_route", {**args, "detail": True})
            return compact.structured_content, full.structured_content

    compact, full = asyncio.run(go())
    assert "stops" not in compact and len(compact["first_stops"]) <= 5 and compact["stops_total"] >= 1
    assert compact["request"]["race"] == "Orc" and compact["provenance"]
    assert isinstance(full["stops"], list) and len(full["stops"]) == compact["stops_total"]
