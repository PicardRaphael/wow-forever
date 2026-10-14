"""Trajets d'une feuille de route (RX1, bloc B), fonctions pures.

Distance et temps d'un trajet sur un graphe déjà construit (`forever/travel.py`) : marche en ligne droite dans un
continent (allongée d'un facteur de détour), vol entre points de vol connus (longueur des trajets du client), pierre
de foyer. Paramètres dans `mechanics.json` (`route.travel`, repris de Factoruide, `suppose`). Positions en yards du
monde (`continent`, `x`, `y`) ; une carte de zone donne des pourcentages convertis par ses bornes
(`UiMapAssignment`). Registre : C4 (vitesse du joueur), C6 (temps en mouvement hors combat), I19 (trajets)."""

from __future__ import annotations

from collections.abc import Mapping
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


class Graph(NamedTuple):
    nodes: dict[int, FlightNode]
    edges: dict[int, list[FlightEdge]]  # départ -> trajets


class Leg(NamedTuple):
    seconds: float
    legs: list[dict[str, Any]]  # étapes : {"kind": walk|fly|hearth, "seconds", ...}
    certainty: str


def travel_params(values: Mapping[str, Any]) -> TravelParams:
    """Paramètres des trajets (`mechanics.json`, `route.travel`). Registre : C4"""
    raise NotImplementedError


def map_to_world(rect: MapRect, x_pct: float, y_pct: float) -> Point:
    """Position monde d'un point de carte en pourcentage (0 à 100) : x croît vers l'est (y du monde décroît),
    y croît vers le sud (x du monde décroît). Registre : I19"""
    raise NotImplementedError


def run_speed(params: TravelParams, level: int) -> float:
    """Vitesse au sol (yards par seconde) : course, majorée de la monture à partir de `mount_level`. Registre : C4"""
    raise NotImplementedError


def walk_seconds(a: Point, b: Point, params: TravelParams, level: int) -> float:
    """Secondes à pied (ligne droite × détour) ; infini entre deux continents. Registre : C6"""
    raise NotImplementedError


def flight_seconds(length: float, params: TravelParams) -> float:
    """Secondes d'un vol de `length` yards, frais fixes compris. Registre : I19"""
    raise NotImplementedError


def travel_time(
    graph: Graph,
    a: Point,
    b: Point,
    *,
    params: TravelParams,
    level: int,
    flights_known: AbstractSet[int],
    hearth: Point | None = None,
) -> Leg:
    """Trajet le plus court de `a` à `b` : à pied, par vols entre points connus, ou par la pierre de foyer (`hearth` :
    position de l'auberge liée, None si la pierre n'est pas disponible). Registre : C6, I19"""
    raise NotImplementedError
