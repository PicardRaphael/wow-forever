"""Livre des donjons (DJ1, bloc C) : fusion champ par champ du client (`dungeons.json` décodé des fixtures wago) et
des addons (fixtures synthétiques `tests/fixtures/addons/dungeons/`), écarts listés, rattachement des quêtes,
« à faire d'abord », butin et taux, niveau des boss relevé dans un journal (`tests/fixtures/dungeons/`).

Valeurs attendues : celles écrites dans les fixtures ; aucun chiffre de jeu ici, aucun réseau."""

import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.dungeons import (
    build_dungeons,
    dungeon_info,
    logged_boss_levels,
    lookup_dungeons,
    merge_dungeons,
    render_report,
    resolve,
    where_item,
)
from forever.pipeline.dungeon_sources import (
    read_atlasloot,
    read_companion,
    read_fdj_dungeons,
    read_fojji,
    read_guide_dungeons,
    read_naowh_journal,
    read_naowh_runs,
    read_zoneinfo,
)
from forever.pipeline.dungeons_client import decode_dungeons, load_dungeon_tables
from forever.quests import build_quests

WOW = FIXTURES / "addons" / "dungeons"
ADDONS = WOW / "Interface" / "AddOns"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
CLIENT = decode_dungeons(load_dungeon_tables(FIXTURES / "wago" / "dungeons", RULES), RULES, LOCAL_VERSION)
MONSTERS = read_json(FIXTURES / "dungeons" / "monsters_bosses.json")
ITEMS = {int(k): v for k, v in read_json(FIXTURES / "dungeons" / "items.json").items()}
READERS = (
    read_naowh_journal,
    read_fojji,
    read_fdj_dungeons,
    read_guide_dungeons,
    read_atlasloot,
    read_companion,
    read_zoneinfo,
)


def sources():
    return [s for s in (r(ADDONS) for r in READERS) if s is not None]


@pytest.fixture(scope="module")
def quest_book(tmp_path_factory):
    return build_quests(isolated_deps(tmp_path_factory.mktemp("quests")), wow_dir=WOW)


@pytest.fixture(scope="module")
def book(quest_book):
    return merge_dungeons(CLIENT, sources(), book=quest_book)


def boss(dungeon, name):
    return next(b for b in dungeon["bosses"] if b["name"] == name)


def item(b, item_id):
    return next(x for x in b["loot"] if x["item"] == item_id)


def test_aliases_join_on_instance(book):
    """« Hall of Thanes » (ForeverDungeonJournal, Forever Guide) et « The Hall of Thanes » (client) : une entrée."""
    thanes = book.dungeons["3065"]
    assert {"client", "fdj", "forever_guide"} <= set(thanes["sources"])
    assert not any(k.startswith("name:") and "thanes" in k for k in book.dungeons)
    assert resolve(book, "Hall of Thanes") == resolve(book, "The Hall of Thanes") == "3065"


def test_level_discrepancy_is_listed(book):
    excavation = book.dungeons["2998"]
    levels = excavation["fields"]["levels"]
    assert levels["value"] == {"min": 24, "max": 29} and levels["source"] == "naowh_dj"  # ordre déclaré
    others = {o["source"]: o["value"] for o in levels["others"]}
    assert others["fojji"] == {"min": 26, "max": 31} and others["fdj"] == {"min": 26, "max": 33}
    assert any(d["field"] == "levels" for d in excavation["discrepancies"])
    client_level = next(e for e in CLIENT["instances"]["2998"]["lfg"])["level"]
    assert excavation["fields"]["client_level"] == {"value": client_level, "source": "client", "certainty": "probable"}


def test_client_encounters_win(book):
    excavation = book.dungeons["2998"]
    expected = [e["name"] for e in CLIENT["instances"]["2998"]["encounters"]]
    assert [b["name"] for b in excavation["bosses"]] == expected  # Highland Horror comprise, ordre du client
    assert boss(excavation, "Highland Horror")["npc"] == 900001  # PNJ lu chez Naowh
    assert boss(excavation, "Highland Horror")["encounter"] is not None


def test_copied_boss_levels_count_once(book):
    level = boss(book.dungeons["2998"], "Saltspine")["level"]
    assert level["value"] == 27 and set(level["sources"]) == {"fojji", "fdj"}
    assert level["independent"] == 1  # FojjiCore et ForeverDungeonJournal : même valeur copiée


def test_logged_boss_level_wins(quest_book):
    logged = logged_boss_levels(MONSTERS)
    assert logged == {11520: [17]}  # niveau « probable » (Questie) ignoré
    book = merge_dungeons(CLIENT, sources(), book=quest_book, logged_levels=logged)
    level = boss(book.dungeons["389"], "Taragaman the Hungerer")["level"]
    assert (level["value"], level["source"], level["certainty"]) == (17, "journal", "certain")
    assert any(o["source"] == "naowh_dj" and o["value"] == 16 for o in level["others"])


