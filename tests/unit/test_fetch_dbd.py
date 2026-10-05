"""Définitions de structure des tables par WoWDBDefs (T08c, bloc B) : commit épinglé, cache par commit, empreintes,
second appel sans téléchargement, refus d'une réponse qui n'est pas un `.dbd` ; réseau simulé (`Deps.http_get`).
Corps `.dbd` synthétiques (structure du format, aucune valeur de jeu)."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, FakeHttp, read_json

from forever.cli import main
from forever.errors import FetchFailedError, OfflineError
from forever.pipeline.dbcache import known_tables
from forever.pipeline.fetch import (
    DBD_COMMIT_URL,
    DBD_INDEX,
    DBD_LICENSE_URL,
    dbd_dir,
    dbd_tables,
    dbd_url,
    fetch_dbd,
    looks_like_dbd,
    read_dbd_index,
)

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER = "fedcba9876543210fedcba9876543210fedcba98"
COMMIT = json.dumps({"sha": SHA, "commit": {"committer": {"date": "2026-10-04T12:00:00Z"}}}).encode()
DBD = b"COLUMNS\nint ID\nint<TraitTree::ID> TraitTreeID\n\nBUILD 1.0.0.1\n$id$ID<32>\nTraitTreeID<32>\n"
LICENSE = b"The Unlicense\n\nThis is free and unencumbered software released into the public domain.\n"


def routes(commit=SHA, tables=("TraitNode", "TraitEdge")):
    out = {DBD_COMMIT_URL: COMMIT, DBD_LICENSE_URL.format(commit=commit): LICENSE}
    out |= {dbd_url(commit, t): DBD for t in tables}
    return out


def test_urls_pin_the_commit():
    assert dbd_url(SHA, "TraitNode") == (
        f"https://raw.githubusercontent.com/wowdev/WoWDBDefs/{SHA}/definitions/TraitNode.dbd"
    )
    assert DBD_COMMIT_URL == "https://api.github.com/repos/wowdev/WoWDBDefs/commits/master"


def test_dbd_tables_come_from_decode_rules():
    tables = dbd_tables(RULES)
    assert set(tables) == known_tables(RULES) | {"TraitNodeGroupXTraitNode"}
    assert tables == sorted(tables)


def test_looks_like_dbd():
    assert looks_like_dbd(DBD)
    assert not looks_like_dbd(b"<!DOCTYPE html><html></html>")
    assert not looks_like_dbd(b"404: Not Found")
    assert not looks_like_dbd(b"\xff\xfe")


def test_fetch_pins_commit_and_writes_index(make_deps):
    http = FakeHttp(routes=routes())
    deps = make_deps(http=http)
    res = fetch_dbd(deps, LOCAL_VERSION, ["TraitNode", "TraitEdge"])
    assert res["commit"] == SHA and res["repo"] == "wowdev/WoWDBDefs" and res["version"] == LOCAL_VERSION
    assert [f["table"] for f in res["files"]] == ["TraitNode", "TraitEdge"]
    assert all(not f["from_cache"] for f in res["files"])
    assert (dbd_dir(deps.cache_dir) / SHA / "TraitNode.dbd").read_bytes() == DBD
    index = read_dbd_index(deps.cache_dir)
    assert index is not None and index["commit"] == SHA
    assert (dbd_dir(deps.cache_dir) / DBD_INDEX).is_file()
    assert len(index["files"]["TraitNode"]["sha256"]) == 64
    assert index["license"]["first_line"] == "The Unlicense"
    assert http.calls[0][0] == DBD_COMMIT_URL


def test_second_fetch_downloads_nothing(make_deps):
    http = FakeHttp(routes=routes())
    deps = make_deps(http=http)
    fetch_dbd(deps, LOCAL_VERSION, ["TraitNode", "TraitEdge"])
    calls = len(http.calls)
    res = fetch_dbd(deps, LOCAL_VERSION, ["TraitNode", "TraitEdge"])
    assert len(http.calls) == calls
    assert all(f["from_cache"] for f in res["files"]) and res["commit"] == SHA


def test_explicit_commit_skips_the_commit_request(make_deps):
    http = FakeHttp(routes=routes(OTHER, ("TraitNode",)))
    deps = make_deps(http=http)
    res = fetch_dbd(deps, LOCAL_VERSION, ["TraitNode"], commit=OTHER)
    assert res["commit"] == OTHER
    assert DBD_COMMIT_URL not in [c[0] for c in http.calls]


def test_answer_that_is_not_a_dbd_is_refused(make_deps):
    bad = routes() | {dbd_url(SHA, "TraitEdge"): b"<html>rate limited</html>"}
    deps = make_deps(http=FakeHttp(routes=bad))
    with pytest.raises(FetchFailedError, match="TraitEdge"):
        fetch_dbd(deps, LOCAL_VERSION, ["TraitNode", "TraitEdge"])
    assert not (dbd_dir(deps.cache_dir) / SHA / "TraitEdge.dbd").exists()
    assert (dbd_dir(deps.cache_dir) / SHA / "TraitNode.dbd").is_file()


def test_commit_answer_without_sha_is_refused(make_deps):
    deps = make_deps(http=FakeHttp(routes={DBD_COMMIT_URL: b'{"message": "API rate limit exceeded"}'}))
    with pytest.raises(FetchFailedError):
        fetch_dbd(deps, LOCAL_VERSION, ["TraitNode"])


def test_offline_refuses(make_deps):
    deps = make_deps(http=FakeHttp(routes=routes()), offline=True)
    with pytest.raises(OfflineError):
        fetch_dbd(deps, LOCAL_VERSION, ["TraitNode"])


def test_cli_fetch_dbd(make_deps, capsys):
    tables = dbd_tables(RULES)
    http = FakeHttp(routes=routes(tables=tables))
    deps = make_deps(http=http)
    code = main(["fetch", "--version", LOCAL_VERSION, "--dbd", "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert data["commit"] == SHA and len(data["files"]) == len(tables)
    assert data["provenance"]["game_version"] == LOCAL_VERSION


def test_missing_license_is_noted_not_fatal(make_deps):
    """Relevé réel du 2026-10-05 : LICENSE absent du dépôt (404) ; la licence est notée absente, rien n'échoue."""
    answers = routes() | {DBD_LICENSE_URL.format(commit=SHA): OSError("HTTP Error 404: Not Found")}
    http = FakeHttp(routes=answers)
    deps = make_deps(http=http)
    res = fetch_dbd(deps, LOCAL_VERSION, ["TraitNode"])
    assert res["license"] is not None and res["license"]["status"] == "absent"
    calls = len(http.calls)
    fetch_dbd(deps, LOCAL_VERSION, ["TraitNode"])
    assert len(http.calls) == calls  # la licence absente n'est pas redemandée
