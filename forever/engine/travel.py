"""Trajets d'une feuille de route (RX1, bloc B), fonctions pures.

Distance et temps d'un trajet sur un graphe déjà construit (`forever/travel.py`) : marche en ligne droite dans un
continent (allongée d'un facteur de détour), vol entre points de vol connus (longueur des trajets du client), pierre
de foyer. Paramètres dans `mechanics.json` (`route.travel`, repris de Factoruide, `suppose`). Positions en yards du
monde (`continent`, `x`, `y`) ; une carte de zone donne des pourcentages convertis par ses bornes
(`UiMapAssignment`). Registre : C4 (vitesse du joueur), C6 (temps en mouvement hors combat), I19 (trajets)."""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable, Mapping
from collections.abc import Set as AbstractSet
from typing import Any, NamedTuple

TRAVEL_KEY = "route.travel"
PARAMS = (
    "run_speed",
    "mount_level",
    "mount_bonus",
    "flight_speed",
    "detour",
    "flight_overhead",
    "hearth_cast",
    "hearth_cooldown",
)


class TravelParams(NamedTuple):
    run_speed: float  # yards par seconde
    mount_level: int
    mount_bonus: float  # part ajoutée à la vitesse de course
    flight_speed: float  # yards par seconde
    detour: float  # allongement de la ligne droite à pied
    flight_overhead: float  # secondes par vol (parler au maître, décollage, atterrissage)
    hearth_cast: float  # secondes
    hearth_cooldown: float  # secondes


class Point(NamedTuple):
    continent: int
    x: float  # yards du monde
    y: float


class MapRect(NamedTuple):
    ui_map: int
    continent: int
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class FlightNode(NamedTuple):
    id: int
    name: str
    point: Point


class FlightEdge(NamedTuple):
    to: int
    length: float  # yards


class Transport(NamedTuple):
    """Trajet d'un transport (bateau, zeppelin, portail, tram) d'un point à un autre, durée comprise."""

    kind: str
    a: Point
    b: Point
    seconds: float


class WalkNet(NamedTuple):
    """Réseau de marche d'un continent : nœuds (x, y) et voisins (nœud, yards de marche)."""

    continent: int
    points: list[tuple[float, float]]
    adj: list[list[tuple[int, float]]]


class Graph(NamedTuple):
    nodes: dict[int, FlightNode]
    edges: dict[int, list[FlightEdge]]  # départ -> trajets
    transports: tuple[Transport, ...] = ()


class Leg(NamedTuple):
    seconds: float
    legs: list[dict[str, Any]]  # étapes : {"kind": walk|fly|hearth, "seconds", ...}
    certainty: str


CERTAINTY = "suppose"  # vitesses et détour repris de Factoruide (TRV1)
PERCENT = 100.0  # conversion d'unité : position de carte en pourcentage


def travel_params(values: Mapping[str, Any]) -> TravelParams:
    """Paramètres des trajets (`mechanics.json`, `route.travel`). Registre : C4"""
    raw = values[TRAVEL_KEY]["value"]
    return TravelParams(
        run_speed=float(raw["run_speed"]),
        mount_level=int(raw["mount_level"]),
        mount_bonus=float(raw["mount_bonus"]),
        flight_speed=float(raw["flight_speed"]),
        detour=float(raw["detour"]),
        flight_overhead=float(raw["flight_overhead"]),
        hearth_cast=float(raw["hearth_cast"]),
        hearth_cooldown=float(raw["hearth_cooldown"]),
    )


def map_to_world(rect: MapRect, x_pct: float, y_pct: float) -> Point:
    """Position monde d'un point de carte en pourcentage (0 à 100) : x croît vers l'est (y du monde décroît),
    y croît vers le sud (x du monde décroît). Registre : I19"""
    fx, fy = x_pct / PERCENT, y_pct / PERCENT
    return Point(
        rect.continent,
        rect.max_x - fy * (rect.max_x - rect.min_x),
        rect.max_y - fx * (rect.max_y - rect.min_y),
    )


