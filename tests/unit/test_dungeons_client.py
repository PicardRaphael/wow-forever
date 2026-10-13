"""Donjons décodés du client (`dungeons.json`), DJ1, bloc A.

Valeurs attendues lues dans les fixtures `tests/fixtures/wago/dungeons/enUS/` (lignes des tables de 1.60.1.70338
extraites par `scripts/extract_dungeon_fixtures.py`) ; les identifiants désignent des lignes du client. Aucun réseau."""

import copy
import csv
import re
import shutil

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.pipeline.decode import decode_version
from forever.pipeline.dungeons_client import (
    DUNGEON_FILE,
    decode_dungeons,
    dungeon_table_files,
    dungeons_errors,
    load_dungeon_tables,
)
from forever.pipeline.verify import verify_version

CSV_DIR = FIXTURES / "wago" / "dungeons"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
RAGEFIRE, DEADMINES, MONASTERY, GNOMEREGAN = 389, 36, 189, 90
THANES, EXCAVATION, RUINS, DALARAN = 3065, 2998, 2999, 2959
MOLTEN_CORE, WARSONG, CRYPTS = 409, 489, 2875
LFG_EXCAVATION, LFG_RUINS, LFG_THANES = 3274, 3272, 3273


def rows(table):
    with (CSV_DIR / "enUS" / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def row(table, key, value):
    return next(r for r in rows(table) if int(r[key]) == value)


def decoded(rules=RULES):
    return decode_dungeons(load_dungeon_tables(CSV_DIR, rules), rules, LOCAL_VERSION)


def test_document_is_well_formed():
    doc = decoded()
    assert doc["build"] == LOCAL_VERSION and doc["certainty"] == "certain"
    assert dungeons_errors(doc) == []
    assert dungeons_errors({"instances": []})  # forme fausse : erreur nommée


def test_five_man_instances_are_kept():
    doc = decoded()
    kept = {int(k) for k in doc["instances"]}
    assert {RAGEFIRE, DEADMINES, MONASTERY, GNOMEREGAN, THANES, EXCAVATION, RUINS, DALARAN} <= kept
    assert MOLTEN_CORE not in kept and WARSONG not in kept  # raid, champ de bataille
    assert CRYPTS not in kept  # instance de groupe sans entrée de recherche : listée à part
    assert {u["map_id"] for u in doc["unlisted"]} >= {CRYPTS}


def test_lfg_levels_are_read():
    doc = decoded()
    lfg = row("LFGDungeons", "ID", LFG_EXCAVATION)
    tuning = row("ContentTuning", "ID", int(lfg["ContentTuningID"]))
    entry = next(e for e in doc["instances"][str(EXCAVATION)]["lfg"] if e["id"] == LFG_EXCAVATION)
    assert entry["level"] == int(tuning["MinLevelSquish"]) == int(tuning["MaxLevelSquish"])
    assert entry["lfg_min"] is None and entry["lfg_max"] is None  # colonnes à zéro : non renseignées
    ruins = row("ContentTuning", "ID", int(row("LFGDungeons", "ID", LFG_RUINS)["ContentTuningID"]))
    entry = doc["instances"][str(RUINS)]["lfg"][0]
    assert (entry["lfg_min"], entry["lfg_max"]) == (int(ruins["LfgMinLevel"]), int(ruins["LfgMaxLevel"]))


def test_lfg_joined_by_name_without_the():
    """« Hall of Thanes » (LFGDungeons) et « The Hall of Thanes » (Map) : une seule instance."""
    doc = decoded()
    assert [e["id"] for e in doc["instances"][str(THANES)]["lfg"]] == [LFG_THANES]


def test_lfg_aliases_come_from_the_rules():
    rules = copy.deepcopy(RULES)
    name = row("LFGDungeons", "ID", LFG_RUINS)["Name_lang"]
    rules["dungeons"]["lfg_names"] = {name: row("Map", "ID", DALARAN)["MapName_lang"]}
    doc = decoded(rules)
    assert LFG_RUINS in [e["id"] for e in doc["instances"][str(DALARAN)]["lfg"]]
    assert str(RUINS) not in doc["instances"]


def test_encounters_are_ordered():
    doc = decoded()
    expected = sorted(
        (r for r in rows("DungeonEncounter") if int(r["MapID"]) == EXCAVATION),
        key=lambda r: (int(r["OrderIndex"]), int(r["ID"])),
    )
    got = doc["instances"][str(EXCAVATION)]["encounters"]
    assert [e["id"] for e in got] == [int(r["ID"]) for r in expected]
    assert [e["name"] for e in got] == [r["Name_lang"] for r in expected]


def test_other_difficulties_are_dropped():
    doc = decoded()
    kept_difficulties = set(RULES["dungeons"]["difficulties"])
    expected = {
        int(r["ID"])
        for r in rows("DungeonEncounter")
        if int(r["MapID"]) == GNOMEREGAN and int(r["DifficultyID"]) in kept_difficulties
    }
    assert {e["id"] for e in doc["instances"][str(GNOMEREGAN)]["encounters"]} == expected
    assert len(expected) < sum(1 for r in rows("DungeonEncounter") if int(r["MapID"]) == GNOMEREGAN)


def test_instance_area_is_read():
    doc = decoded()
    areas = {int(r["ID"]) for r in rows("AreaTable") if int(r["ContinentID"]) == THANES}
    assert set(doc["instances"][str(THANES)]["areas"]) == areas


def test_no_journal_items_from_this_client():
    """Tables du journal absentes du build (DON9) : aucun butin du client, la note le dit."""
    doc = decoded()
    assert all("items" not in i for i in doc["instances"].values())
    assert any("journal" in n.lower() for n in doc["notes"])


def test_no_game_number_in_the_decoder():
    source = (DATA_DIR.parent / "pipeline" / "dungeons_client.py").read_text(encoding="utf-8")
    for number in (RAGEFIRE, THANES, EXCAVATION, DALARAN, LFG_EXCAVATION):
        assert not re.search(rf"\b{number}\b", source), number


def test_gate_is_the_dungeon_tables():
    assert [t for t, _ in dungeon_table_files(RULES)] == RULES["dungeon_tables"]
    assert {"Map", "LFGDungeons", "DungeonEncounter", "ContentTuning", "AreaTable"} <= set(RULES["dungeon_tables"])


def test_missing_tables_give_a_note(tmp_path):
    """Candidate sans les tables des donjons : fichier hérité de la base, note, aucune erreur."""
    csv_dir = tmp_path / "csv"
    shutil.copytree(WAGO_70124, csv_dir)
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=csv_dir, out=tmp_path / "cand")
    written = read_json(candidate.root / LOCAL_VERSION / DUNGEON_FILE)
    assert written.get("inherited_from") == LOCAL_VERSION


