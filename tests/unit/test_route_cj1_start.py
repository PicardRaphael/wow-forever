"""CJ1, bloc 1 (décision 277, registre I18) : une route part de la position réelle du personnage et de la zone de
départ de sa race, retire ses quêtes déjà faites et écarte les quêtes d'une autre race, d'événement, d'effort de
guerre, répétables, de métier ou trop hautes.

Constat du 2026-10-14 : un Gnome de niveau 1 à Coldridge Valley recevait une route partant d'Elwynn Forest (position
du contexte jamais transmise, départ départagé par l'identifiant de quête).

Valeurs : monde fabriqué (`tests/fixtures/route/route.json` et quêtes fabriquées ici, identifiants hors du jeu) ;
réglages (`route.filters`), races et règles d'XP lus dans les données de la version du dépôt ; guides de RestedXP
fabriqués (`tests/fixtures/rxp_guides`). Aucun chiffre de jeu ici."""

import copy
import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json
from test_engine_route import MAPS, ROUTE, VALUES, _book

from forever.engine.route import RouteState, Stop, check_stop
from forever.engine.travel import Graph, map_to_world, travel_params, travel_time
from forever.quests import QuestBook
from forever.route import (
    RouteRequest,
    done_quests,
    race_allowed,
    route_filters,
    route_world,
    rxp_start_giver,
    start_position,
    start_quest,
)
from forever.rxp_guides import read_rxp_guides, who_for

RACES = read_json(DATA_DIR / LOCAL_VERSION / "races.json")["races"]
FILTERS = VALUES["route.filters"]["value"]
GUIDES = FIXTURES / "rxp_guides"


def _travel():
    tp = travel_params(VALUES)
    graph = Graph({}, {})
    return lambda a, b, level: travel_time(graph, a, b, params=tp, level=level, flights_known=frozenset()).seconds


def _world(game_data, book=None, **request):
    req = RouteRequest(**{"class_name": "mage", "faction": "horde", "start_level": 1, "end_level": 5, **request})
    return route_world(
        game_data,
        book or _book(),
        MAPS,
        request=req,
        values=VALUES,
        dungeons=[],
        travel=_travel(),
        kill_seconds=lambda _level: ROUTE["kill_seconds"],
    )


def _with(book, quest_id, **fields):
    """Copie du livre où la quête `quest_id` porte en plus les champs donnés (source fabriquée)."""
    quests = copy.deepcopy(book.quests)
    for key, value in fields.items():
        quests[quest_id]["fields"][key] = {"value": value, "source": "fixture", "certainty": "probable"}
    return QuestBook(quests, [], "fixture", False, [], book.zone_names)


# --- départ ---------------------------------------------------------------------------------------------------


def test_start_from_the_context_position_first(game_data):
    world, _ = _world(game_data)
    req = RouteRequest("mage", "horde", 1, 5, start_at=(9002, 20.0, 30.0))
    point, reason = start_position(MAPS, req, world.quests, rxp_giver=None)
    assert point == map_to_world(MAPS[9002], 20.0, 30.0) and reason == "position"


def test_start_from_the_free_guide_of_the_race_without_position(game_data):
    world, _ = _world(game_data)
    giver = world.quests[110].giver
    point, reason = start_position(MAPS, RouteRequest("mage", "horde", 1, 5), world.quests, rxp_giver=giver)
    assert point == giver and reason == "parcours"


def test_unknown_position_map_falls_back(game_data):
    world, _ = _world(game_data)
    req = RouteRequest("mage", "horde", 1, 5, start_at=(123456789, 20.0, 30.0))
    _, reason = start_position(MAPS, req, world.quests, rxp_giver=None)
    assert reason == "quête"


def test_start_quest_ties_go_to_the_nearest_giver_not_the_lowest_id(game_data):
    world, _ = _world(game_data)
    tied = [world.quests[101], world.quests[110]]
    tied = [q.__class__(**{**q.__dict__, "level": 1, "min_level": 1}) for q in tied]  # même niveau, même minimum
    near = tied[1].giver
    assert start_quest(tied, 1, near=near).id == 110
    assert start_quest(tied, 1).id == 101  # sans position : ordre stable d'avant


def test_rxp_start_giver_is_the_first_accept_of_the_race_chain(game_data):
    world, _ = _world(game_data)
    library = read_rxp_guides(GUIDES)
    giver = rxp_start_giver(library, who_for("Mage", "Orc", "Horde"), world.quests, 1)
    assert giver == world.quests[101].giver  # première prise permise du parcours de la race
    assert rxp_start_giver(library, who_for("Mage", "Gnome", "Alliance"), world.quests, 1) is None  # quêtes absentes


def test_skyborne_races_use_the_restedxp_token():
    for name, race in RACES.items():
        if race.get("client_file") == "Skyborne":
            assert who_for("Mage", name, race["faction"]).race == "Skyborne"
    assert who_for("Mage", "Undead", "Horde").race == "Undead"


# --- quêtes déjà faites ---------------------------------------------------------------------------------------


def test_done_quests_leave_the_route_but_open_their_followers(game_data):
    world, _ = _world(game_data, done=(102,))
    assert 102 not in world.quests
    assert 103 in world.quests  # son prérequis 102 est fait
    start = RouteState(level=2, xp=0.0, position=world.quests[103].giver, done=frozenset({102}))
    assert check_stop(game_data, world, start, Stop("accept", 103)) is None


