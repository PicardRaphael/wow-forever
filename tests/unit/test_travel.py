"""Trajets décodés du client (`travel.json`), RX1, bloc B.

Valeurs attendues lues dans les fixtures `tests/fixtures/wago/travel/enUS/` (lignes des tables de 1.60.1.70338
extraites par `scripts/extract_travel_fixtures.py`) ; les identifiants désignent des lignes du client. Aucun réseau."""

import csv
import itertools
import math
import re
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, REPO_ROOT, WAGO_70124, isolated_deps, read_json

from forever.pipeline.decode import decode_version
from forever.pipeline.travel_client import (
    TRAVEL_FILE,
    decode_travel,
    load_travel_tables,
    travel_errors,
    travel_table_files,
)
from forever.pipeline.verify import verify_version
from forever.travel import graph_from_doc

CSV_DIR = FIXTURES / "wago" / "travel"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
STORMWIND, SENTINEL_HILL, DARKSHIRE = 2, 4, 12  # lignes de TaxiNodes
TO_SENTINEL_HILL, TO_DARKSHIRE = 6, 23  # lignes de TaxiPath
ELWYNN = 1429  # ligne de UiMapAssignment


def rows(table):
    with (CSV_DIR / "enUS" / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def segments_length(path_id):
    points = sorted((r for r in rows("TaxiPathNode") if int(r["PathID"]) == path_id), key=lambda r: int(r["NodeIndex"]))
    total = 0.0
    for a, b in itertools.pairwise(points):
        total += math.dist(
            [float(a["Loc_0"]), float(a["Loc_1"]), float(a["Loc_2"])],
            [float(b["Loc_0"]), float(b["Loc_1"]), float(b["Loc_2"])],
        )
    return total


def decoded(rules=RULES):
    return decode_travel(load_travel_tables(CSV_DIR, rules), rules, LOCAL_VERSION)


def test_document_is_well_formed():
    doc = decoded()
    assert doc["build"] == LOCAL_VERSION and doc["certainty"] == "certain"
    assert travel_errors(doc) == []
    assert travel_errors({"nodes": []})  # forme fausse : erreur nommée


def test_travel_tables_decoded():
    doc = decoded()
    nodes = {n["id"]: n for n in doc["nodes"]}
    assert set(nodes) == {STORMWIND, SENTINEL_HILL, DARKSHIRE}
    sw = next(r for r in rows("TaxiNodes") if int(r["ID"]) == STORMWIND)
    assert nodes[STORMWIND]["name"] == sw["Name_lang"]
    assert nodes[STORMWIND]["continent"] == int(sw["ContinentID"])
    assert nodes[STORMWIND]["x"] == pytest.approx(float(sw["Pos_0"]))
    assert nodes[STORMWIND]["y"] == pytest.approx(float(sw["Pos_1"]))
    assert {n["faction"] for n in nodes.values()} == {"alliance"}  # drapeau du camp lu par decode_rules.json
    paths = {p["id"]: p for p in doc["paths"]}
    assert set(paths) == {TO_SENTINEL_HILL, TO_DARKSHIRE}
    p = paths[TO_SENTINEL_HILL]
    row = next(r for r in rows("TaxiPath") if int(r["ID"]) == TO_SENTINEL_HILL)
    assert (p["from"], p["to"], p["cost"]) == (int(row["FromTaxiNode"]), int(row["ToTaxiNode"]), int(row["Cost"]))
    assert p["length"] == pytest.approx(segments_length(TO_SENTINEL_HILL), rel=1e-9)
    assert paths[TO_DARKSHIRE]["length"] == pytest.approx(segments_length(TO_DARKSHIRE), rel=1e-9)


def test_teleport_segment_is_excluded():
    tables = load_travel_tables(CSV_DIR, RULES)
    nodes = [dict(r) for r in tables["TaxiPathNode"]]
    first = next(r for r in nodes if int(r["PathID"]) == TO_SENTINEL_HILL and int(r["NodeIndex"]) == 0)
    first["Flags"] = RULES["travel"]["teleport_flag"]  # segment suivant le premier point : téléportation
    doc = decode_travel({**tables, "TaxiPathNode": nodes}, RULES, LOCAL_VERSION)
    length = next(p["length"] for p in doc["paths"] if p["id"] == TO_SENTINEL_HILL)
    assert length < segments_length(TO_SENTINEL_HILL)


def test_maps_decoded():
    doc = decoded()
    maps = {m["ui_map"]: m for m in doc["maps"]}
    row = next(r for r in rows("UiMapAssignment") if int(r["UiMapID"]) == ELWYNN)
    m = maps[ELWYNN]
    assert m["continent"] == int(row["MapID"])
    assert (m["min_x"], m["min_y"]) == pytest.approx((float(row["Region_0"]), float(row["Region_1"])))
    assert (m["max_x"], m["max_y"]) == pytest.approx((float(row["Region_3"]), float(row["Region_4"])))


def test_graph_from_doc_filters_faction():
    doc = decoded()
    graph, maps = graph_from_doc(doc, "alliance")
    assert set(graph.nodes) == {STORMWIND, SENTINEL_HILL, DARKSHIRE}
    assert {e.to for e in graph.edges[STORMWIND]} == {SENTINEL_HILL, DARKSHIRE}
    assert ELWYNN in maps
    horde, _ = graph_from_doc(doc, "horde")
    assert horde.nodes == {} and horde.edges == {}


def test_no_game_number_in_the_decoder():
    source = (REPO_ROOT / "forever" / "pipeline" / "travel_client.py").read_text(encoding="utf-8")
    for number in (STORMWIND, SENTINEL_HILL, DARKSHIRE, TO_SENTINEL_HILL, TO_DARKSHIRE, ELWYNN):
        assert not re.search(rf"\b{number}\b", source), number


def test_gate_is_the_travel_tables():
    assert [t for t, _ in travel_table_files(RULES)] == RULES["travel_tables"]
    assert set(RULES["travel_tables"]) == {"TaxiNodes", "TaxiPath", "TaxiPathNode", "UiMapAssignment"}


def test_missing_tables_give_a_note(tmp_path):
    """Candidate sans les tables des trajets : fichier hérité de la base, aucune erreur."""
    csv_dir = tmp_path / "csv"
    shutil.copytree(WAGO_70124, csv_dir)
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=csv_dir, out=tmp_path / "cand")
    written = read_json(candidate.root / LOCAL_VERSION / TRAVEL_FILE)
    assert written.get("inherited_from") == LOCAL_VERSION


