"""CJ1, bloc 1b (décisions 277 et 278, registre I18) : zone de départ d'abord. Sous le seuil des bas niveaux
(`route.filters.low_level`), notre route ne prend une quête que dans la zone de départ ou dans une zone que le parcours
de référence de la race visite à ces niveaux ; une quête de classe ou de donjon reste permise. Le rejeu d'un guide
(RestedXP, Factoruide) n'est pas contraint.

Constat du 2026-10-14 : un Gnome Guerrier 1 à 10 partait vers Elwynn Forest ; RestedXP et Polestar restent dans la
zone de la race jusqu'au niveau 10.

Valeurs : monde fabriqué (`tests/fixtures/route/route.json`), guides fabriqués (`tests/fixtures/rxp_guides`), réglages
lus dans les données de la version du dépôt. Aucun chiffre de jeu ici."""

from dataclasses import replace

from conftest import FIXTURES
from test_engine_route import CAP, MAPS, make_world, start_state

from forever.compare import replay_rxp
from forever.engine.route import RouteState, Stop, check_stop
from forever.route import reference_zones
from forever.rxp_guides import guide_chain, read_rxp_guides, who_for

GUIDES = FIXTURES / "rxp_guides"
VALE, HILLS = 9001, 9002  # cartes fabriquées de la fixture


def _early(world, zones, level):
    return replace(world, early_zones=frozenset(zones), early_level=level)


def test_quest_outside_the_start_zones_waits_for_the_low_level_threshold(game_data):
    world, _ = make_world(game_data)
    world = _early(world, {VALE}, 4)
    assert world.quests[110].zone == HILLS
    low = RouteState(level=2, xp=0.0, position=world.quests[110].giver)
    assert check_stop(game_data, world, low, Stop("accept", 110)) is not None
    assert check_stop(game_data, world, low, Stop("accept", 101)) is None  # zone de départ
    high = RouteState(level=4, xp=0.0, position=world.quests[110].giver)
    assert check_stop(game_data, world, high, Stop("accept", 110)) is None


def test_class_and_dungeon_quests_stay_allowed(game_data):
    world, _ = make_world(game_data)
    assert world.quests[107].class_quest and not world.quests[101].class_quest
    hills = {q: replace(world.quests[q], zone=HILLS) for q in (107,)}
    world = _early(replace(world, quests={**world.quests, **hills}), {VALE}, 4)
    state = RouteState(level=3, xp=0.0, position=world.quests[107].giver)
    assert check_stop(game_data, world, state, Stop("accept", 107)) is None  # quête de classe
    assert world.quests[111].dungeon is not None and world.quests[111].zone == HILLS
    assert check_stop(game_data, world, state, Stop("accept", 111)) is None  # quête de donjon


def test_no_constraint_without_start_zones(game_data):
    world, _ = make_world(game_data)
    assert world.early_zones is None
    state = RouteState(level=2, xp=0.0, position=world.quests[110].giver)
    assert check_stop(game_data, world, state, Stop("accept", 110)) is None


def test_reference_zones_are_the_zones_of_the_race_guide_below_the_threshold(game_data):
    world, _ = make_world(game_data)
    quests = {**world.quests, 103: replace(world.quests[103], zone=HILLS)}  # prise du guide « 3-5 » (Orc)
    library = read_rxp_guides(GUIDES)
    orc_mage = who_for("Mage", "Orc", "Horde")
    assert reference_zones(library, orc_mage, quests, below=3) == frozenset({VALE})
    assert reference_zones(library, orc_mage, quests, below=10) == frozenset({VALE, HILLS})
    troll = who_for("Mage", "Troll", "Horde")  # 103 réservée à l'Orc dans le guide
    assert reference_zones(library, troll, quests, below=10) == frozenset({VALE})
    assert reference_zones(library, who_for("Mage", "Gnome", "Alliance"), world.quests, below=10) == frozenset()


def test_guide_replays_are_not_constrained(game_data):
    world, _ = make_world(game_data)
    world = _early(world, {VALE}, 60)
    library = read_rxp_guides(GUIDES)
    who = who_for("Mage", "Orc", "Horde")
    chain = guide_chain(library, who)
    replay = replay_rxp(game_data, world, chain.guides, who, start_state(), end_level=5, cap=CAP)
    assert not any("zone de départ" in s["reason"] for s in replay.skipped)
    assert MAPS  # cartes de la fixture chargées
