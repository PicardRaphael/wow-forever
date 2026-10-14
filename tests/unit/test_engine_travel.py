"""Trajets d'une feuille de route (RX1, bloc B, registre C4, C6, I19) : fonctions pures de
`forever/engine/travel.py`. Paramètres lus dans `mechanics.json` de la version du dépôt (`route.travel`, repris de
Factoruide) ; graphe et cartes décodés des fixtures `tests/fixtures/wago/travel/` ; positions de test synthétiques."""

import math

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.engine.travel import (
    PARAMS,
    Point,
    flight_seconds,
    map_to_world,
    run_speed,
    travel_params,
    travel_time,
    walk_seconds,
)
from forever.pipeline.travel_client import decode_travel, load_travel_tables
from forever.travel import graph_from_doc

VALUES = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
STORMWIND, SENTINEL_HILL = 2, 4  # lignes de TaxiNodes de la fixture
TO_SENTINEL_HILL = 6  # ligne de TaxiPath
ELWYNN = 1429
LEVEL = 10  # niveau de test (sous le niveau de la monture lu dans mechanics.json : vérifié par le test)
NEAR = 30.0  # yards : positions de test placées à côté d'un point de vol


@pytest.fixture(scope="module")
def doc():
    return decode_travel(load_travel_tables(FIXTURES / "wago" / "travel", RULES), RULES, LOCAL_VERSION)


@pytest.fixture(scope="module")
def world(doc):
    return graph_from_doc(doc, "alliance")


@pytest.fixture
def params():
    return travel_params(VALUES)


def near(node, dx=NEAR):
    return Point(node.point.continent, node.point.x + dx, node.point.y)


def test_params_come_from_mechanics(params):
    entry = VALUES["route.travel"]
    assert entry["certainty"] == "suppose" and "Factoruide" in entry["source"] and entry["registry"] == "C4"
    assert set(entry["value"]) == set(PARAMS)
    assert params.run_speed == float(entry["value"]["run_speed"])
    assert params.mount_level == int(entry["value"]["mount_level"]) and LEVEL < params.mount_level


def test_map_to_world(world):
    _, maps = world
    rect = maps[ELWYNN]
    centre = map_to_world(rect, 50.0, 50.0)
    assert centre.continent == rect.continent
    assert centre.x == pytest.approx((rect.min_x + rect.max_x) / 2)
    assert centre.y == pytest.approx((rect.min_y + rect.max_y) / 2)
    top_left = map_to_world(rect, 0.0, 0.0)  # nord-ouest de la carte : x et y du monde au maximum
    assert (top_left.x, top_left.y) == pytest.approx((rect.max_x, rect.max_y))


def test_straight_line_time(params):
    a, b = Point(0, 0.0, 0.0), Point(0, 300.0, 400.0)
    expected = math.dist((0.0, 0.0), (300.0, 400.0)) * params.detour / params.run_speed
    assert walk_seconds(a, b, params, LEVEL) == pytest.approx(expected, rel=1e-12)
    assert math.isinf(walk_seconds(a, Point(1, 0.0, 0.0), params, LEVEL))  # autre continent


def test_mount_speed_from_level(params):
    assert run_speed(params, params.mount_level - 1) == params.run_speed
    assert run_speed(params, params.mount_level) == pytest.approx(params.run_speed * (1 + params.mount_bonus))


def test_flight_used_when_known(world, doc, params):
    graph, _ = world
    a, b = near(graph.nodes[STORMWIND]), near(graph.nodes[SENTINEL_HILL])
    leg = travel_time(graph, a, b, params=params, level=LEVEL, flights_known={STORMWIND, SENTINEL_HILL})
    assert [step["kind"] for step in leg.legs] == ["walk", "fly", "walk"]
    length = next(p["length"] for p in doc["paths"] if p["id"] == TO_SENTINEL_HILL)
    expected = (
        walk_seconds(a, graph.nodes[STORMWIND].point, params, LEVEL)
        + flight_seconds(length, params)
        + walk_seconds(graph.nodes[SENTINEL_HILL].point, b, params, LEVEL)
    )
    assert leg.seconds == pytest.approx(expected, rel=1e-12)
    assert leg.seconds < walk_seconds(a, b, params, LEVEL)
    assert leg.certainty == "suppose"


def test_flight_ignored_when_unknown(world, params):
    graph, _ = world
    a, b = near(graph.nodes[STORMWIND]), near(graph.nodes[SENTINEL_HILL])
    leg = travel_time(graph, a, b, params=params, level=LEVEL, flights_known={STORMWIND})
    assert [step["kind"] for step in leg.legs] == ["walk"]
    assert leg.seconds == pytest.approx(walk_seconds(a, b, params, LEVEL), rel=1e-12)


def test_flight_seconds(params):
    assert flight_seconds(600.0, params) == pytest.approx(600.0 / params.flight_speed + params.flight_overhead)


def test_hearth_used_when_shorter(world, params):
    graph, _ = world
    a, b = near(graph.nodes[STORMWIND]), near(graph.nodes[SENTINEL_HILL])
    inn = near(graph.nodes[SENTINEL_HILL], dx=-NEAR)
    leg = travel_time(graph, a, b, params=params, level=LEVEL, flights_known=set(), hearth=inn)
    assert [step["kind"] for step in leg.legs] == ["hearth", "walk"]
    assert leg.seconds == pytest.approx(params.hearth_cast + walk_seconds(inn, b, params, LEVEL), rel=1e-12)


def test_unreachable_other_continent(world, params):
    graph, _ = world
    a = near(graph.nodes[STORMWIND])
    leg = travel_time(graph, a, Point(1, 0.0, 0.0), params=params, level=LEVEL, flights_known=set(graph.nodes))
    assert math.isinf(leg.seconds) and leg.legs == []
