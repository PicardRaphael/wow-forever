"""CJ1, bloc 1b (décision 277, règle de l'utilisateur, registre I18) : pas de farm quand des quêtes restent. Même
quand le farm paraît plus rentable (temps par monstre très court), notre route prend toutes les quêtes encore
faisables avant de farmer, et l'amélioration locale ne les retire pas pour farmer à leur place.

Constat du 2026-10-14 : un Tauren Guerrier 1 à 10 rendait deux quêtes puis farmait jusqu'au niveau 10.

Valeurs : monde fabriqué (`tests/fixtures/route/route.json`) ; règles d'XP lues dans les données du dépôt."""

from dataclasses import replace

from test_engine_route import CAP, make_world, start_state

from forever.engine.route import Stop, apply_stop, check_stop
from forever.engine.xp import gray_level
from forever.optimize.route import plan

END = 5


def _quick_grind(world):
    return replace(world, kill_seconds=lambda _level: 0.5)  # farm artificiellement très rentable


def _left(game_data, world, stops):
    """Quêtes encore faisables (non grises) au moment du farm final."""
    state = start_state()
    for s in stops:
        state, _ = apply_stop(game_data, world, state, s, cap=CAP)
    gray = gray_level(game_data, state.level)
    return [
        q.id
        for q in world.quests.values()
        if q.level > gray and q.dungeon is None and check_stop(game_data, world, state, Stop("accept", q.id)) is None
    ]


def test_no_farm_while_quests_remain(game_data):
    world, _ = make_world(game_data, dungeons=[])
    world = _quick_grind(world)
    found = plan(game_data, world, start_state(), end_level=END, cap=CAP)
    kinds = [r.kind for r in found.result.stops]
    if "grind" in kinds:
        assert _left(game_data, world, found.stops) == []
    taken = {s.ref for s in found.stops if s.kind == "turnin"}
    assert len(taken) >= 3  # la route fait des quêtes au lieu de farmer dès le début


def test_improvement_keeps_the_quests_of_the_construction(game_data):
    world, _ = make_world(game_data, dungeons=[])
    world = _quick_grind(world)
    built = plan(game_data, world, start_state(), end_level=END, cap=CAP, tries=0)
    improved = plan(game_data, world, start_state(), end_level=END, cap=CAP)
    assert {s.ref for s in built.stops if s.kind == "turnin"} <= {s.ref for s in improved.stops if s.kind == "turnin"}
