"""Fraîcheur : les quatre statuts sans réseau (critère 2), priorités, cache 6 h."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from conftest import FIXTURES, LOCAL_VERSION, NOW, PREFIX, PRODUCT, FakeHttp

from forever.cli import main
from forever.freshness import check_freshness, classify, freshness_for_version
from forever.pipeline.builds import Build


def check(deps, *, allow_network=True):
    return check_freshness(deps, LOCAL_VERSION, product=PRODUCT, prefix=PREFIX, allow_network=allow_network)


# --- Critère 2 : les quatre statuts ---------------------------------------------------------------


def fresh_http():
    """Réponse où la dernière version publiée est celle installée. La fixture nomme 1.60.1.70009 ; le dépôt suit les
    versions du jeu (T08a), la fraîcheur se juge donc contre la version installée, pas contre une chaîne figée."""
    payload = json.loads((FIXTURES / "wago" / "builds_fresh.json").read_text(encoding="utf-8"))
    for entry in payload["wow_classic_beta"]:
        if entry["version"] == "1.60.1.70009":
            entry["version"] = LOCAL_VERSION
    return FakeHttp(body=json.dumps(payload).encode("utf-8"))


def test_fresh(make_deps):
    r = check(make_deps(http=fresh_http()))
    assert r["freshness"] == "fresh"
    assert r["source"] == "network"
    assert r["latest_version"] == LOCAL_VERSION


def test_stale(make_deps):
    r = check(make_deps(http=FakeHttp.fixture("builds_stale.json")))
    assert r["freshness"] == "stale"
    assert r["latest_version"] == "1.60.1.70150"
    assert any("1.60.1.70150" in a for a in r["assumptions"])


def test_unknown_when_network_fails_and_no_cache(make_deps):
    r = check(make_deps(http=FakeHttp.failing()))
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"
    assert r["checked_at"] is None and r["age_hours"] is None


def test_silent(make_deps):
    r = check(make_deps(http=FakeHttp.fixture("builds_silent.json")))
    assert r["freshness"] == "silent"


# --- Priorités et bornes -------------------------------------------------------------------------


def test_exactly_fourteen_days_is_fresh():
    latest = Build(LOCAL_VERSION, NOW - timedelta(days=14))
    assert classify(LOCAL_VERSION, latest, NOW, timedelta(days=14)) == "fresh"
    older = Build(LOCAL_VERSION, NOW - timedelta(days=14, seconds=1))
    assert classify(LOCAL_VERSION, older, NOW, timedelta(days=14)) == "silent"


def test_newer_version_wins_over_silence():
    latest = Build("1.60.1.70150", NOW - timedelta(days=30))
    assert classify(LOCAL_VERSION, latest, NOW, timedelta(days=14)) == "stale"


def test_no_prefixed_version_is_silent(make_deps):
    assert classify(LOCAL_VERSION, None, NOW, timedelta(days=14)) == "silent"
    r = check(make_deps(http=FakeHttp.fixture("builds_other_product.json")))
    assert r["freshness"] == "silent"


# --- Cache ---------------------------------------------------------------------------------------


def test_recent_cache_avoids_network(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    check(make_deps(http=fresh_http(), now=NOW - timedelta(hours=2), cache_dir=cache))
    http = FakeHttp.fixture("builds_stale.json")
    r = check(make_deps(http=http, cache_dir=cache))
    assert http.calls == []
    assert r["freshness"] == "fresh"
    assert r["source"] == "cache"


def test_old_cache_triggers_network(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    check(make_deps(http=fresh_http(), now=NOW - timedelta(hours=7), cache_dir=cache))
    http = FakeHttp.fixture("builds_stale.json")
    r = check(make_deps(http=http, cache_dir=cache))
    assert len(http.calls) == 1
    assert r["freshness"] == "stale"
    assert r["source"] == "network"


def test_network_failure_with_cache_is_unknown_with_last_state(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    check(make_deps(http=fresh_http(), now=NOW - timedelta(hours=9), cache_dir=cache))
    r = check(make_deps(http=FakeHttp.failing(), cache_dir=cache))
    assert r["freshness"] == "unknown"
    assert r["checked_at"] == "2026-09-27T03:00:00Z"
    assert r["age_hours"] == 9.0
    assert r["latest_version"] == LOCAL_VERSION
    assert any("fresh" in a and "9 h" in a for a in r["assumptions"])
    # le cache garde sa dernière observation réussie
    again = check(make_deps(http=FakeHttp.failing(), cache_dir=cache), allow_network=False)
    assert again["checked_at"] == "2026-09-27T03:00:00Z"


def test_tool_without_network_reuses_old_cache_with_assumption(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    check(make_deps(http=fresh_http(), now=NOW - timedelta(hours=9), cache_dir=cache))
    http = FakeHttp.fixture("builds_stale.json")
    r = check(make_deps(http=http, cache_dir=cache), allow_network=False)
    assert http.calls == []
    assert r["freshness"] == "fresh"
    assert r["source"] == "cache"
    assert r["age_hours"] == 9.0
    assert any("9 h" in a and "forever status" in a for a in r["assumptions"])


def test_tool_without_network_reclassifies_cache_with_now(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    # observation du 2026-09-27 : 70009 publiée le 2026-09-24 ; relue 20 jours plus tard
    check(make_deps(http=fresh_http(), cache_dir=cache))
    later = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
    r = check(make_deps(now=later, cache_dir=cache), allow_network=False)
    assert r["freshness"] == "silent"


def test_tool_without_network_and_without_cache_is_unknown(make_deps):
    http = fresh_http()
    r = check(make_deps(http=http), allow_network=False)
    assert http.calls == []
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"


def test_offline_deps_never_call_network(make_deps):
    http = fresh_http()
    r = check(make_deps(http=http, offline=True))
    assert http.calls == []
    assert r["freshness"] == "unknown"


def test_corrupt_cache_is_ignored(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    cache.mkdir()
    (cache / "status.json").write_text("{pas du json", encoding="utf-8")
    r = check(make_deps(http=fresh_http(), cache_dir=cache))
    assert r["freshness"] == "fresh"


# --- Cache daté dans le futur : traité comme absent ------------------------------------------------


def future_cache(make_deps, cache):
    """Cache écrit par une horloge en avance d'un jour sur NOW."""
    check(make_deps(http=fresh_http(), now=NOW + timedelta(days=1), cache_dir=cache))


