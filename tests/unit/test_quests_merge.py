"""Quêtes de Forever fusionnées (T04d, bloc D) : sources, priorité par champ, statut, écarts.

Fixture : `tests/fixtures/addons/quests/` (dossier du client réduit, extrait des addons installés par
`scripts/extract_quest_fixtures.py addons`, voir son README) ; quêtes vues par le client : `quest_rewards.json` de la
version du dépôt. Aucun réseau."""

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.pipeline.quest_rewards import seen_quest_xp
from forever.quests import STATUSES, build_quests, value

WOW = FIXTURES / "addons" / "quests"


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    from conftest import isolated_deps

    deps = isolated_deps(tmp_path_factory.mktemp("quests"))
    return build_quests(deps, wow_dir=WOW)


def test_every_source_is_read(book):
    keys = {s["source"] for s in book.sources}
    assert keys >= {"questie", "questie_forever", "completo", "journeys", "naowh_dj", "forever_guide", "fdj", "client"}
    assert all(q["status"] in STATUSES for q in book.quests.values())


def test_new_forever_quest_from_completo(book):
    q = book.quests[92432]
    assert q["status"] == "nouvelle"
    giver = value(q, "giver")
    assert (giver["name"], giver["map"], giver["x"], giver["y"]) == ("Emissary Jacques", 1424, 48.3, 60.1)
    assert q["fields"]["giver"]["source"] == "completo"
    assert q["fields"]["giver"]["certainty"] == "suppose"


def test_level_discrepancy_is_kept_and_priority_decides(book):
    q = book.quests[5761]
    assert q["discrepancies"]["level"]["naowh_dj"] == 9
    assert q["discrepancies"]["level"]["forever_guide"] == 16
    assert value(q, "level") == 16 and q["fields"]["level"]["source"] == "forever_guide"
    assert value(q, "min_level") == 9


def test_agreeing_prerequisites_are_not_a_discrepancy(book):
    q = book.quests[7]
    assert value(q, "prereq_any") == [783]
    assert "prereq_any" not in q["discrepancies"]
    assert {"questie", "completo"} <= set(q["sources"])


def test_fdj_internal_xp_discrepancy_is_reported(book):
    q = book.quests[96395]
    xp = q["discrepancies"]["xp"]
    assert xp["fdj"] != xp["fdj_text"]


def test_forever_guide_new_quest_with_its_giver_and_turn_in(book):
    q = book.quests[96403]
    assert q["status"] == "nouvelle"
    assert value(q, "new") is True
    assert value(q, "giver")["name"] == value(q, "turn_in")["name"] == "Thom Filch"
    assert value(q, "giver")["map"] == 1455


def test_classic_quest_absent_from_completo_in_a_covered_zone(book):
    q = book.quests[7677]  # README de la fixture : quête Classic d'Elwynn Forest absente de Completo
    assert q["status"] == "absente des sources Forever"
    assert q["certainty"] == "suppose"


def test_client_xp_wins_over_questie_and_makes_the_quest_retouched(book):
    rewards = read_json(DATA_DIR / LOCAL_VERSION / "quest_rewards.json")
    q = book.quests[5725]
    assert q["fields"]["xp"]["source"] == "client"
    assert q["fields"]["xp"]["certainty"] == "probable"
    assert value(q, "xp") == pytest.approx(seen_quest_xp(rewards, 5725), rel=1e-12)
    assert q["status"] == "retouchée" and "xp" in q["changed_fields"]


def test_unchanged_classic_quest(book):
    q = book.quests[783]
    assert q["status"] == "inchangée"
    assert q["changed_fields"] == []


def test_quest_learned_in_game_is_a_player_record(book):
    q = book.quests[96607]  # QuestieForeverDB de la fixture
    assert q["status"] == "nouvelle"
    assert q["fields"]["name"]["source"] == "questie_forever"
    assert q["fields"]["name"]["certainty"] == "probable"


def test_gearquest_rewards_attached_by_unique_name_only(book):
    assert value(book.quests[825], "rewards")["items"]
    assert value(book.quests[790], "rewards") is None or not value(book.quests[790], "rewards").get("items")
    assert any("Sarkoth" in n and "ambigu" in n for n in book.notes)


def test_rx1_fields_are_present_for_a_dungeon_quest(book):
    q = book.quests[5723]
    assert value(q, "dungeon") == "Ragefire Chasm"
    assert value(q, "faction") == "horde"
    assert value(q, "objectives")["creatures"]
    turn_in = value(q, "turn_in")
    assert {"map", "x", "y"} <= set(turn_in)


def test_nothing_from_the_list_is_written_in_the_repository(book):
    assert book.fingerprint and not (DATA_DIR / "quests").exists()
