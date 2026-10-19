"""RTE8 (bloc 4d, demande de l'utilisateur du 2026-10-19) : un point d'une capitale que le réseau de marche de Journeys
ne relie pas (Bink, Ironforge : le nœud le plus proche sur la carte est une poche d'un autre étage) n'est plus
injoignable. En repli, le trajet passe par le nœud le plus proche du point parmi ceux qu'atteint l'autre bout, puis la
ligne droite allongée du détour jusqu'au point, marquée `suppose` (avertissement de la route). Hors des capitales
(île), le réseau garde l'infini : un transport reste nécessaire.

Capitales : liste des cartes de zone lue dans les données (`mechanics.json`, `route.cities`). Réseaux, points et
détour fabriqués ici ; aucun chiffre de jeu."""

import math

import pytest
from conftest import DATA_DIR, read_json

from forever.engine.travel import MapRect, Point, WalkNet, walk_yards
from forever.manifest import load_manifest
from forever.travel import WalkCache, city_line_warning, city_maps

DETOUR = 1.5  # détour fabriqué (la vraie valeur vit dans route.travel)


def net():
    """Réseau principal 0-1-2 le long de l'axe x ; poche 3-4 (autre étage) juste à côté du nœud 2, sans lien."""
    points = [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (205.0, 0.0), (205.0, 40.0)]
    edges = [(0, 1, 100.0), (1, 2, 100.0), (3, 4, 40.0)]
    adj: list[list[tuple[int, float]]] = [[] for _ in points]
    for a, b, w in edges:
        adj[a].append((b, w))
        adj[b].append((a, w))
    return WalkNet(0, points, adj)


OUTSIDE = Point(0, 0.0, -10.0)  # près du nœud 0
INSIDE = Point(0, 206.0, 30.0)  # au plus près de la poche (nœud 4), dans la ville


def test_unlinked_point_outside_a_city_stays_unreachable():
    assert walk_yards(net(), OUTSIDE, INSIDE, detour=DETOUR) == math.inf


def test_unlinked_city_point_takes_the_straight_line_from_the_nearest_reached_node():
    expected = 10.0 + 200.0 + math.dist((200.0, 0.0), (206.0, 30.0)) * DETOUR  # nœud 0, réseau, ligne allongée
    found = walk_yards(net(), OUTSIDE, INSIDE, detour=DETOUR, in_city=(False, True))
    assert found == pytest.approx(expected, rel=1e-12)
    back = walk_yards(net(), INSIDE, OUTSIDE, detour=DETOUR, in_city=(True, False))
    assert back == pytest.approx(expected, rel=1e-12)  # même trajet dans l'autre sens


def test_linked_city_point_keeps_the_network():
    near_main = Point(0, 150.0, 5.0)  # au plus près du nœud 1 ou 2, relié
    plain = walk_yards(net(), OUTSIDE, near_main, detour=DETOUR)
    assert walk_yards(net(), OUTSIDE, near_main, detour=DETOUR, in_city=(False, True)) == plain


def test_walk_cache_uses_the_city_predicate_and_records_the_fallback():
    city = lambda p: p.x > 150.0
    walker = WalkCache({0: net()}, DETOUR, city=city)
    assert math.isfinite(walker(OUTSIDE, INSIDE))
    assert walker.city_lines == {INSIDE}
    island = WalkCache({0: net()}, DETOUR)
    assert island(OUTSIDE, INSIDE) == math.inf and island.city_lines == set()


def test_warning_names_the_cities_reached_by_a_straight_line():
    walker = WalkCache({0: net()}, DETOUR, city=lambda p: p.x > 150.0)
    walker(OUTSIDE, INSIDE)
    maps = {9001: MapRect(9001, 0, 150.0, -100.0, 300.0, 100.0)}
    text = city_line_warning(walker, maps, {9001: "Fixture City"})
    assert text is not None and "Fixture City" in text and "ligne droite" in text and "suppose" in text
    assert city_line_warning(WalkCache({0: net()}, DETOUR), maps, {9001: "Fixture City"}) is None


def test_the_capitals_of_both_factions_are_in_the_data():
    version = load_manifest(DATA_DIR)["game_version"]
    values = read_json(DATA_DIR / version / "mechanics.json")["values"]
    cities = city_maps(values)
    maps = {m["ui_map"] for m in read_json(DATA_DIR / version / "travel.json")["maps"]}
    assert len(cities) == 6 and cities <= maps  # trois capitales par camp, toutes cartes du client
