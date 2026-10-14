"""Suites de la relecture de RX1 (blocs F à H) : bateau à escales lu comme un circuit, comparaison sans donjon et
état de la route rejouée exposé, réseau de marche qui ne fait pas marcher sur l'eau, visite de métier manquée.
Valeurs de fixture ou inventées pour le test."""

import math

from conftest import FIXTURES
from test_engine_route import CAP, run, start_state
from test_route_professions import NAME, _data
from test_route_professions import _world as prof_world

from forever.engine.route import RouteQuest, Stop
from forever.engine.travel import Graph, Point, ride_seconds, travel_params, travel_time
from forever.pipeline.travel_sources import Dock, JourneysNetwork, Ship
from forever.route import profession_visits
from forever.travel import transports_from_network

SPEEDS = {"Boat": 10.0}


def _network():
    docks = (
        Dock(0, 0.0, 0.0, None, "A", 30.0, 1000.0),
        Dock(0, 500.0, 0.0, None, "B", 20.0, 2000.0),
        Dock(1, 0.0, 0.0, None, "C", 10.0, 3000.0),
    )
    return JourneysNetwork((Ship("Boat", "A", docks),), (), SPEEDS, 4.0, 6.0, None)


def test_ship_with_stops_is_a_circuit():
    net = _network()
    legs = {(t.a, t.b): t.seconds for t in transports_from_network(net, "alliance")}
    docks = net.ships[0].docks
    expected = {}
    for i, d in enumerate(docks):
        nxt = docks[(i + 1) % len(docks)]
        expected[(Point(d.continent, d.x, d.y), Point(nxt.continent, nxt.x, nxt.y))] = ride_seconds(
            d.wait, d.length, 10.0, 4.0, 6.0
        )
    assert legs == expected  # A→B, B→C, C→A ; ni B→A ni C→B


def test_walk_unreachable_inside_a_network_stays_unreachable():
    from conftest import DATA_DIR, LOCAL_VERSION, read_json

    tp = travel_params(read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"])
    a, b = Point(0, 0.0, 0.0), Point(0, 100.0, 0.0)
    island = travel_time(
        Graph({}, {}), a, b, params=tp, level=1, flights_known=frozenset(), walk=lambda _p, _q: math.inf
    )
    assert math.isinf(island.seconds)  # île sans transport : pas de marche sur l'eau
    none = travel_time(Graph({}, {}), a, b, params=tp, level=1, flights_known=frozenset(), walk=lambda _p, _q: math.nan)
    assert none.seconds == math.dist((0, 0), (100, 0)) * tp.detour / tp.run_speed  # pas de réseau : ligne droite


def test_missed_profession_visit(game_data):
    from dataclasses import replace

    visits = profession_visits(_data(), {NAME: (60, 75)}, faction="horde", start_level=1, end_level=5)
    world = prof_world(game_data, visits)
    giver = start_state().position
    leap = RouteQuest(id=1, name="Fixture Leap", level=2, min_level=1, base_xp=1e6, xp_source="test",
                      xp_certainty="suppose", giver=giver, turn_in=giver, objective=None, kills=0.0, mob_level=2,
                      zone=9001)  # fmt: skip  # paramètre de test : saut de niveaux
    world = replace(world, quests={1: leap}, dungeons={}, trainers=())
    stops = [Stop("accept", 1), Stop("turnin", 1)]
    missed = run(game_data, world, stops, end_level=CAP, finish=False)
    assert not missed.feasible and any(NAME in w and "manquée" in w for w in missed.warnings)
    assert run(game_data, world, [Stop("prof", NAME), *stops], end_level=CAP, finish=False).feasible


def test_compare_route_without_dungeons_exposes_state(tmp_path, monkeypatch):
    import json

    from forever.cli import main

    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(FIXTURES / "addons" / "dungeons"))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    import contextlib
    import io

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["route", "compare", str(FIXTURES / "route" / "fixture.fgguide"), "--json"]) == 0
    doc = json.loads(out.getvalue())
    for side in ("ours", "theirs"):
        assert {"feasible", "reached", "warnings"} <= set(doc[side])
        assert doc[side]["reached"] is True
