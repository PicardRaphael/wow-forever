"""Fraîcheur : les quatre statuts sans réseau (critère 2), priorités, cache 6 h."""

from datetime import UTC, datetime, timedelta

from conftest import LOCAL_VERSION, NOW, PREFIX, PRODUCT, FakeHttp

from forever.freshness import check_freshness, classify, freshness_for_version
from forever.pipeline.builds import Build


def check(deps, *, allow_network=True):
    return check_freshness(deps, LOCAL_VERSION, product=PRODUCT, prefix=PREFIX, allow_network=allow_network)


# --- Critère 2 : les quatre statuts ---------------------------------------------------------------


def test_fresh(make_deps):
    r = check(make_deps(http=FakeHttp.fixture("builds_fresh.json")))
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
    check(make_deps(http=FakeHttp.fixture("builds_fresh.json"), now=NOW - timedelta(hours=2), cache_dir=cache))
    http = FakeHttp.fixture("builds_stale.json")
    r = check(make_deps(http=http, cache_dir=cache))
    assert http.calls == []
    assert r["freshness"] == "fresh"
    assert r["source"] == "cache"


def test_old_cache_triggers_network(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    check(make_deps(http=FakeHttp.fixture("builds_fresh.json"), now=NOW - timedelta(hours=7), cache_dir=cache))
    http = FakeHttp.fixture("builds_stale.json")
    r = check(make_deps(http=http, cache_dir=cache))
    assert len(http.calls) == 1
    assert r["freshness"] == "stale"
    assert r["source"] == "network"


def test_network_failure_with_cache_is_unknown_with_last_state(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    check(make_deps(http=FakeHttp.fixture("builds_fresh.json"), now=NOW - timedelta(hours=9), cache_dir=cache))
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
    check(make_deps(http=FakeHttp.fixture("builds_fresh.json"), now=NOW - timedelta(hours=9), cache_dir=cache))
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
    check(make_deps(http=FakeHttp.fixture("builds_fresh.json"), cache_dir=cache))
    later = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
    r = check(make_deps(now=later, cache_dir=cache), allow_network=False)
    assert r["freshness"] == "silent"


def test_tool_without_network_and_without_cache_is_unknown(make_deps):
    http = FakeHttp.fixture("builds_fresh.json")
    r = check(make_deps(http=http), allow_network=False)
    assert http.calls == []
    assert r["freshness"] == "unknown"
    assert r["source"] == "none"


def test_offline_deps_never_call_network(make_deps):
    http = FakeHttp.fixture("builds_fresh.json")
    r = check(make_deps(http=http, offline=True))
    assert http.calls == []
    assert r["freshness"] == "unknown"


def test_corrupt_cache_is_ignored(make_deps, tmp_path):
    cache = tmp_path / "shared-cache"
    cache.mkdir()
    (cache / "status.json").write_text("{pas du json", encoding="utf-8")
    r = check(make_deps(http=FakeHttp.fixture("builds_fresh.json"), cache_dir=cache))
    assert r["freshness"] == "fresh"


def test_freshness_for_version_reads_product_from_sources(make_deps):
    r = freshness_for_version(make_deps(http=FakeHttp.fixture("builds_stale.json")), LOCAL_VERSION, allow_network=True)
    assert r["freshness"] == "stale"
