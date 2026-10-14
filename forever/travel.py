"""Graphe des trajets d'une feuille de route (RX1, bloc B), assemblé hors du moteur.

Points de vol et trajets de `travel.json` (client, décision 266 : le client prime), filtrés par camp ; cartes de zone
pour convertir une position de carte en position monde. Le moteur (`forever/engine/travel.py`) calcule ensuite les
temps. Registre : I19."""

from __future__ import annotations

import json
from typing import Any

from forever.config import Deps
from forever.engine.travel import FlightEdge, FlightNode, Graph, MapRect, Point

SIDES = {"horde": "H", "alliance": "A"}  # camp -> lettre des transports de Journeys


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
    from forever.engine.travel import Point, Transport, ride_seconds

    side = SIDES[faction]
    out: list[Transport] = []
    for ship in network.ships:
        speed = network.speeds.get(ship.kind)
        if side not in ship.sides or not speed:
            continue
        docks = ship.docks
        for i, dock in enumerate(docks):
            nxt = docks[(i + 1) % len(docks)]
            if len(docks) == 2 or i + 1 < len(docks):
                seconds = ride_seconds(dock.wait, dock.length, speed, network.board_s, network.loading_s)
                out.append(Transport(ship.kind, Point(dock.continent, dock.x, dock.y),
                                     Point(nxt.continent, nxt.x, nxt.y), seconds))  # fmt: skip
            if len(docks) > 2 and i > 0:  # escale : retour vers le quai précédent
                back = docks[i - 1]
                seconds = ride_seconds(dock.wait, back.length, speed, network.board_s, network.loading_s)
                out.append(Transport(ship.kind, Point(dock.continent, dock.x, dock.y),
                                     Point(back.continent, back.x, back.y), seconds))  # fmt: skip
    for link in network.links:
        if side not in link.sides:
            continue
        a, b = Point(link.a[0], link.a[1], link.a[2]), Point(link.b[0], link.b[1], link.b[2])
        out += [Transport(link.kind, a, b, link.seconds), Transport(link.kind, b, a, link.seconds)]
    return tuple(out)


class WalkCache:
    """Marche par les réseaux de Journeys, avec mémoire (nœud le plus proche d'un point, distances d'un nœud)."""

    def __init__(self, nets: dict[int, Any], detour: float) -> None:
        self.nets = nets
        self.detour = detour
        self.near: dict[Point, int | None] = {}
        self.dist: dict[tuple[int, int], list[float]] = {}

    def __call__(self, a: Point, b: Point) -> float:
        import math

        from forever.engine.travel import nearest_node, node_distances, walk_yards

        net = self.nets.get(a.continent)
        if net is None or a.continent != b.continent:
            return math.inf
        for p in (a, b):
            if p not in self.near:
                self.near[p] = nearest_node(net, p)
        source, target = self.near[a], self.near[b]
        if source is None or target is None:
            return math.inf
        key = (a.continent, source)
        if key not in self.dist:
            self.dist[key] = node_distances(net, source)
        return walk_yards(net, a, b, detour=self.detour, distances=self.dist[key], ends=(source, target))


def walk_nets(raw: dict[int, Any]) -> dict[int, Any]:
    """Réseaux de marche du moteur (`WalkNet`) à partir du graphe lu dans Journeys."""
    from forever.engine.travel import WalkNet

    nets = {}
    for continent, (points, edges) in raw.items():
        adj: list[list[tuple[int, float]]] = [[] for _ in points]
        for a, b, w in edges:
            adj[a].append((b, w))
            adj[b].append((a, w))
        nets[continent] = WalkNet(continent, points, adj)
    return nets
