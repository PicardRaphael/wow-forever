"""Départ d'une route (RX1c, relevé de la comparaison avec RestedXP) : le départ est le donneur d'une quête permise au
niveau de départ, au niveau le plus proche ; avant, la quête de plus bas niveau du livre (une quête neutre de l'autre
continent pour un Chasseur de la Horde au niveau 15) rendait toute la route infinie. Le Mage aux premiers niveaux, sans
rotation du moteur, garde l'estimation du temps par monstre au lieu d'échouer.

Valeurs : monde fabriqué de `tests/fixtures/route/route.json` ; données de la version du dépôt."""

import math

from conftest import FIXTURES
from test_engine_route import make_world

from forever.route import RouteRequest, route_context, start_quest

WOW = FIXTURES / "addons" / "dungeons"


def test_start_quest_is_allowed_and_nearest_to_the_start_level(game_data):
    world, _ = make_world(game_data)
    quests = list(world.quests.values())
    assert start_quest(quests, 1).level == min(q.level for q in quests if q.min_level <= 1)
    at3 = start_quest(quests, 3)
    allowed = [q for q in quests if q.min_level <= 3]
    assert at3.min_level <= 3 and abs(at3.level - 3) == min(abs(q.level - 3) for q in allowed)
    assert start_quest([], 3) is None


def test_mage_kill_time_at_level_1_falls_back_to_the_estimate(make_deps):
    deps = make_deps(wow_dir=WOW)
    ctx = route_context(deps, RouteRequest("mage", "horde", 1, 5, dungeons="none"), wow_dir=WOW)
    kill = ctx.kill(1)
    assert kill.source != "engine" and math.isfinite(kill.seconds) and kill.seconds > 0
