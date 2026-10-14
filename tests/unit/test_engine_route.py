"""Simulation d'une feuille de route (RX1, bloc C, registre I18, I17, I14) : `forever/engine/route.py`.

Fixture `tests/fixtures/route/route.json` (12 quêtes sur 2 zones, un donjon placé, valeurs inventées) ; règles d'XP,
bonus et paramètres (`route.travel`, `route.search`) lus dans les données de la version du dépôt. Aucun chiffre de
jeu ici."""

import math

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.engine.route import (
    RouteState,
    Stop,
    best_zone_xp_h,
    check_stop,
    simulate,
)
from forever.engine.travel import Graph, MapRect, map_to_world, travel_params, travel_time
from forever.engine.xp import Party, QuestXpInput, XpBonusState, mob_kill_xp, quest_xp
from forever.quests import QuestBook
from forever.route import RouteRequest, route_world

ROUTE = read_json(FIXTURES / "route" / "route.json")
VALUES = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
MAPS = {m["ui_map"]: MapRect(**m) for m in ROUTE["maps"]}
DUNGEON = ROUTE["dungeon"]["id"]
CAP = 60  # plafond passé au moteur dans ces tests (au-delà des niveaux de la fixture)


def _book():
    quests = {q["id"]: q for q in ROUTE["quests"]}
    names = {int(k): v for k, v in ROUTE["zone_names"].items()}
    return QuestBook(quests, [], "fixture", False, [], names)


def make_world(game_data, class_name="mage", *, bonuses=None, dungeons=None, **request):
    tp = travel_params(VALUES)
    graph = Graph({}, {})

    def travel(a, b, level):
        return travel_time(graph, a, b, params=tp, level=level, flights_known=frozenset()).seconds

    req = RouteRequest(class_name=class_name, faction="horde", start_level=1, end_level=5, **request)
    world, warnings = route_world(
        game_data,
        _book(),
        MAPS,
        request=req,
        values=VALUES,
        dungeons=[ROUTE["dungeon"]] if dungeons is None else dungeons,
        travel=travel,
        kill_seconds=lambda _level: ROUTE["kill_seconds"],
    )
    if bonuses is not None:
        from dataclasses import replace

        world = replace(world, bonuses=bonuses)
    return world, warnings


def start_state(level=1):
    s = ROUTE["start"]
    return RouteState(level=level, xp=0.0, position=map_to_world(MAPS[s["map"]], s["x"], s["y"]))


def run(game_data, world, stops, *, start=None, end_level=5, finish=True):
    return simulate(game_data, world, stops, start or start_state(), end_level=end_level, cap=CAP, finish=finish)


def test_world_keeps_only_routable_quests(game_data):
    world, warnings = make_world(game_data)
    assert 109 not in world.quests  # sans donneur : jamais placée
    assert 108 not in world.quests and any("108" in w for w in warnings)  # niveau minimal au-delà de la route
    assert world.quests[103].prereq_all == (102,) and world.quests[105].exclusive == (106,)
    assert world.quests[111].dungeon == DUNGEON and world.dungeons[DUNGEON].levels == (3, 3)


def test_world_params_come_from_mechanics(game_data):
    world, _ = make_world(game_data)
    raw = VALUES["route.search"]["value"]
    assert world.params.log_size == raw["log_size"]
    assert world.params.stop_overhead_s == raw["stop_overhead_s"]
    assert (world.params.tries, world.params.seed) == (raw["tries"], raw["seed"])


def test_min_level_checked(game_data):
    world, _ = make_world(game_data)
    state = start_state()
    assert check_stop(game_data, world, state, Stop("accept", 101)) is None
    assert check_stop(game_data, world, start_state(level=2), Stop("accept", 103)) is not None  # prérequis
    late = world.quests[110]
    assert check_stop(game_data, world, start_state(level=late.min_level - 1), Stop("accept", 110)) is not None
    assert check_stop(game_data, world, start_state(level=late.min_level), Stop("accept", 110)) is None