def run_speed(params: TravelParams, level: int) -> float:
    """Vitesse au sol (yards par seconde) : course, majorée de la monture à partir de `mount_level`. Registre : C4"""
    if level >= params.mount_level:
        return params.run_speed * (1 + params.mount_bonus)
    return params.run_speed


def walk_seconds(a: Point, b: Point, params: TravelParams, level: int) -> float:
    """Secondes à pied (ligne droite × détour) ; infini entre deux continents. Registre : C6"""
    if a.continent != b.continent:
        return math.inf
    return math.dist((a.x, a.y), (b.x, b.y)) * params.detour / run_speed(params, level)


def flight_seconds(length: float, params: TravelParams) -> float:
    """Secondes d'un vol de `length` yards, frais fixes compris. Registre : I19"""
    return length / params.flight_speed + params.flight_overhead


def _flights(graph: Graph, start: int, known: AbstractSet[int], params: TravelParams) -> dict[int, tuple[float, int]]:
    """Plus courts vols depuis `start` entre points connus : arrivée -> (secondes, précédent). Chaque trajet compte
    ses frais fixes (un atterrissage par trajet du client)."""
    best: dict[int, tuple[float, int]] = {start: (0.0, start)}
    queue = [(0.0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost > best[node][0]:
            continue
        for edge in graph.edges.get(node, []):
            if edge.to not in known:
                continue
            nxt = cost + flight_seconds(edge.length, params)
            if edge.to not in best or nxt < best[edge.to][0]:
                best[edge.to] = (nxt, node)
                heapq.heappush(queue, (nxt, edge.to))
    return best


def _walk_s(
    a: Point, b: Point, params: TravelParams, level: int, walk: Callable[[Point, Point], float] | None
) -> float:
    """Secondes à pied : réseau de marche (`walk`, yards) s'il est donné ; `walk` rend NaN sans réseau pour ces
    points (ligne droite allongée) et l'infini quand le réseau ne les relie pas (île : un transport est nécessaire)."""
    if a.continent != b.continent:
        return math.inf
    if walk is None:
        return walk_seconds(a, b, params, level)
    yards = walk(a, b)
    if math.isnan(yards):
        return walk_seconds(a, b, params, level)
    return yards / run_speed(params, level)


def travel_time(
    graph: Graph,
    a: Point,
    b: Point,
    *,
    params: TravelParams,
    level: int,
    flights_known: AbstractSet[int],
    hearth: Point | None = None,
    walk: Callable[[Point, Point], float] | None = None,
) -> Leg:
    """Trajet le plus court de `a` à `b` (Dijkstra sur les points utiles : départ, arrivée, points de vol connus,
    quais et extrémités des transports) : marche (réseau `walk` en yards, sinon ligne droite allongée), vols entre
    points connus, transports (bateaux, zeppelins, portails, tram), pierre de foyer depuis le départ (`hearth` :
    auberge liée, None si indisponible). Registre : C6, I19"""
    hubs: list[Point] = [a, b]
    flight_hub: dict[int, int] = {}
    for node in sorted(n for n in flights_known if n in graph.nodes):
        flight_hub[node] = len(hubs)
        hubs.append(graph.nodes[node].point)
    ride: dict[int, list[tuple[int, float, Transport]]] = {}
    for t in graph.transports:
        ia, ib = len(hubs), len(hubs) + 1
        hubs += [t.a, t.b]
        ride.setdefault(ia, []).append((ib, t.seconds, t))
    fly: dict[int, list[tuple[int, float, int, int]]] = {}
    for start, i in flight_hub.items():
        for end, (seconds, _) in _flights(graph, start, flights_known, params).items():
            if end != start and end in flight_hub:
                fly.setdefault(i, []).append((flight_hub[end], seconds, start, end))
    best: dict[int, float] = {0: 0.0}
    prev: dict[int, tuple[int, dict[str, Any]]] = {}
    queue: list[tuple[float, int]] = [(0.0, 0)]
    if hearth is not None:
        hubs.append(hearth)
        best[len(hubs) - 1] = params.hearth_cast
        prev[len(hubs) - 1] = (0, {"kind": "hearth", "seconds": params.hearth_cast})
        heapq.heappush(queue, (params.hearth_cast, len(hubs) - 1))
    while queue:
        cost, u = heapq.heappop(queue)
        if cost > best.get(u, math.inf) or u == 1:
            continue
        moves: list[tuple[int, float, dict[str, Any]]] = []
        for v, point in enumerate(hubs):
            if v != u and point.continent == hubs[u].continent:
                s = _walk_s(hubs[u], point, params, level, walk)
                moves.append((v, s, {"kind": "walk", "seconds": s}))
        for v, s, t in ride.get(u, []):
            moves.append((v, s, {"kind": "ride", "seconds": s, "transport": t.kind}))
        for v, s, start, end in fly.get(u, []):
            moves.append((v, s, {"kind": "fly", "seconds": s, "from": start, "to": end}))
        for v, s, leg in moves:
            total = cost + s
            if total < best.get(v, math.inf):
                best[v] = total
                prev[v] = (u, leg)
                heapq.heappush(queue, (total, v))
    if 1 not in best:
        return Leg(math.inf, [], CERTAINTY)
    legs: list[dict[str, Any]] = []
    node = 1
    while node != 0:
        node, leg = prev[node]
        legs.append(leg)
    legs.reverse()
    merged: list[dict[str, Any]] = []
    for leg in legs:  # deux marches de suite (passage par un point sans s'y arrêter) : une seule
        if merged and leg["kind"] == "walk" and merged[-1]["kind"] == "walk":
            merged[-1] = {"kind": "walk", "seconds": merged[-1]["seconds"] + leg["seconds"]}
        else:
            merged.append(leg)
    return Leg(best[1], merged, CERTAINTY)


def ride_seconds(wait: float, length: float, speed: float, board_s: float, loading_s: float) -> float:
    """Durée d'un trajet de bateau ou de zeppelin : attente au quai, traversée, embarquement et chargement.
    Registre : I19"""
    return wait + length / speed + board_s + loading_s


def nearest_node(net: WalkNet, p: Point) -> int | None:
    """Nœud du réseau le plus proche de `p` (même continent), None si le réseau est vide ou d'un autre continent."""
    if p.continent != net.continent or not net.points:
        return None
    return min(range(len(net.points)), key=lambda i: (net.points[i][0] - p.x) ** 2 + (net.points[i][1] - p.y) ** 2)


def node_distances(net: WalkNet, source: int) -> list[float]:
    """Yards de marche du nœud `source` vers chaque nœud (Dijkstra ; infini si inatteignable). Registre : C6"""
    dist = [math.inf] * len(net.points)
    dist[source] = 0.0
    queue = [(0.0, source)]
    while queue:
        d, u = heapq.heappop(queue)
        if d > dist[u]:
            continue
        for v, w in net.adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(queue, (d + w, v))
    return dist


def walk_yards(
    net: WalkNet,
    a: Point,
    b: Point,
    *,
    detour: float,
    distances: list[float] | None = None,
    ends: tuple[int | None, int | None] | None = None,
) -> float:
    """Yards à pied de `a` à `b` par le réseau : ligne droite jusqu'au nœud le plus proche de chaque point, puis le
    réseau ; même nœud des deux côtés : ligne droite allongée de `detour`. `distances` : distances déjà calculées
    depuis le nœud de `a` ; `ends` : nœuds les plus proches déjà connus. Registre : C6, I19"""
    na, nb = ends if ends is not None else (nearest_node(net, a), nearest_node(net, b))
    if na is None or nb is None:
        return math.inf
    if na == nb:
        return math.dist((a.x, a.y), (b.x, b.y)) * detour
    dist = distances if distances is not None else node_distances(net, na)
    through = dist[nb]
    if not math.isfinite(through):
        return math.inf
    return math.dist((a.x, a.y), net.points[na]) + through + math.dist(net.points[nb], (b.x, b.y))
