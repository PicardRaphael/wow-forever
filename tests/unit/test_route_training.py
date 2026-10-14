"""Visites au maître de classe dans une feuille de route (RX1, bloc F, registre I18) : niveaux où la classe apprend
des sorts (Naowh Training, lu en local), maîtres de classe et positions (Questie), arrêt `train` dans la route,
visite au plus tard `train_max_delay` niveaux après (sinon route refusée), trajets d'entraînement comptés dans le
farm final. Fixtures synthétiques `tests/fixtures/addons/journeys/` et `tests/fixtures/route/route.json`."""

from dataclasses import replace

import pytest
from conftest import FIXTURES
from test_engine_route import CAP, MAPS, ROUTE, VALUES, _book, make_world, run, start_state

from forever.engine.route import RouteQuest, Stop
from forever.engine.travel import map_to_world
from forever.optimize.route import plan
from forever.pipeline.travel_sources import TrainerNpc, read_questie_trainers, read_training_levels

ADDONS = FIXTURES / "addons" / "journeys" / "Interface" / "AddOns"
TRAINER = TrainerNpc(990001, "Fixture Arcanist", "Mage Trainer", "H", 9001, 41.0, 41.0)  # zone A de route.json


def test_training_levels_read():
    assert read_training_levels(ADDONS) == {1: (1, 6), 8: (1, 2, 4, 6)}  # sort de quête exclu
    assert read_training_levels(FIXTURES / "addons" / "dungeons" / "Interface" / "AddOns") == {}


def test_trainers_read_from_questie():
    trainers = read_questie_trainers(ADDONS, "Mage Trainer")
    assert [(t.npc, t.sides, t.ui_map, t.x, t.y) for t in trainers] == [
        (990001, "H", 9001, 40.0, 40.0),
        (990001, "H", 9001, 41.0, 41.0),
        (990002, "A", 9002, 60.0, 60.0),
    ]
    assert [t.npc for t in read_questie_trainers(ADDONS, "Warrior Trainer")] == [990003]


def _world(game_data, trainers=(TRAINER,), train_levels=(1, 2, 4, 6), dungeons=None):
    """Monde de `make_world` (fixture route.json), avec maîtres de classe et niveaux d'entraînement."""
    from forever.engine.travel import Graph, travel_params, travel_time
    from forever.route import RouteRequest, route_world

    tp = travel_params(VALUES)

    def travel(a, b, level):
        return travel_time(Graph({}, {}), a, b, params=tp, level=level, flights_known=frozenset()).seconds

    request = RouteRequest(class_name="mage", faction="horde", start_level=1, end_level=5)
    return route_world(
        game_data,
        _book(),
        MAPS,
        request=request,
        values=VALUES,
        dungeons=[ROUTE["dungeon"]] if dungeons is None else dungeons,
        travel=travel,
        kill_seconds=lambda _level: ROUTE["kill_seconds"],
        trainers=list(trainers),
        train_levels=train_levels,
    )


def test_world_keeps_trainers_of_the_faction_and_levels_of_the_route(game_data):
    world, _ = _world(game_data)
    assert world.trainers == (map_to_world(MAPS[9001], 41.0, 41.0),)
    assert world.train_levels == (2, 4)  # au-dessus du départ, sous l'arrivée (route de 1 à 5)
    alliance = TrainerNpc(990002, "Fixture Sage", "Mage Trainer", "A", 9002, 60.0, 60.0)
    other, _ = _world(game_data, trainers=[alliance], train_levels=(2, 4))
    assert other.trainers == ()  # maître de l'autre camp


def test_params_come_from_mechanics(game_data):
    world, _ = _world(game_data)
    raw = VALUES["route.search"]["value"]
    assert (world.params.train_time_s, world.params.train_max_delay) == (raw["train_time_s"], raw["train_max_delay"])


def test_train_stop(game_data):
    world, _ = _world(game_data)
    assert not run(
        game_data, world, [Stop("train", 2)], start=start_state(level=1), end_level=CAP, finish=False
    ).feasible
    result = run(game_data, world, [Stop("train", 2)], start=start_state(level=2), end_level=CAP, finish=False)
    assert result.feasible
    stop = result.stops[0]
    trainer = world.trainers[0]
    assert stop.travel_s == pytest.approx(world.travel(start_state().position, trainer, 2), rel=1e-12)
    assert stop.seconds == pytest.approx(stop.travel_s + world.params.train_time_s, rel=1e-12)
    again = run(game_data, world, [Stop("train", 2), Stop("train", 2)], start=start_state(level=2), end_level=CAP,
                finish=False)  # fmt: skip
    assert not again.feasible  # déjà entraîné


def _big_quest(world):
    """Quête de test qui fait gagner plusieurs niveaux d'un coup (paramètre de test, signalé comme tel)."""
    giver = start_state().position
    big = RouteQuest(id=1, name="Fixture Leap", level=2, min_level=1, base_xp=1e6, xp_source="test",
                     xp_certainty="suppose", giver=giver, turn_in=giver, objective=None, kills=0.0, mob_level=2,
                     zone=9001)  # fmt: skip
    return replace(world, quests={1: big}, dungeons={})


def test_missed_training_is_infeasible(game_data):
    world = _big_quest(_world(game_data)[0])
    leap = [Stop("accept", 1), Stop("turnin", 1)]
    missed = run(game_data, world, leap, start=start_state(level=2), end_level=CAP, finish=False)
    assert not missed.feasible and any("manqué" in w for w in missed.warnings)
    trained = run(game_data, world, [Stop("train", 2), *leap], start=start_state(level=2), end_level=CAP,
                  finish=False)  # fmt: skip
    assert trained.feasible


def test_grind_counts_training_trips(game_data):
    world, _ = _world(game_data, dungeons=[])
    plain, _ = make_world(game_data, dungeons=[])
    with_trips = run(game_data, world, [], end_level=5)
    without = run(game_data, plain, [], end_level=5)
    trip = 2 * world.travel(start_state().position, world.trainers[0], 2) + world.params.train_time_s
    assert with_trips.seconds == pytest.approx(without.seconds + 2 * trip, rel=1e-9)  # niveaux 2 et 4
    assert with_trips.feasible and not with_trips.warnings


def test_plan_trains_in_time(game_data):
    world, _ = _world(game_data)
    p = plan(game_data, world, start_state(), end_level=5, cap=CAP)
    assert p.result.feasible and not any("manqué" in w for w in p.result.warnings)
    trains = [s for s in p.result.stops if s.kind == "train"]
    assert trains and all(s.level >= 2 for s in trains)
