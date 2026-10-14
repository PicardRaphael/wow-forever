"""CJ1, bloc 1f (décisions 277 et 279, registre I18) : base adaptée. Sur les niveaux couverts par le parcours gratuit de
la race et de la classe, la route reprend ses quêtes dans son ordre (rejouées par nos règles) et y ajoute ce que nos
routes font toujours par défaut : les quêtes de classe absentes du parcours et les donjons placés avec toutes leurs
quêtes prises avant le passage ; chaque ajout est placé là où la route est la plus courte et dit dans les écarts.

Valeurs : monde fabriqué (`tests/fixtures/route/route.json`), guides fabriqués (`tests/fixtures/rxp_guides`) ; règles
lues dans les données du dépôt. Aucun chiffre de jeu ici."""

from dataclasses import replace

from conftest import FIXTURES
from test_engine_route import CAP, make_world, start_state

from forever.compare import adapted_route, replay_rxp
from forever.rxp_guides import guide_chain, read_rxp_guides, who_for

GUIDES = FIXTURES / "rxp_guides"
END = 5
CLASS_QUEST = 106  # rendue quête de classe ici ; étape « << skip » du guide fabriqué : absente du parcours


def _setup(game_data):
    world, _ = make_world(game_data)
    world = replace(world, quests={**world.quests, CLASS_QUEST: replace(world.quests[CLASS_QUEST], class_quest=True)})
    who = who_for("Mage", "Orc", "Horde")
    chain = guide_chain(read_rxp_guides(GUIDES), who)
    return world, who, chain


def test_adapted_route_keeps_the_guide_and_adds_class_quests_and_dungeons(game_data):
    world, who, chain = _setup(game_data)
    replay = replay_rxp(game_data, world, chain.guides, who, start_state(), end_level=END, cap=CAP)
    adapted = adapted_route(game_data, world, chain.guides, who, start_state(), end_level=END, cap=CAP)
    turned = [s.ref for s in adapted.stops if s.kind == "turnin"]
    assert {s.ref for s in replay.stops if s.kind == "turnin"} <= set(turned)  # le parcours, gardé
    assert CLASS_QUEST in turned  # quête de classe ajoutée
    passes = [i for i, s in enumerate(adapted.stops) if s.kind == "dungeon"]
    assert len(passes) == 1
    before = {s.ref for s in adapted.stops[: passes[0]] if s.kind == "accept"}
    assert set(world.dungeons[adapted.stops[passes[0]].ref].quests) & set(world.quests) <= before
    assert adapted.result.feasible and adapted.result.reached  # farm du parcours (`.xp`) compris dans le rejeu
    kinds = {a["kind"] for a in adapted.additions}
    assert kinds == {"quête de classe", "donjon avec ses quêtes"}
    assert all("seconds" in a for a in adapted.additions)


def test_adapted_route_without_additions_is_the_replay(game_data):
    world, _ = make_world(game_data, dungeons=[])
    who = who_for("Mage", "Orc", "Horde")
    chain = guide_chain(read_rxp_guides(GUIDES), who)
    replay = replay_rxp(game_data, world, chain.guides, who, start_state(), end_level=END, cap=CAP)
    adapted = adapted_route(
        game_data, world, chain.guides, who, start_state(), end_level=END, cap=CAP, class_quests=False
    )
    assert [s for s in adapted.stops if s.kind != "grind"] == [s for s in replay.stops if s.kind != "grind"]
    assert adapted.additions == []
