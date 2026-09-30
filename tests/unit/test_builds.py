"""Versions publiées (wago.tools) : parseur tolérant et client HTTP injecté, sans réseau."""

import json
from datetime import UTC, datetime

import pytest
from conftest import FIXTURES, LOCAL_VERSION, PREFIX, PRODUCT, FakeHttp

from forever.pipeline.builds import (
    BUILDS_URL,
    Build,
    BuildsUnavailable,
    fetch_builds,
    latest_build,
    parse_builds,
    version_key,
)
from forever.timefmt import parse_utc


def load(name):
    return json.loads((FIXTURES / "wago" / name).read_text(encoding="utf-8"))


def test_dict_and_list_forms_give_same_builds():
    from_dict = parse_builds(load("builds_fresh.json"), PRODUCT, PREFIX)
    from_list = parse_builds(load("builds_list_form.json"), PRODUCT, PREFIX)
    assert sorted(from_dict, key=lambda b: b.version) == sorted(from_list, key=lambda b: b.version)
    assert {b.version for b in from_dict} == {"1.60.1.70009", "1.60.1.69977"}


def test_prefix_filter_excludes_other_versions_and_products():
    builds = parse_builds(load("builds_other_product.json"), PRODUCT, PREFIX)
    assert builds == []


def test_latest_follows_created_at_not_arrival_order():
    builds = parse_builds(load("builds_stale.json"), PRODUCT, PREFIX)
    assert [b.version for b in builds][-1] != "1.60.1.70150"  # arrivée : 70150 n'est pas le dernier élément
    latest = latest_build(builds)
    assert latest == Build("1.60.1.70150", datetime(2026, 9, 26, 18, 45, tzinfo=UTC))


def test_latest_of_nothing_is_none():
    assert latest_build([]) is None


def test_both_date_formats_are_accepted():
    builds = {b.version: b.created_at for b in parse_builds(load("builds_mixed_dates.json"), PRODUCT, PREFIX)}
    assert builds["1.60.1.69977"] == datetime(2026, 9, 10, 11, 5, tzinfo=UTC)
    assert builds["1.60.1.70009"] == datetime(2026, 9, 24, 15, 32, 10, tzinfo=UTC)  # +02:00 ramené en UTC
    assert builds["1.60.1.69900"] == datetime(2026, 9, 1, 8, 0, tzinfo=UTC)  # sans fuseau : UTC
    assert all(dt.tzinfo is not None for dt in builds.values())


def test_out_of_range_date_is_ignored():
    payload = {PRODUCT: [{"version": "1.60.1.70009", "created_at": "9999-12-31T23:59:59-05:00"}]}
    assert parse_builds(payload, PRODUCT, PREFIX) == []


def test_parse_utc_out_of_range_is_value_error():
    with pytest.raises(ValueError):
        parse_utc("0001-01-01T00:00:00+05:00")


def test_version_key_compares_numerically():
    assert version_key("1.60.1.70150") > version_key("1.60.1.70009")
    assert version_key("1.60.10.1") > version_key("1.60.9.99999")


def test_fetch_uses_wago_url_user_agent_and_timeout():
    http = FakeHttp.fixture("builds_fresh.json")
    payload = fetch_builds(http)
    assert payload == load("builds_fresh.json")
    assert len(http.calls) == 1
    url, headers, timeout = http.calls[0]
    assert url == BUILDS_URL == "https://wago.tools/api/builds"
    assert headers.get("User-Agent")
    assert timeout == 2.0


def test_network_error_becomes_builds_unavailable():
    with pytest.raises(BuildsUnavailable):
        fetch_builds(FakeHttp.failing())


def test_invalid_json_becomes_builds_unavailable():
    with pytest.raises(BuildsUnavailable):
        fetch_builds(FakeHttp(body=b"<html>maintenance</html>"))


# --- list_builds et commande builds (T03) -------------------------------------------------------


def test_list_builds_sorted_by_created_at_desc(make_deps):
    from forever.pipeline.builds import list_builds

    builds = list_builds(make_deps(http=FakeHttp.fixture("builds_mixed_dates.json")), PRODUCT, PREFIX)
    assert [b.version for b in builds] == ["1.60.1.70009", "1.60.1.69977", "1.60.1.69900"]


def test_list_builds_filters_product_and_prefix(make_deps):
    from forever.pipeline.builds import list_builds

    assert list_builds(make_deps(http=FakeHttp.fixture("builds_other_product.json")), PRODUCT, PREFIX) == []


def test_list_builds_offline_makes_no_call(make_deps):
    from forever.errors import OfflineError
    from forever.pipeline.builds import list_builds

    http = FakeHttp.fixture("builds_fresh.json")
    with pytest.raises(OfflineError):
        list_builds(make_deps(http=http, offline=True), PRODUCT, PREFIX)
    assert http.calls == []


def test_builds_unavailable_exits_with_network_code():
    from forever.errors import EXIT_NETWORK

    assert BuildsUnavailable("x").exit_code == EXIT_NETWORK == 5


def builds_with_local():
    """Échantillon des builds publiés où la version la plus récente est celle installée : `forever builds` doit la
    marquer « locale ». La fixture nomme 1.60.1.70009 ; le dépôt suit les versions du jeu (T08a)."""
    payload = json.loads((FIXTURES / "wago" / "builds_mixed_dates.json").read_text(encoding="utf-8"))
    for entry in payload[PRODUCT]:
        if entry["version"] == "1.60.1.70009":
            entry["version"] = LOCAL_VERSION
    return FakeHttp(body=json.dumps(payload).encode("utf-8"))


def test_cli_builds_marks_local_version(capsys, make_deps):
    from forever.cli import main

    code = main(["builds"], make_deps(http=builds_with_local()))
    out = capsys.readouterr().out
    assert code == 0
    local_line = next(line for line in out.splitlines() if LOCAL_VERSION in line)
    assert "locale" in local_line
    assert out.rstrip().splitlines()[-1].startswith("Provenance")


def test_cli_builds_json(capsys, make_deps):
    from forever.cli import main

    code = main(["builds", "--json", "--limit", "2"], make_deps(http=builds_with_local()))
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["local_version"] == LOCAL_VERSION and payload["latest"] == LOCAL_VERSION
    assert [b["version"] for b in payload["builds"]] == [LOCAL_VERSION, "1.60.1.69977"]
    assert payload["builds"][0]["local"] is True and payload["total"] == 3
    assert "provenance" in payload


def test_cli_builds_network_failure_is_code_5(capsys, make_deps):
    from forever.cli import main

    code = main(["builds", "--json"], make_deps(http=FakeHttp.failing()))
    assert code == 5
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "builds_unavailable"


def test_cli_builds_offline(capsys, make_deps):
    from forever.cli import main

    http = FakeHttp.fixture("builds_fresh.json")
    code = main(["builds", "--offline", "--json"], make_deps(http=http))
    assert code == 5 and http.calls == []
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "offline"
