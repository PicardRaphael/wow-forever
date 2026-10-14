"""Recherche d'une feuille de route (RX1, bloc C, registre I18, I17) : construction, amélioration locale, assemblage
et commande `forever route plan|show`.

Moteur et optimiseur : fixture `tests/fixtures/route/route.json` (voir `test_engine_route.py`). Commande : addons
synthétiques de `tests/fixtures/addons/dungeons/` et données de la version du dépôt. Aucun chiffre de jeu ici."""

import json

import pytest
from conftest import FIXTURES
from test_engine_route import CAP, DUNGEON, ROUTE, make_world, run, start_state

from forever.cli import main
from forever.optimize.route import construct, plan
from forever.provenance import validate_provenance

END = 5
WOW = FIXTURES / "addons" / "dungeons"


@pytest.fixture(scope="module")
def planned(game_data):
    world, _ = make_world(game_data)
    return world, plan(game_data, world, start_state(), end_level=END, cap=CAP)


def _accepts(stops):
    return [s.ref for s in stops if s.kind == "accept"]


def test_route_reaches_the_end_level(planned):
    _, p = planned
    assert p.result.feasible and p.result.reached and p.result.end_level == END


def _check_prerequisites(world, stops):
    turned = []
    for s in stops:
        if s.kind == "accept":
            q = world.quests[s.ref]
            assert set(q.prereq_all) <= set(turned), s
            assert not q.prereq_any or set(q.prereq_any) & set(turned), s
            assert not q.after or set(q.after) & set(turned), s
        if s.kind == "turnin":
            turned.append(s.ref)


def test_prerequisites_respected(game_data, planned):
    world, p = planned
    built = construct(game_data, world, start_state(), end_level=END, cap=CAP)
    _check_prerequisites(world, p.stops)
    _check_prerequisites(world, built)
    assert 103 in _accepts(built)  # la chaîne de la fixture est suivie (test non vide)


def test_exclusive_once(game_data, planned):
    world, p = planned
    built = construct(game_data, world, start_state(), end_level=END, cap=CAP)
    assert len({105, 106} & set(_accepts(p.stops))) <= 1
    assert len({105, 106} & set(_accepts(built))) == 1


def test_min_level_respected(planned):
    world, p = planned
    for s in p.result.stops:
        if s.kind == "accept":
            assert s.level >= world.quests[s.ref].min_level, s
    assert 108 not in _accepts(p.stops)  # niveau minimal au-delà de la route


def test_unroutable_quest_never_placed(planned):
    _, p = planned
    assert 109 not in {s.ref for s in p.stops}  # sans donneur


def test_dungeon_at_first_pass_with_quests(planned):
    world, p = planned
    passes = [i for i, s in enumerate(p.result.stops) if s.kind in ("dungeon", "dungeon_repeat")]
    assert len(passes) == 1
    at = p.result.stops[passes[0]]
    assert (at.kind, at.ref, at.level) == ("dungeon", DUNGEON, ROUTE["dungeon"]["placement"]["level"])
    before = {s.ref for s in p.result.stops[: passes[0]] if s.kind == "accept"}
    assert set(world.dungeons[DUNGEON].quests) <= before


def test_no_repeat_dungeon_without_reason(game_data):
    from dataclasses import replace

    world, _ = make_world(game_data)
    # paramètres de test : aucune zone à battre, farm et objectifs hors de prix : un passage suivant vaut
    repeat = replace(world, best_zone_xp_h=lambda _level: None, kill_seconds=lambda _level: 1e6)
    zone = plan(game_data, world, start_state(), end_level=END, cap=CAP)
    free = plan(game_data, repeat, start_state(), end_level=END + 2, cap=CAP)
    assert [s.kind for s in zone.stops].count("dungeon_repeat") == 0
    assert [s.kind for s in free.stops].count("dungeon_repeat") >= 1


def test_class_quest_only_for_class(game_data):
    mage, _ = make_world(game_data, "mage")
    warrior, _ = make_world(game_data, "warrior")
    assert 107 in mage.quests and 107 not in warrior.quests
    assert 107 in _accepts(plan(game_data, mage, start_state(), end_level=END, cap=CAP).stops)
    assert 107 not in _accepts(plan(game_data, warrior, start_state(), end_level=END, cap=CAP).stops)


