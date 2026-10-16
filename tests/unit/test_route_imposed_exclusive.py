"""Bloc 4d (2026-10-16) : une quête imposée (route d'équipement) écarte ses quêtes exclusives. Constat : Mage-tastic
Gizmonitor, imposée pour ses récompenses, n'entrait jamais dans la route : l'optimiseur prenait d'abord la quête qui
l'exclut. Une quête exclusive d'une quête imposée est retirée du monde de la route, dite dans les avertissements.

Valeurs : monde fabriqué (`tests/fixtures/route/route.json`, quêtes 105 et 106 exclusives). Aucun chiffre de jeu ici."""

from test_engine_route import make_world


def test_imposed_quest_removes_its_exclusive_quests(game_data):
    world, warnings = make_world(game_data, include=(106,))
    assert 106 in world.quests and 105 not in world.quests
    assert any("105" in w and "exclusive" in w for w in warnings)


def test_without_imposed_quest_both_stay(game_data):
    world, _ = make_world(game_data)
    assert 105 in world.quests and 106 in world.quests


def test_imposed_quest_is_done_even_past_the_end_level(game_data):
    """Une quête imposée se fait même si le niveau final est déjà atteint : construction et déroulé continuent
    jusqu'à son rendu, seulement vers ses étapes (Mage-tastic Gizmonitor, prise au niveau final de la route)."""
    from test_engine_route import CAP, start_state

    from forever.engine.route import Stop, simulate
    from forever.optimize.route import construct

    world, _ = make_world(game_data, include=(101,))
    at_end = start_state(level=5)  # niveau final de `make_world`
    stops = construct(game_data, world, at_end, end_level=5, cap=CAP)
    assert Stop("turnin", 101) in stops
    assert {s.ref for s in stops} == {101}  # rien d'autre après le niveau final
    result = simulate(game_data, world, stops, at_end, end_level=5, cap=CAP)
    assert result.feasible and any((r.kind, r.ref) == ("turnin", 101) for r in result.stops)
