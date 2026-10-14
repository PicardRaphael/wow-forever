"""Trajets complets d'une feuille de route (RX1, bloc F, registre C6, I19) : transports et réseau de marche de Naowh
Journeys lus en local, changement de continent, temps de marche par le réseau. Fixtures synthétiques
`tests/fixtures/addons/journeys/` ; le graphe de marche (base64, deflate, CBOR) est fabriqué ici. Aucun chiffre de
jeu ici : les valeurs viennent des fixtures ou de `mechanics.json`."""

import base64
import math
import shutil
import struct
import zlib

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.engine.travel import (
    Graph,
    Point,
    Transport,
    WalkNet,
    nearest_node,
    node_distances,
    ride_seconds,
    travel_params,
    travel_time,
    walk_yards,
)
from forever.pipeline.travel_sources import read_journeys_network, read_journeys_walks
from forever.travel import transports_from_network

ADDONS = FIXTURES / "addons" / "journeys" / "Interface" / "AddOns"
VALUES = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
TP = travel_params(VALUES)
LEVEL = 10  # sous le niveau de la monture lu dans mechanics.json (vérifié ci-dessous)


# --- CBOR minimal pour fabriquer la fixture (entiers, chaînes, tableaux, tables) --------------------------------


def _head(major: int, n: int) -> bytes:
    if n < 24:
        return bytes([major << 5 | n])
    if n < 256:
        return bytes([major << 5 | 24, n])
    if n < 65536:
        return bytes([major << 5 | 25]) + struct.pack(">H", n)
    return bytes([major << 5 | 26]) + struct.pack(">I", n)


def cbor(value) -> bytes:
    if isinstance(value, int):
        return _head(0, value) if value >= 0 else _head(1, -1 - value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return _head(3, len(raw)) + raw
    if isinstance(value, list):
        return _head(4, len(value)) + b"".join(cbor(v) for v in value)
    if isinstance(value, dict):
        return _head(5, len(value)) + b"".join(cbor(k) + cbor(v) for k, v in value.items())
    raise TypeError(value)


def packed(doc) -> str:
    deflate = zlib.compressobj(wbits=-15)
    raw = deflate.compress(cbor(doc)) + deflate.flush()
    return base64.b64encode(raw).decode("ascii")


# Carré de 4 nœuds sans diagonale (un mur au milieu) : 0 (0,0), 1 (1000,0), 2 (1000,1000), 3 (0,1000)
SQUARE = {
    "c": [0, 0, 0, 1000, 0, 0, 1000, 1000, 0, 0, 1000, 0],
    "e": [1, 2, 1100, 2, 3, 1200, 3, 4, 1300, 4, 1, 1400],
}


@pytest.fixture
def addons(tmp_path):
    root = tmp_path / "AddOns"
    shutil.copytree(ADDONS, root)
    data = root / "NaowhForever_JourneysData" / "Data"
    data.mkdir(parents=True)
    (data / "Map0.lua").write_text(
        "-- fixture\nlocal ns = _G.NaowhForever\n\n"
        f'ns.JourneyData.graph[0] = "{packed(SQUARE)}"\n'
        f'ns.JourneyData.walks[0] = "{packed({"k": [], "d": [], "r": []})}"\n',
        encoding="utf-8",
    )
    return root


def test_journeys_network_read():
    net = read_journeys_network(ADDONS)
    assert net is not None
    assert [s.kind for s in net.ships] == ["Boat", "Zeppelin"]
    boat = net.ships[0]
    assert boat.sides == "AH" and [d.name for d in boat.docks] == ["West Dock", "East Dock"]
    assert (boat.docks[0].continent, boat.docks[0].wait, boat.docks[0].length) == (0, 30, 1000)
    assert net.speeds == {"Boat": 10, "Zeppelin": 20} and (net.board_s, net.loading_s) == (4, 6)
    assert [(link.kind, link.seconds) for link in net.links] == [("Tram", 50)]
    assert read_journeys_network(FIXTURES / "addons" / "dungeons" / "Interface" / "AddOns") is None  # addon absent


def test_journeys_walk_graph(addons):
    walks = read_journeys_walks(addons)
    points, edges = walks[0]
    assert points == [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)]
    assert sorted(edges) == [(0, 1, 1100.0), (0, 3, 1400.0), (1, 2, 1200.0), (2, 3, 1300.0)]
    assert read_journeys_walks(ADDONS) == {}  # données de marche absentes : aucun réseau


