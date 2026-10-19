"""Graphe des trajets d'une feuille de route (RX1, bloc B), assemblé hors du moteur.

Points de vol et trajets de `travel.json` (client, décision 266 : le client prime), filtrés par camp ; cartes de zone
pour convertir une position de carte en position monde. Le moteur (`forever/engine/travel.py`) calcule ensuite les
temps. Registre : I19."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from forever.config import Deps
from forever.engine.travel import FlightEdge, FlightNode, Graph, MapRect, Point

SIDES = {"horde": "H", "alliance": "A"}  # camp -> lettre des transports de Journeys
CITIES_KEY = "route.cities"  # RTE8 : cartes de zone des capitales des deux camps (mechanics.json)


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
    """Transports de Journeys permis au camp `faction` (bateaux et zeppelins : un circuit, chaque quai vers le
    suivant, le dernier vers le premier ; portails et tram : dans les deux sens, durée de l'addon). Registre : I19"""
    from forever.engine.travel import Point, Transport, ride_seconds

    side = SIDES[faction]
    out: list[Transport] = []
    for ship in network.ships:
        speed = network.speeds.get(ship.kind)
        if side not in ship.sides or not speed:
            continue
        docks = ship.docks  # circuit : chaque quai vers le suivant, le dernier vers le premier
        for i, dock in enumerate(docks):
            nxt = docks[(i + 1) % len(docks)]
            seconds = ride_seconds(dock.wait, dock.length, speed, network.board_s, network.loading_s)
            out.append(Transport(ship.kind, Point(dock.continent, dock.x, dock.y), Point(nxt.continent, nxt.x, nxt.y),
                                 seconds))  # fmt: skip
    for link in network.links:
        if side not in link.sides:
            continue
        a, b = Point(link.a[0], link.a[1], link.a[2]), Point(link.b[0], link.b[1], link.b[2])
        out += [Transport(link.kind, a, b, link.seconds), Transport(link.kind, b, a, link.seconds)]
    return tuple(out)


class WalkCache:
    """Marche par les réseaux de Journeys, avec mémoire (nœud le plus proche d'un point, distances d'un nœud).
    `city` : un point est-il dans une capitale (RTE8) ; `city_lines` : points de capitale atteints en ligne droite."""

    def __init__(self, nets: dict[int, Any], detour: float, city: Callable[[Point], bool] | None = None) -> None:
        self.nets = nets
        self.detour = detour
        self.city = city
        self.near: dict[Point, int | None] = {}
        self.dist: dict[tuple[int, int], list[float]] = {}
        self.inside: dict[Point, bool] = {}
        self.city_lines: set[Point] = set()

    def _distances(self, continent: int, node: int) -> list[float]:
        from forever.engine.travel import node_distances

        key = (continent, node)
        if key not in self.dist:
            self.dist[key] = node_distances(self.nets[continent], node)
        return self.dist[key]

    def _in_city(self, p: Point) -> bool:
        if self.city is None:
            return False
        if p not in self.inside:
            self.inside[p] = bool(self.city(p))
        return self.inside[p]

    def __call__(self, a: Point, b: Point) -> float:
        import math

        from forever.engine.travel import nearest_node, walk_yards

        net = self.nets.get(a.continent)
        if a.continent != b.continent:
            return math.inf
        if net is None:
            return math.nan  # pas de réseau sur ce continent : ligne droite allongée
        for p in (a, b):
            if p not in self.near:
                self.near[p] = nearest_node(net, p)
        source, target = self.near[a], self.near[b]
        if source is None or target is None:
            return math.nan
        dist = self._distances(a.continent, source)
        if source == target or math.isfinite(dist[target]):
            return walk_yards(net, a, b, detour=self.detour, distances=dist, ends=(source, target))
        in_city = (self._in_city(a), self._in_city(b))
        if not any(in_city):
            return math.inf  # île : un transport est nécessaire
        back = self._distances(a.continent, target) if in_city[0] else None
        yards = walk_yards(
            net, a, b, detour=self.detour, distances=dist, ends=(source, target), in_city=in_city, back=back
        )
        if math.isfinite(yards):
            self.city_lines.update(p for p, inside in zip((a, b), in_city, strict=True) if inside)
        return yards


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


def city_maps(values: Mapping[str, Any]) -> frozenset[int]:
    """Cartes de zone (uiMapID) des capitales des deux camps (`route.cities`) ; vide si la clé manque. Registre : C6"""
    entry = values.get(CITIES_KEY)
    if not isinstance(entry, Mapping):
        return frozenset()
    return frozenset(int(m) for m in (entry.get("value") or {}).get("maps", []))


def map_of(maps: Mapping[int, MapRect], point: Point | None) -> int | None:
    """Carte (uiMapID) qui contient un point du monde : la plus petite des cartes de son continent qui le couvrent."""
    if point is None:
        return None
    best: tuple[float, int] | None = None
    for ui_map, m in maps.items():
        if m.continent != point.continent:
            continue
        inside_x = min(m.min_x, m.max_x) <= point.x <= max(m.min_x, m.max_x)
        if inside_x and min(m.min_y, m.max_y) <= point.y <= max(m.min_y, m.max_y):
            area = abs(m.max_x - m.min_x) * abs(m.max_y - m.min_y)
            if best is None or area < best[0]:
                best = (area, ui_map)
    return best[1] if best else None


def city_line_warning(walker: Any, maps: Mapping[int, MapRect], names: Mapping[int, str]) -> str | None:
    """Avertissement d'une route dont un trajet finit en ligne droite dans une capitale (RTE8), None sinon."""
    points = getattr(walker, "city_lines", None)
    if not points:
        return None
    found = sorted({names.get(m, str(m)) for m in (map_of(maps, p) for p in points) if m is not None})
    where = ", ".join(found) if found else "une capitale"
    return (
        f"trajets supposés (suppose) : ligne droite allongée dans {where}, le réseau de marche de Journeys n'y "
        "reliant pas certains points (question RTE8)"
    )
