"""GameTables du client par wago.tools (`api/casc`, T08b, bloc A) : adresse, cache, réponse vide = absente ;
réseau simulé. Fixture synthétique (structure d'une GameTable, valeurs inventées) : tests/fixtures/wago/gametables/."""

import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, FakeHttp

from forever.cli import main
from forever.errors import FetchFailedError, OfflineError
from forever.pipeline.fetch import (
    fetch_gametables,
    gametable_path,
    gametable_url,
    index_path,
    looks_like_gametable,
)

BODY = (FIXTURES / "wago" / "gametables" / "synthetique.txt").read_bytes()
RULES = json.loads((DATA_DIR / LOCAL_VERSION / "decode_rules.json").read_text(encoding="utf-8"))
GAMETABLES = RULES["gametables"]


def test_decode_rules_name_the_gametables():
    assert {"xp", "hppersta", "basemp", "armormitigationbylvl", "npctotalhp"} <= set(GAMETABLES)
    assert all(isinstance(v, int) and v > 0 for v in GAMETABLES.values())


def test_gametable_url_form():
    assert gametable_url(12, LOCAL_VERSION) == f"https://wago.tools/api/casc/12?version={LOCAL_VERSION}"


def test_looks_like_gametable():
    assert looks_like_gametable(BODY)
    assert not looks_like_gametable(b"<!DOCTYPE html><html></html>")
    assert not looks_like_gametable(b'{"error": "not found"}')
    assert not looks_like_gametable(b"\xff\xfe")


def test_fetch_writes_file_and_index(make_deps):
    http = FakeHttp(routes={gametable_url(5, LOCAL_VERSION): BODY})
    deps = make_deps(http=http)
    [res] = fetch_gametables(deps, LOCAL_VERSION, {"xp": 5})
    assert res["name"] == "xp" and res["file_id"] == 5 and not res["from_cache"] and not res["absent"]
    assert gametable_path(deps.cache_dir, LOCAL_VERSION, "xp").read_bytes() == BODY
    index = json.loads(index_path(deps.cache_dir, LOCAL_VERSION).read_text(encoding="utf-8"))
    assert index["tables"]["gametables/xp"]["file_id"] == 5
    assert index["tables"]["gametables/xp"]["bytes"] == len(BODY)


def test_second_fetch_is_served_from_cache(make_deps):
    http = FakeHttp(routes={gametable_url(5, LOCAL_VERSION): BODY})
    deps = make_deps(http=http)
    fetch_gametables(deps, LOCAL_VERSION, {"xp": 5})
    [res] = fetch_gametables(deps, LOCAL_VERSION, {"xp": 5})
    assert res["from_cache"] and len(http.calls) == 1


def test_empty_answer_is_absent_and_nothing_else_is_called(make_deps):
    http = FakeHttp(routes={gametable_url(5, LOCAL_VERSION): b"", gametable_url(6, LOCAL_VERSION): BODY})
    deps = make_deps(http=http)
    results = fetch_gametables(deps, LOCAL_VERSION, {"vide": 5, "xp": 6})
    assert [(r["name"], r["absent"]) for r in results] == [("vide", True), ("xp", False)]
    assert [c[0] for c in http.calls] == [gametable_url(5, LOCAL_VERSION), gametable_url(6, LOCAL_VERSION)]
    assert not gametable_path(deps.cache_dir, LOCAL_VERSION, "vide").exists()
    index = json.loads(index_path(deps.cache_dir, LOCAL_VERSION).read_text(encoding="utf-8"))
    assert index["tables"]["gametables/vide"]["absent"] is True
    again = fetch_gametables(deps, LOCAL_VERSION, {"vide": 5})
    assert again[0]["absent"] and again[0]["from_cache"] and len(http.calls) == 2


def test_html_answer_is_refused(make_deps):
    http = FakeHttp(routes={gametable_url(5, LOCAL_VERSION): b"<html>erreur</html>"})
    deps = make_deps(http=http)
    with pytest.raises(FetchFailedError):
        fetch_gametables(deps, LOCAL_VERSION, {"xp": 5})
    assert not gametable_path(deps.cache_dir, LOCAL_VERSION, "xp").exists()


def test_offline_makes_no_call(make_deps):
    http = FakeHttp(body=BODY)
    with pytest.raises(OfflineError):
        fetch_gametables(make_deps(http=http, offline=True), LOCAL_VERSION, {"xp": 5})
    assert http.calls == []


def test_cli_fetch_gametables_reads_decode_rules(capsys, make_deps):
    http = FakeHttp(routes={gametable_url(fid, LOCAL_VERSION): BODY for fid in GAMETABLES.values()})
    code = main(["fetch", "--version", LOCAL_VERSION, "--gametables", "--json"], make_deps(http=http))
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert {g["name"] for g in data["gametables"]} == set(GAMETABLES)
    assert len(http.calls) == len(GAMETABLES)
    assert data["provenance"]["game_version"] == LOCAL_VERSION