def test_rate_order(book):
    cape = item(boss(book.dungeons["389"], "Taragaman the Hungerer"), 14149)
    assert cape["rate"] == pytest.approx(0.32) and cape["rate_source"] == "naowh_dj" and not cape.get("classic")
    others = {o["source"]: o for o in cape["others"]}
    assert others["fojji"]["rate"] == pytest.approx(0.305)
    assert others["atlasloot"]["classic"] is True and others["forever_guide"]["classic"] is True
    cuffs = item(boss(book.dungeons["389"], "Taragaman the Hungerer"), 14148)
    assert cuffs["rate_source"] == "fojji"  # 0 chez Naowh : inconnu, source suivante


def test_unknown_rate_is_null(book):
    fang = item(boss(book.dungeons["2999"], "Witherfang"), 280500)
    assert fang["rate"] is None and fang["rate_source"] is None


def test_observed_loot_wins(quest_book):
    runs = read_naowh_runs(WOW / "WTF")
    book = merge_dungeons(CLIENT, sources(), book=quest_book, records={"kills": runs.kills, "loot": runs.loot})
    cape = item(boss(book.dungeons["389"], "Taragaman the Hungerer"), 14149)
    assert cape["rate_source"] == "relevé" and cape["certainty"] == "certain"
    assert cape["observed"] == {"drops": 1, "kills": 1}
    assert any(o["source"] == "naowh_dj" for o in cape["others"])  # écart signalé


def test_quests_attached_with_xp_source(book, quest_book):
    rfc = book.dungeons["389"]
    ids = [q["id"] for q in rfc["quests"]]
    assert {5723, 5728} <= set(ids)
    for q in rfc["quests"]:
        entry = quest_book.quests[q["id"]]["fields"].get("xp")
        assert q["xp"] == (entry["value"] if entry else None)
        assert q["xp_source"] == (entry["source"] if entry else None)
    assert next(q for q in rfc["quests"] if q["id"] == 5723)["min_level"] == 9  # QuestMinLevel de Naowh


def test_first_steps_are_ordered(book):
    assert book.dungeons["389"]["first_steps"] == [5726, 5727]  # chaîne de 5728, hors du donjon
    excavation = book.dungeons["2998"]["first_steps"]
    assert excavation[0] == 96498 and 96499 in excavation  # alternative : la première est retenue


def test_access_keys_are_kept(book):
    assert book.dungeons["2998"]["access"][0]["item"] == 280100


def test_wings_are_distinct(book):
    wings = [k for k in book.dungeons if k.startswith("189:")]
    assert len(wings) == 2 and "189" not in book.dungeons
    graveyard = book.dungeons[resolve(book, "Scarlet Monastery: Graveyard")]
    assert graveyard["fields"]["levels"]["value"] == {"min": 26, "max": 36} and graveyard["instance"] == 189


def test_addon_only_dungeon_is_kept(book):
    key = resolve(book, "Alcaz Prison")
    assert key is not None and book.dungeons[key]["closed"] is True and book.dungeons[key]["instance"] is None


def test_usable_for_class_and_level(book):
    mage = dungeon_info(book, "389", class_name="mage", level=14, items=ITEMS)
    cape = item(boss(mage, "Taragaman the Hungerer"), 14149)
    assert cape["usable"] is True and cape["level_ok"] is False
    warrior = dungeon_info(book, "389", class_name="warrior", level=20, items=ITEMS)
    assert item(boss(warrior, "Taragaman the Hungerer"), 14149)["usable"] is False
    assert item(boss(warrior, "Taragaman the Hungerer"), 14148)["usable"] is True


def test_runs_are_attached(quest_book):
    runs = read_naowh_runs(WOW / "WTF").runs
    book = merge_dungeons(CLIENT, sources(), book=quest_book, runs=runs)
    seconds = sorted(r["seconds"] for r in book.dungeons["389"]["runs"])
    assert seconds == [2360, 2400]


def test_where_item(book):
    (hit,) = where_item(book, 14149)
    assert hit["dungeon"] == "389" and hit["boss"] == "Taragaman the Hungerer"
    assert hit["rate"] == pytest.approx(0.32) and hit["source"] == "naowh_dj" and hit["version"] == "1.1.11"


def test_lookup_by_level(book):
    keys = {d["id"] for d in lookup_dungeons(book, level=15)}
    assert "389" in keys and "2998" not in keys


def test_build_dungeons_reads_the_cache(tmp_path):
    deps = isolated_deps(tmp_path)
    first = build_dungeons(deps, wow_dir=WOW)
    second = build_dungeons(deps, wow_dir=WOW)
    assert not first.from_cache and second.from_cache and second.fingerprint == first.fingerprint
    assert {s["source"] for s in first.sources} >= {"client", "naowh_dj", "fdj"}
    assert any(s["source"] == "naowh_dj" and s["version"] == "1.1.11" for s in first.sources)


def test_report_has_counts_and_no_rates(book):
    report = render_report(book)
    assert "Excavation Site: Wetlands" in report and "naowh_dj" in report
    assert "0.32" not in report and "14149" not in report  # agrégats seulement (décision 133)


def test_book_is_json_serializable(book):
    json.dumps(book.dungeons)
