"""CJ1 (décision 277, précision de l'utilisateur du 2026-10-14, registre I17, I18) : toutes les quêtes d'un donjon sont
prises avant son premier passage, même au prix d'un aller-retour ; une quête qui ouvre une quête de donjon (prérequis
de sa chaîne) est toujours prise, quel que soit le trajet.

Valeurs : monde fabriqué (`tests/fixtures/route/route.json`) ; règles d'XP lues dans les données du dépôt."""

from dataclasses import replace

from test_engine_route import make_world, start_state

from forever.optimize.route import _worth_it

FAR = 1e9  # trajet démesuré : seule la règle du donjon peut faire prendre la quête


def test_prerequisite_of_a_dungeon_quest_is_always_worth_it(game_data):
    world, _ = make_world(game_data)
    dungeon_quest = world.quests[111]
    assert dungeon_quest.dungeon is not None
    world = replace(world, quests={**world.quests, 111: replace(dungeon_quest, prereq_all=(110,))})
    state = start_state(level=3)
    assert _worth_it(game_data, world, state, 110, FAR)
    assert _worth_it(game_data, world, state, 111, FAR)
    assert not _worth_it(game_data, world, state, 106, FAR)  # quête ordinaire, trajet démesuré