def test_class_quests_can_be_left_out(game_data):
    world, _ = make_world(game_data, "mage", class_quests=False)
    assert 107 not in world.quests


def test_exclude_and_include(game_data):
    world, _ = make_world(game_data, exclude=(110,))
    assert 110 not in world.quests
    p = plan(game_data, world, start_state(), end_level=END, cap=CAP)
    assert 110 not in {s.ref for s in p.stops}


def test_dungeons_none_drops_dungeon_and_its_quests(game_data):
    world, warnings = make_world(game_data, dungeons=[])
    assert not world.dungeons and 111 not in world.quests and 112 not in world.quests
    assert any("111" in w for w in warnings)  # quête de donjon écartée, dite
    p = plan(game_data, world, start_state(), end_level=END, cap=CAP)
    assert all(s.kind not in ("dungeon", "dungeon_repeat") for s in p.stops) and p.result.reached


def test_route_deterministic(game_data):
    world, _ = make_world(game_data)
    a = plan(game_data, world, start_state(), end_level=END, cap=CAP, seed=7)
    b = plan(game_data, world, start_state(), end_level=END, cap=CAP, seed=7)
    assert a.stops == b.stops and a.result.seconds == b.result.seconds


def test_improvement_never_worse(game_data, planned):
    world, p = planned
    built = construct(game_data, world, start_state(), end_level=END, cap=CAP)
    cost = run(game_data, world, built, end_level=END).seconds
    assert p.construct_seconds == pytest.approx(cost, rel=1e-12)
    assert p.result.seconds <= cost
    assert p.tries == world.params.tries


@pytest.fixture(scope="module")
def cli_plan(tmp_path_factory):
    """Plan de la commande (une seule fois pour le module)."""
    tmp = tmp_path_factory.mktemp("route_cli")
    mp = pytest.MonkeyPatch()
    mp.setenv("FOREVER_CACHE_DIR", str(tmp / "cache"))
    mp.setenv("FOREVER_WOW_DIR", str(WOW))
    mp.setenv("FOREVER_OFFLINE", "1")
    import contextlib
    import io

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["route", "plan", "--class", "hunter", "--faction", "horde", "--from", "1", "--to", "3", "--json"])
    mp.undo()
    return code, json.loads(out.getvalue()), tmp


def test_route_cli_plan_json(cli_plan):
    code, doc, tmp = cli_plan
    assert code == 0
    assert doc["levels"]["from"] == 1 and doc["levels"]["to"] == 3 and doc["levels"]["reached"] == 3
    assert doc["stops"] and doc["seconds"] > 0 and doc["xp_h"] > 0
    assert {"kind", "ref", "level", "xp", "seconds", "certainty"} <= set(doc["stops"][0])
    assert (tmp / "cache" / "routes" / f"{doc['id']}.json").is_file()


def test_route_provenance(cli_plan):
    _, doc, _ = cli_plan
    assert validate_provenance(doc["provenance"]) == []
    rank = {"suppose": 0, "probable": 1, "certain": 2}
    weakest = min((s["certainty"] for s in doc["stops"]), key=rank.__getitem__)
    assert doc["certainty"] == doc["provenance"]["certainty"] == weakest


def test_route_plan_places_bonus_reminders(cli_plan, game_data):
    from forever.engine.xp import XpBonusState
    from forever.route import bonus_reminders

    _, doc, _ = cli_plan
    expected = bonus_reminders(game_data, XpBonusState(), hours=doc["seconds"] / 3600, level=1)
    assert [r["text"] for r in doc["reminders"]] == [r.text for r in expected]


def test_route_cli_show(cli_plan, monkeypatch, capsys):
    _, doc, tmp = cli_plan
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp / "cache"))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    assert main(["route", "show", doc["id"], "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["id"] == doc["id"] and shown["stops"] == doc["stops"]
    assert main(["route", "show", doc["id"]]) == 0
    assert "niveau" in capsys.readouterr().out
