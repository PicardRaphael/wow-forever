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