def _net():
    points = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)]
    adj = [
        [(1, 1100.0), (3, 1400.0)],
        [(0, 1100.0), (2, 1200.0)],
        [(1, 1200.0), (3, 1300.0)],
        [(2, 1300.0), (0, 1400.0)],
    ]
    return WalkNet(0, points, adj)


def test_walk_through_the_network():
    net = _net()
    assert nearest_node(net, Point(0, 10.0, 990.0)) == 3
    assert nearest_node(net, Point(1, 0.0, 0.0)) is None  # autre continent
    assert node_distances(net, 0) == [0.0, 1100.0, 2300.0, 1400.0]
    a, b = Point(0, 10.0, 0.0), Point(0, 1000.0, 990.0)  # près du nœud 0 et du nœud 2
    expected = math.dist((10, 0), (0, 0)) + 2300.0 + math.dist((1000, 1000), (1000, 990))
    assert walk_yards(net, a, b, detour=TP.detour) == pytest.approx(expected, rel=1e-12)
    near_a, near_b = Point(0, 0.0, 10.0), Point(0, 10.0, 0.0)  # même nœud : ligne droite allongée
    assert walk_yards(net, near_a, near_b, detour=TP.detour) == pytest.approx(
        math.dist((0, 10), (10, 0)) * TP.detour, rel=1e-12
    )


def test_walk_network_used_by_travel_time():
    net = _net()
    a, b = Point(0, 10.0, 0.0), Point(0, 1000.0, 990.0)
    assert LEVEL < TP.mount_level
    walk = lambda p, q: walk_yards(net, p, q, detour=TP.detour)
    leg = travel_time(Graph({}, {}), a, b, params=TP, level=LEVEL, flights_known=frozenset(), walk=walk)
    assert leg.seconds == pytest.approx(walk(a, b) / TP.run_speed, rel=1e-12)
    straight = travel_time(Graph({}, {}), a, b, params=TP, level=LEVEL, flights_known=frozenset())
    assert straight.seconds < leg.seconds  # le mur rallonge le trajet


def test_ride_seconds():
    assert ride_seconds(30, 1000, 10, 4, 6) == pytest.approx(30 + 1000 / 10 + 4 + 6, rel=1e-12)


def test_transports_follow_faction_and_direction():
    net = read_journeys_network(ADDONS)
    horde = transports_from_network(net, "horde")
    alliance = transports_from_network(net, "alliance")
    assert {t.kind for t in horde} == {"Boat", "Zeppelin", "Tram"}
    assert {t.kind for t in alliance} == {"Boat", "Tram"}  # zeppelin de la Horde seulement
    boat = [t for t in alliance if t.kind == "Boat"]
    west, east = net.ships[0].docks
    out = next(t for t in boat if t.a.continent == 0)
    back = next(t for t in boat if t.a.continent == 1)
    assert out.seconds == pytest.approx(ride_seconds(west.wait, west.length, 10, 4, 6), rel=1e-12)
    assert back.seconds == pytest.approx(ride_seconds(east.wait, east.length, 10, 4, 6), rel=1e-12)
    tram = next(t for t in alliance if t.kind == "Tram")
    assert tram.seconds == 50


def test_transport_leg_changes_continent():
    dock_a, dock_b = Point(0, 0.0, 0.0), Point(1, 0.0, 0.0)
    boat = Transport("Boat", dock_a, dock_b, 140.0)
    a, b = Point(0, 300.0, 400.0), Point(1, 600.0, 800.0)
    assert math.isinf(travel_time(Graph({}, {}), a, b, params=TP, level=LEVEL, flights_known=frozenset()).seconds)
    leg = travel_time(Graph({}, {}, (boat,)), a, b, params=TP, level=LEVEL, flights_known=frozenset())
    walk_a = 500.0 * TP.detour / TP.run_speed
    walk_b = 1000.0 * TP.detour / TP.run_speed
    assert leg.seconds == pytest.approx(walk_a + 140.0 + walk_b, rel=1e-12)
    assert [x["kind"] for x in leg.legs] == ["walk", "ride", "walk"]
    assert leg.legs[1]["transport"] == "Boat"


def test_transport_not_used_when_walking_is_shorter():
    far = Transport("Tram", Point(0, 0.0, 0.0), Point(0, 100.0, 0.0), 10_000.0)
    a, b = Point(0, 0.0, 0.0), Point(0, 100.0, 0.0)
    leg = travel_time(Graph({}, {}, (far,)), a, b, params=TP, level=LEVEL, flights_known=frozenset())
    assert [x["kind"] for x in leg.legs] == ["walk"]
