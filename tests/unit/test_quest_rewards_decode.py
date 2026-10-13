"""Récompenses des quêtes décodées du client (`quest_rewards.json`) et XP d'un monstre par niveau (`PerKill` de la
GameTable `xp`), T04d, bloc B.

Valeurs attendues lues dans les fixtures : `tests/fixtures/client/QuestXP.csv` (table `QuestXP` de 1.60.1.70338),
`tests/fixtures/client/questcache_sample.wdb` (cache des quêtes du client) et `tests/fixtures/wago/1.60.1.70124/`
(GameTables, dont `xp.txt`). Aucun réseau."""

import csv
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.pipeline.character_scaling import (
    CHARACTER_FILE,
    decode_character_scaling,
    load_character_tables,
    load_gametables,
    read_gametable,
)
from forever.pipeline.decode import decode_version
from forever.pipeline.quest_rewards import (
    QUEST_FILE,
    decode_quest_rewards,
    load_quest_tables,
    new_seen_quests,
    quest_rewards_errors,
    seen_quest_xp,
)
from forever.pipeline.questcache import read_questcache
from forever.pipeline.verify import verify_version

CLIENT = FIXTURES / "client"
SAMPLE = CLIENT / "questcache_sample.wdb"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
MECHANICS = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]


def questxp_rows() -> dict[int, list[int]]:
    with (CLIENT / "QuestXP.csv").open(encoding="utf-8", newline="") as f:
        return {
            int(r["ID"]): [int(r[k]) for k in sorted((k for k in r if k.startswith("Difficulty_")), key=_index)]
            for r in csv.DictReader(f)
        }


def _index(column: str) -> int:
    return int(column.rsplit("_", 1)[1])


@pytest.fixture(scope="module")
def csv_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("quests")
    (root / "enUS").mkdir()
    shutil.copyfile(CLIENT / "QuestXP.csv", root / "enUS" / "QuestXP.csv")
    return root


@pytest.fixture(scope="module")
def cache():
    return read_questcache(SAMPLE)


@pytest.fixture(scope="module")
def doc(csv_dir, cache):
    return decode_quest_rewards(load_quest_tables(csv_dir, RULES), RULES, LOCAL_VERSION, cache=cache)


def test_quest_xp_equals_the_client_table(doc):
    rows = questxp_rows()
    assert {int(k): v for k, v in doc["quest_xp"].items()} == rows
    assert not quest_rewards_errors(doc)


def test_seen_quests_come_from_the_cache(doc, cache):
    assert set(doc["seen_quests"]) == {str(q) for q in cache.records}
    seen = doc["seen_quests"]["479"]
    record = cache.records[479]
    assert (seen["level"], seen["min_level"], seen["sort_id"], seen["next_quest"]) == (
        record.level,
        record.min_level,
        record.sort_id,
        record.next_quest,
    )
    assert (seen["xp_difficulty"], seen["xp_multiplier"], seen["money"]) == (
        record.xp_difficulty,
        record.xp_multiplier,
        record.money,
    )
    assert doc["questcache"]["build"] == cache.build and doc["questcache"]["records"] == len(cache.records)


@pytest.mark.parametrize("quest", [479, 5725, 97249])
def test_seen_quest_xp_is_the_cell_times_the_multiplier(doc, cache, quest):
    record = cache.records[quest]
    cell = questxp_rows()[record.level][record.xp_difficulty]
    assert seen_quest_xp(doc, quest) == pytest.approx(cell * record.xp_multiplier, rel=1e-12)


def test_unseen_quest_has_no_client_xp(doc):
    assert seen_quest_xp(doc, 7) is None


def test_seen_quests_are_kept_from_the_base_and_replaced_by_the_cache(csv_dir, cache, doc):
    tables = load_quest_tables(csv_dir, RULES)
    base = {**doc, "seen_quests": {**doc["seen_quests"], "1": {**doc["seen_quests"]["479"], "level": 1}}}
    base["seen_quests"]["479"] = {**doc["seen_quests"]["479"], "xp_multiplier": 0.5}
    without_cache = decode_quest_rewards(tables, RULES, LOCAL_VERSION, cache=None, base=base)
    assert without_cache["seen_quests"] == base["seen_quests"]
    assert without_cache["questcache"] is None
    with_cache = decode_quest_rewards(tables, RULES, LOCAL_VERSION, cache=cache, base=base)
    assert with_cache["seen_quests"]["1"] == base["seen_quests"]["1"]  # gardée de la base
    assert with_cache["seen_quests"]["479"] == doc["seen_quests"]["479"]  # le cache l'emporte


