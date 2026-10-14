"""Graphe des trajets d'une feuille de route (RX1, bloc B), assemblé hors du moteur.

Points de vol et trajets de `travel.json` (client, décision 266 : le client prime), filtrés par camp ; cartes de zone
pour convertir une position de carte en position monde. Le moteur (`forever/engine/travel.py`) calcule ensuite les
temps. Registre : I19."""

from __future__ import annotations

import json
from typing import Any

from forever.config import Deps
from forever.engine.travel import FlightEdge, FlightNode, Graph, MapRect, Point


def load_travel(deps: Deps, faction: str) -> tuple[Graph, dict[int, MapRect]]:
    """Graphe des vols du camp `faction` (« horde » ou « alliance ») et cartes de zone de la version installée."""
    from forever.pipeline.travel_client import TRAVEL_FILE
    from forever.store import load_version

    data = load_version(deps)
    doc = json.loads((data.path / TRAVEL_FILE).read_text(encoding="utf-8"))
    return graph_from_doc(doc, faction)


def graph_from_doc(doc: dict[str, Any], faction: str) -> tuple[Graph, dict[int, MapRect]]:
    nodes = {
        n["id"]: FlightNode(n["id"], n["name"], Point(n["continent"], n["x"], n["y"]))
        for n in doc["nodes"]
        if n.get("faction") in (faction, "both")
    }
    edges: dict[int, list[FlightEdge]] = {}
    for p in doc["paths"]:
        if p["from"] in nodes and p["to"] in nodes:
            edges.setdefault(p["from"], []).append(FlightEdge(p["to"], float(p["length"])))
    maps = {
        m["ui_map"]: MapRect(m["ui_map"], m["continent"], m["min_x"], m["min_y"], m["max_x"], m["max_y"])
        for m in doc["maps"]
    }
    return Graph(nodes, edges), maps


def transports_from_network(network: Any, faction: str) -> tuple[Any, ...]:
    """Transports de Journeys permis au camp `faction`, dans les deux sens (bateaux et zeppelins : un trajet par
    quai vers le suivant ; portails et tram : durée de l'addon). Registre : I19"""
    raise NotImplementedError