def test_decode_version_writes_dungeons_when_tables_are_present(tmp_path):
    csv_dir = tmp_path / "csv"
    shutil.copytree(WAGO_70124, csv_dir)
    for name, rel in dungeon_table_files(RULES):
        shutil.copyfile(CSV_DIR / rel, csv_dir / rel)
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=csv_dir, out=tmp_path / "cand")
    vdir = candidate.root / LOCAL_VERSION
    written = read_json(vdir / DUNGEON_FILE)
    assert "inherited_from" not in written and dungeons_errors(written) == []
    sources = read_json(vdir / "sources.json")
    assert sources["files"][DUNGEON_FILE]["certainty"] == "certain"
    report = verify_version(isolated_deps(tmp_path), str(candidate.root))
    assert report["ok"], report["errors"]


def test_fetch_lists_instance_tables(make_deps):
    from forever.cli import _fetch_defaults

    tables, _ = _fetch_defaults(make_deps())
    assert set(RULES["dungeon_tables"]) <= set(tables)


def test_installed_dungeons_match_the_fixture_rows():
    doc = read_json(DATA_DIR / LOCAL_VERSION / DUNGEON_FILE)
    assert dungeons_errors(doc) == []
    fixture = decoded()
    for map_id in (EXCAVATION, DALARAN, THANES, RUINS):
        assert doc["instances"][str(map_id)]["encounters"] == fixture["instances"][str(map_id)]["encounters"]