def test_new_seen_quests_lists_absent_and_changed_quests(doc, cache):
    installed = {**doc, "seen_quests": {k: v for k, v in doc["seen_quests"].items() if k != "5725"}}
    installed["seen_quests"]["479"] = {**doc["seen_quests"]["479"], "xp_difficulty": 1}
    assert new_seen_quests(cache, installed) == [479, 5725]
    assert new_seen_quests(cache, doc) == []
    assert new_seen_quests(cache, None) == sorted(cache.records)


def test_errors_on_a_malformed_document(doc):
    assert quest_rewards_errors([]) != []
    bad = {**doc, "quest_xp": {"16": [1, 2]}}
    assert any("quest_xp" in e for e in quest_rewards_errors(bad))


def test_kill_xp_is_decoded_from_the_xp_gametable():
    doc = decode_character_scaling(
        load_character_tables(WAGO_70124, RULES), RULES, load_gametables(WAGO_70124 / "gametables", RULES), "x"
    )
    per_kill = {int(r["Level"]): r["PerKill"] for r in read_gametable(WAGO_70124 / "gametables" / "xp.txt")}
    cap = RULES["levels"]["level_cap"]
    assert doc["kill_xp"] == [per_kill[lv] for lv in range(1, cap + 1)]


def test_kill_xp_without_the_gametable_is_absent():
    doc = decode_character_scaling(load_character_tables(WAGO_70124, RULES), RULES, {}, "x")
    assert doc["kill_xp"] is None


def test_installed_kill_xp_agrees_with_the_mob_xp_rule():
    """Risque du plan T04d : `PerKill` différent de la règle de `leveling.mob_xp` changerait le poids des niveaux du
    chemin des talents ; il concorde à chaque niveau (sinon arrêt et accord)."""
    char = read_json(DATA_DIR / LOCAL_VERSION / CHARACTER_FILE)
    rule = MECHANICS["leveling.mob_xp"]["value"]
    assert char["kill_xp"] == [rule["base"] + rule["per_level"] * lv for lv in range(1, char["level_cap"] + 1)]


def test_installed_quest_rewards():
    doc = read_json(DATA_DIR / LOCAL_VERSION / QUEST_FILE)
    assert not quest_rewards_errors(doc)
    assert {int(k): v for k, v in doc["quest_xp"].items()} == questxp_rows()
    sample = read_questcache(SAMPLE)
    for quest, record in sample.records.items():
        seen = doc["seen_quests"][str(quest)]
        assert (seen["level"], seen["xp_difficulty"]) == (record.level, record.xp_difficulty), quest


def test_decode_version_writes_quest_rewards(tmp_path):
    csv = tmp_path / "csv"
    shutil.copytree(WAGO_70124, csv)
    shutil.copyfile(CLIENT / "QuestXP.csv", csv / "enUS" / "QuestXP.csv")
    candidate = decode_version(
        isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=csv, out=tmp_path / "cand", questcache=SAMPLE
    )
    vdir = candidate.root / LOCAL_VERSION
    written = read_json(vdir / QUEST_FILE)
    assert "inherited_from" not in written
    assert written["seen_quests"]["479"]["xp_difficulty"] == read_questcache(SAMPLE).records[479].xp_difficulty
    sources = read_json(vdir / "sources.json")
    assert sources["files"][QUEST_FILE]["certainty"] == "certain"
    report = verify_version(isolated_deps(tmp_path), str(candidate.root))
    assert report["ok"], report["errors"]


def test_decode_version_without_questxp_inherits_quest_rewards(tmp_path):
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand")
    written = read_json(candidate.root / LOCAL_VERSION / QUEST_FILE)
    assert written["inherited_from"] == LOCAL_VERSION