def test_prerequisite_and_chain_checked(game_data):
    world, _ = make_world(game_data)
    result = run(game_data, world, [Stop("accept", 103)], start=start_state(level=2))
    assert not result.feasible
    stops = [Stop("accept", 102), Stop("objective", 102), Stop("turnin", 102), Stop("accept", 103)]
    assert run(game_data, world, stops, start=start_state(level=2)).feasible


def test_exclusive_checked(game_data):
    world, _ = make_world(game_data)
    stops = [Stop("accept", 105), Stop("accept", 106)]
    assert not run(game_data, world, stops).feasible
    assert run(game_data, world, stops[:1]).feasible


def test_log_size_checked(game_data):
    from dataclasses import replace

    world, _ = make_world(game_data)
    small = replace(world, params=replace(world.params, log_size=1))
    assert not run(game_data, small, [Stop("accept", 101), Stop("accept", 102)]).feasible
    assert run(game_data, world, [Stop("accept", 101), Stop("accept", 102)]).feasible


def test_turnin_needs_objective_or_dungeon(game_data):
    world, _ = make_world(game_data)
    assert not run(game_data, world, [Stop("accept", 101), Stop("turnin", 101)]).feasible
    assert run(game_data, world, [Stop("accept", 101), Stop("objective", 101), Stop("turnin", 101)]).feasible
    assert run(game_data, world, [Stop("accept", 107), Stop("turnin", 107)]).feasible  # sans objectif
    at3 = start_state(level=3)
    assert not run(game_data, world, [Stop("accept", 111), Stop("turnin", 111)], start=at3).feasible
    stops = [Stop("accept", 111), Stop("dungeon", DUNGEON), Stop("turnin", 111)]
    assert run(game_data, world, stops, start=at3, end_level=6).feasible


def test_dungeon_only_in_its_window(game_data):
    world, _ = make_world(game_data)
    assert not run(game_data, world, [Stop("dungeon", DUNGEON)], start=start_state(level=2)).feasible
    assert run(game_data, world, [Stop("dungeon", DUNGEON)], start=start_state(level=3), end_level=6).feasible
    assert not run(game_data, world, [Stop("dungeon", DUNGEON)], start=start_state(level=4), end_level=6).feasible


def test_no_repeat_dungeon_without_reason(game_data):
    from dataclasses import replace

    world, _ = make_world(game_data)
    at3 = start_state(level=3)
    twice = [Stop("dungeon", DUNGEON), Stop("dungeon_repeat", DUNGEON)]
    better_zone = replace(world, best_zone_xp_h=lambda _level: math.inf)
    assert not run(game_data, better_zone, twice, start=at3, end_level=8).feasible
    no_zone = replace(world, best_zone_xp_h=lambda _level: None)
    assert run(game_data, no_zone, twice, start=at3, end_level=8).feasible
    assert not run(game_data, no_zone, [Stop("dungeon_repeat", DUNGEON)], start=at3, end_level=8).feasible


def _expected_xp(game_data, world, result, bonuses):
    total = 0.0
    for s in result.stops:
        if s.kind == "objective":
            q = world.quests[s.ref]
            expected = q.kills * mob_kill_xp(game_data, s.level, q.mob_level, bonuses=bonuses).xp
        elif s.kind == "turnin":
            q = world.quests[s.ref]
            inp = QuestXpInput(q.level, q.base_xp, q.xp_source, q.xp_certainty)
            expected = quest_xp(game_data, s.level, inp, bonuses=bonuses).xp
        elif s.kind == "dungeon":
            d = world.dungeons[s.ref]
            party = Party(tuple([s.level] * d.group))
            one = mob_kill_xp(game_data, s.level, d.mob_level, elite=True, dungeon=True, party=party, bonuses=bonuses)
            expected = d.kills * one.xp
        else:
            assert s.kind == "accept"
            expected = 0.0
        assert s.xp == pytest.approx(expected, rel=1e-12), s
        total += expected
    return total