def test_decode_version_writes_travel_when_tables_are_present(tmp_path):
    csv_dir = tmp_path / "csv"
    shutil.copytree(WAGO_70124, csv_dir)
    for _, rel in travel_table_files(RULES):
        shutil.copyfile(CSV_DIR / rel, csv_dir / rel)
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=csv_dir, out=tmp_path / "cand")
    vdir = candidate.root / LOCAL_VERSION
    written = read_json(vdir / TRAVEL_FILE)
    assert "inherited_from" not in written and travel_errors(written) == []
    sources = read_json(vdir / "sources.json")
    assert sources["files"][TRAVEL_FILE]["certainty"] == "certain"
    report = verify_version(isolated_deps(tmp_path), str(candidate.root))
    assert report["ok"], report["errors"]


def test_fetch_lists_travel_tables(make_deps):
    from forever.cli import _fetch_defaults

    tables, _ = _fetch_defaults(make_deps())
    assert set(RULES["travel_tables"]) <= set(tables)


def test_installed_travel_matches_the_fixture_rows():
    doc = read_json(DATA_DIR / LOCAL_VERSION / TRAVEL_FILE)
    assert travel_errors(doc) == []
    fixture = decoded()
    installed = {p["id"]: p for p in doc["paths"]}
    for p in fixture["paths"]:
        assert installed[p["id"]]["length"] == pytest.approx(p["length"], rel=1e-9)
    nodes = {n["id"]: n for n in doc["nodes"]}
    for n in fixture["nodes"]:
        assert nodes[n["id"]] == n