def test_done_quests_come_from_the_character_profile_only(make_deps, tmp_path):
    deps = make_deps()
    profile = {
        "schema_version": 4,
        "active": "Bob",
        "characters": {
            "Bob": {"quests_completed": {"value": {"102": "2026-10-14T10:00:00Z"}, "source": "Questie"}},
            "Autre": {"quests_completed": {"value": {"101": "2026-10-14T10:00:00Z"}, "source": "Questie"}},
        },
        "realms": {},
        "archived_characters": {},
    }
    deps.profile_path.parent.mkdir(parents=True, exist_ok=True)
    deps.profile_path.write_text(json.dumps(profile), encoding="utf-8")
    assert done_quests(deps, "Bob") == (102,)
    assert done_quests(deps, "Inconnu") == ()
    assert done_quests(deps, None) == ()


# --- race, catégories, drapeaux, métier, niveau ----------------------------------------------------------------


def _race(name):
    return RACES[name]["id"], RACES[name]["faction"].lower()


def test_race_mask_rules():
    gnome, alliance = _race("Gnome")
    human, _ = _race("Human")
    gnome_bit, human_bit = 1 << (gnome - 1), 1 << (human - 1)
    assert race_allowed(0, gnome, RACES)
    assert race_allowed(gnome_bit, gnome, RACES)
    assert not race_allowed(human_bit, gnome, RACES)
    sky = next(
        r["id"] for r in RACES.values() if r.get("client_file") == "Skyborne" and r["faction"].lower() == alliance
    )
    alliance_classic = sum(
        1 << (r["id"] - 1) for r in RACES.values() if r["faction"].lower() == alliance and r["id"] <= 32
    )
    assert race_allowed(alliance_classic, sky, RACES)  # masque de tout le camp : permis
    assert not race_allowed(human_bit, sky, RACES)  # masque d'une seule autre race : écarté
    assert race_allowed(1 << 32, sky, RACES)  # bit étendu des sources de Forever
    assert not race_allowed(1 << 32, gnome, RACES)


def test_other_race_quests_are_dropped(game_data):

    troll, _ = _race("Troll")
    book = _with(_book(), 105, races=1 << (troll - 1))
    world, _ = _world(game_data, book, race="Orc")
    assert 105 not in world.quests and 106 in world.quests
    world, _ = _world(game_data, book, race="Troll")
    assert 105 in world.quests


@pytest.mark.parametrize("field", ["sort", "special"])
def test_event_war_effort_and_repeatable_quests_are_dropped(game_data, field):
    value = FILTERS["excluded_sorts"][0] if field == "sort" else FILTERS["repeatable_flag"]
    world, warnings = _world(game_data, _with(_book(), 105, **{field: value}))
    assert 105 not in world.quests and any("105" in w for w in warnings)


def test_event_flag_drops_the_quest(game_data):
    world, _ = _world(game_data, _with(_book(), 105, special=FILTERS["event_flag"]))
    assert 105 not in world.quests


def test_profession_quests_need_the_profession(game_data):
    sort, name = next(iter(FILTERS["profession_sorts"].items()))
    book = _with(_book(), 105, sort=int(sort))
    world, _ = _world(game_data, book)
    assert 105 not in world.quests
    world, _ = _world(game_data, book, professions=((name, 1, 75),))
    assert 105 in world.quests


def test_required_skill_quests_need_a_profession(game_data):
    world, _ = _world(game_data, _with(_book(), 105, skill=1))
    assert 105 not in world.quests


def test_red_quests_are_not_accepted(game_data):
    red = game_data.leveling.quest_band.red_min_diff
    book = _with(_book(), 105, level=1 + red + 1)
    world, _ = _world(game_data, book)
    state = RouteState(level=1, xp=0.0, position=world.quests[101].giver)
    if 105 in world.quests:
        assert check_stop(game_data, world, state, Stop("accept", 105)) is not None


def test_route_filters_come_from_mechanics():
    filters = route_filters(VALUES)
    assert filters.excluded_sorts == frozenset(int(s) for s in FILTERS["excluded_sorts"])
    assert filters.low_level == FILTERS["low_level"] and filters.capitals == tuple(FILTERS["capitals"])


# --- lecture de Questie : catégorie, drapeaux, métier requis ----------------------------------------------------


def test_questie_category_flags_and_skill_are_read(tmp_path):
    import shutil

    from forever.pipeline.quest_sources import read_questie_quests

    src = FIXTURES / "addons" / "quests" / "Interface" / "AddOns" / "Questie"
    root = tmp_path / "AddOns"
    shutil.copytree(src, root / "Questie")
    db = root / "Questie" / "Database" / "Classic" / "classicQuestDB.lua"
    text = db.read_text(encoding="utf-8")
    sort, flag = FILTERS["excluded_sorts"][0], FILTERS["repeatable_flag"]
    rows = (
        f'[990001] = {{"Fixture Fair",nil,nil,1,5,0,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,{sort},nil,nil,nil,nil,nil,8,{flag}}},\n'
        '[990002] = {"Fixture Craft",nil,nil,1,5,0,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,12,{7,1},nil,nil,nil,nil,8},\n'
    )
    marker = "QuestieDB.questData = [[return {\n"
    assert marker in text
    db.write_text(text.replace(marker, marker + rows), encoding="utf-8")
    source, _ = read_questie_quests(root)
    fair, craft = source.quests[990001], source.quests[990002]
    assert fair["sort"] == sort and fair["special"] == flag and "zone_area" not in fair
    assert craft["skill"] == 7 and craft["zone_area"] == 12 and "sort" not in craft