def test_route_xp_uses_t04d_and_t04f(game_data):
    bonuses = XpBonusState(food=True)
    with_bonus, _ = make_world(game_data, bonuses=bonuses)
    without, _ = make_world(game_data)
    stops = [
        Stop("accept", 101),
        Stop("accept", 102),
        Stop("objective", 101),
        Stop("objective", 102),
        Stop("turnin", 101),
        Stop("turnin", 102),
        Stop("accept", 107),
        Stop("turnin", 107),
    ]
    a = run(game_data, with_bonus, stops, end_level=CAP, finish=False)
    b = run(game_data, without, stops, end_level=CAP, finish=False)
    assert a.feasible and b.feasible
    assert a.xp == pytest.approx(_expected_xp(game_data, with_bonus, a, bonuses), rel=1e-12)
    assert b.xp == pytest.approx(_expected_xp(game_data, without, b, None), rel=1e-12)
    assert a.xp > b.xp  # bonus de la nourriture (T04f) pris en compte


def test_dungeon_xp_uses_elite_dungeon_and_group(game_data):
    world, _ = make_world(game_data)
    result = run(game_data, world, [Stop("dungeon", DUNGEON)], start=start_state(level=3), end_level=CAP, finish=False)
    assert result.feasible
    assert result.xp == pytest.approx(_expected_xp(game_data, world, result, None), rel=1e-12)


def test_levels_follow_the_xp_curve(game_data):
    world, _ = make_world(game_data)
    result = run(game_data, world, [], end_level=3)
    assert result.reached and result.end_level == 3
    needed = sum(game_data.xp_to_next[level - 1] for level in (1, 2))
    assert result.xp == pytest.approx(needed, rel=1e-9)


def test_grind_finishes_the_route(game_data):
    world, _ = make_world(game_data)
    result = run(game_data, world, [], end_level=2)
    assert [s.kind for s in result.stops] == ["grind"]
    per_kill = mob_kill_xp(game_data, 1, 1).xp
    expected = game_data.xp_to_next[0] / per_kill * ROUTE["kill_seconds"]
    assert result.seconds == pytest.approx(expected, rel=1e-9)


def test_travel_counted_between_stops(game_data):
    world, _ = make_world(game_data)
    result = run(game_data, world, [Stop("accept", 110)], start=start_state(level=2), end_level=CAP, finish=False)
    stop = result.stops[0]
    q = world.quests[110]
    assert stop.travel_s == pytest.approx(world.travel(start_state().position, q.giver, 2), rel=1e-12)
    assert stop.seconds == pytest.approx(stop.travel_s + world.params.stop_overhead_s, rel=1e-12)


def test_route_certainty_is_the_weakest_term(game_data):
    world, _ = make_world(game_data)
    stops = [Stop("accept", 101), Stop("objective", 101), Stop("turnin", 101)]
    result = run(game_data, world, stops, end_level=CAP, finish=False)
    rank = {"suppose": 0, "probable": 1, "certain": 2}
    weakest = min((s.certainty for s in result.stops), key=rank.__getitem__)
    assert result.certainty == weakest
    for s in result.stops:
        assert rank[s.certainty] <= min((rank[t.certainty] for t in s.terms), default=2)


def test_best_zone_none_when_every_quest_is_gray(game_data):
    world, _ = make_world(game_data)
    quests = list(world.quests.values())
    assert best_zone_xp_h(game_data, quests, 2, kill_seconds=ROUTE["kill_seconds"], overhead_s=1.0) > 0
    assert best_zone_xp_h(game_data, quests, CAP, kill_seconds=ROUTE["kill_seconds"], overhead_s=1.0) is None


def test_missed_dungeon_window_is_infeasible(game_data):
    world, _ = make_world(game_data)
    at3 = start_state(level=3)
    assert any("manqué" in w for w in run(game_data, world, [], start=at3, end_level=5).warnings)  # par le farm
    assert run(game_data, world, [Stop("dungeon", DUNGEON)], start=at3, end_level=5).feasible
    no_dungeon, _ = make_world(game_data, dungeons=[])
    assert run(game_data, no_dungeon, [], start=at3, end_level=5).feasible