def write_cache(cache, fetched_at, version=LOCAL_VERSION):
    cache.mkdir(parents=True, exist_ok=True)
    latest = {"version": version, "created_at": "2026-09-24T22:02:03Z"}
    data = {"schema_version": 1, "product": PRODUCT, "fetched_at": fetched_at, "latest": latest}
    (cache / "status.json").write_text(json.dumps(data), encoding="utf-8")


def test_future_cache_is_ignored_without_network(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    future_cache(make_deps, cache)
    r = check(make_deps(cache_dir=cache), allow_network=False)
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"
    assert r["checked_at"] is None and r["age_hours"] is None and r["latest_version"] is None
    assert any("futur" in a for a in r["assumptions"])


def test_future_cache_is_ignored_when_network_fails(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    future_cache(make_deps, cache)
    r = check(make_deps(http=FakeHttp.failing(), cache_dir=cache))
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"
    assert any("futur" in a for a in r["assumptions"])


def test_future_cache_does_not_skip_network_check(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    future_cache(make_deps, cache)
    http = FakeHttp.fixture("builds_stale.json")
    r = check(make_deps(http=http, cache_dir=cache))
    assert len(http.calls) == 1
    assert r["freshness"] == "stale"
    assert r["source"] == "network"
    # le cache fautif est remplacé par l'observation du moment
    assert check(make_deps(cache_dir=cache), allow_network=False)["checked_at"] == "2026-09-27T12:00:00Z"


@pytest.mark.parametrize(
    "fetched_at", ["9999-12-31T23:59:59Z", "9999-12-31T23:59:59-05:00", "0001-01-01T00:00:00+05:00"]
)
@pytest.mark.parametrize("network", [False, True], ids=["sans-reseau", "reseau-en-panne"])
def test_extreme_cache_dates_do_not_crash(make_deps, tmp_path, fetched_at, network):
    cache = tmp_path / "shared-cache"
    write_cache(cache, fetched_at)
    r = check(make_deps(http=FakeHttp.failing(), cache_dir=cache), allow_network=network)
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"


@pytest.mark.parametrize("version", ["latest", 70009, None])
def test_cache_with_invalid_version_is_ignored(make_deps, tmp_path, version):
    cache = tmp_path / "shared-cache"
    write_cache(cache, "2026-09-27T10:00:00Z", version=version)
    r = check(make_deps(cache_dir=cache), allow_network=False)
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"


def test_status_offline_with_future_cache(capsys, make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    future_cache(make_deps, cache)
    assert main(["status", "--offline", "--json"], make_deps(cache_dir=cache)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["freshness"]["freshness"] == "unknown"
    assert data["provenance"]["freshness"] == "unknown"
    assert any("futur" in a for a in data["provenance"]["assumptions"])


def test_freshness_for_version_reads_product_from_sources(make_deps):
    r = freshness_for_version(make_deps(http=FakeHttp.fixture("builds_stale.json")), LOCAL_VERSION, allow_network=True)
    assert r["freshness"] == "stale"
