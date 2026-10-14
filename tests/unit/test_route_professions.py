"""Maîtres de métier sur la route (RX1, bloc H, registre I18) : métiers de Naowh Forever Professions lus en local
(maîtres, rangs), visite placée quand le rang suivant est ouvert par la compétence actuelle et que son niveau requis
tombe dans la route, visite manquée refusée, commande `--profession`. Fixtures synthétiques
`tests/fixtures/addons/journeys/` et `tests/fixtures/route/route.json`."""

import json

from conftest import FIXTURES
from test_engine_route import CAP, MAPS, ROUTE, VALUES, _book, run, start_state

from forever.cli import main
from forever.engine.route import Stop
from forever.engine.travel import map_to_world
from forever.optimize.route import plan
from forever.pipeline.travel_sources import read_profession_data
from forever.route import RouteRequest, profession_visits, route_world

ADDONS = FIXTURES / "addons" / "journeys" / "Interface" / "AddOns"
NAME = "Fixturecraft"


def _data():
    return read_profession_data(ADDONS)


def test_profession_data_read():
    data = _data()
    assert set(data) == {NAME}
    craft = data[NAME]
    assert craft.skill_line == 9171
    assert [(r.cap, r.skill, r.level) for r in craft.ranks] == [(150, 50, None), (225, 125, None), (300, 200, 4)]
    assert [(t.npc, t.sides, t.ui_map) for t in craft.trainers] == [(990101, "H", 9001), (990102, "A", 9002),
                                                                     (990103, "-", 9002)]  # fmt: skip
    assert read_profession_data(FIXTURES / "addons" / "dungeons" / "Interface" / "AddOns") == {}


def test_visit_only_when_the_next_rank_is_open():
    open_now = profession_visits(_data(), {NAME: (60, 75)}, faction="horde", start_level=1, end_level=5)
    assert list(open_now) == [NAME]
    level, trainers = open_now[NAME]
    assert level == 1 and [t.npc for t in trainers] == [990101]  # maître du camp seulement
    assert profession_visits(_data(), {NAME: (30, 75)}, faction="horde", start_level=1, end_level=5) == {}  # compétence
    expert = profession_visits(_data(), {NAME: (150, 150)}, faction="horde", start_level=1, end_level=5)
    assert expert[NAME][0] == 1  # compagnon au maximum : le rang expert est ouvert
    artisan = profession_visits(_data(), {NAME: (210, 225)}, faction="horde", start_level=1, end_level=5)
    assert artisan[NAME][0] == 4  # niveau requis du rang
    assert profession_visits(_data(), {NAME: (210, 225)}, faction="horde", start_level=1, end_level=3) == {}
    assert profession_visits(_data(), {"Inconnu": (60, 75)}, faction="horde", start_level=1, end_level=5) == {}


def _world(game_data, visits):
    from forever.engine.travel import Graph, travel_params, travel_time

    tp = travel_params(VALUES)

    def travel(a, b, level):
        return travel_time(Graph({}, {}), a, b, params=tp, level=level, flights_known=frozenset()).seconds

    request = RouteRequest(class_name="mage", faction="horde", start_level=1, end_level=5)
    world, _ = route_world(game_data, _book(), MAPS, request=request, values=VALUES, dungeons=[ROUTE["dungeon"]],
                           travel=travel, kill_seconds=lambda _level: ROUTE["kill_seconds"],
                           prof_visits=visits)  # fmt: skip
    return world


def test_profession_stop(game_data):
    visits = profession_visits(_data(), {NAME: (210, 225)}, faction="horde", start_level=1, end_level=5)
    world = _world(game_data, visits)
    assert world.prof_visits[NAME] == (4, (map_to_world(MAPS[9001], 42.0, 42.0),))
    assert not run(game_data, world, [Stop("prof", NAME)], start=start_state(level=3), end_level=CAP,
                   finish=False).feasible  # fmt: skip
    done = run(game_data, world, [Stop("prof", NAME)], start=start_state(level=4), end_level=CAP, finish=False)
    assert done.feasible
    stop = done.stops[0]
    assert stop.seconds == stop.travel_s + world.params.train_time_s


def test_plan_visits_the_profession_trainer(game_data):
    visits = profession_visits(_data(), {NAME: (60, 75)}, faction="horde", start_level=1, end_level=5)
    world = _world(game_data, visits)
    p = plan(game_data, world, start_state(), end_level=5, cap=CAP)
    assert p.result.feasible and not any("manqué" in w for w in p.result.warnings)
    assert [s.ref for s in p.result.stops if s.kind == "prof"] == [NAME]


def test_route_plan_with_profession(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(FIXTURES / "addons" / "dungeons"))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    argv = ["route", "plan", "--class", "hunter", "--faction", "horde", "--from", "1", "--to", "3", "--json"]
    assert main([*argv, "--profession", "Alchemy:60:75"]) == 0  # Naowh Professions absent de la fixture : rien
    doc = json.loads(capsys.readouterr().out)
    assert not [s for s in doc["stops"] if s["kind"] == "prof"]
    assert doc["request"]["professions"] == [["Alchemy", 60, 75]]
    assert main([*argv, "--profession", "Alchemy:x:75"]) != 0  # forme invalide
