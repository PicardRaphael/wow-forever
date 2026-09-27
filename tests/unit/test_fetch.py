"""Téléchargement des tables du client (wago.tools) : URL, cache, empreintes, erreurs ; réseau simulé."""

import hashlib
import json

import pytest
from conftest import FIXTURES, LOCAL_VERSION, FakeHttp

from forever.cli import main
from forever.config import FETCH_TIMEOUT
from forever.errors import EXIT_NETWORK, FetchFailedError, InvalidArgumentError, OfflineError
from forever.pipeline.fetch import fetch_tables, index_path, table_path, table_url

FETCH = FIXTURES / "wago" / "fetch"
SPELLNAME = (FETCH / "SpellName_min.csv").read_bytes()
SPELLEFFECT = (FETCH / "SpellEffect_min.csv").read_bytes()
URL_NAME = table_url("SpellName", LOCAL_VERSION, None)
URL_EFFECT = table_url("SpellEffect", LOCAL_VERSION, None)


def routes(**extra):
    return {URL_NAME: SPELLNAME, URL_EFFECT: SPELLEFFECT, **extra}


def test_table_url_form():
    assert URL_NAME == "https://wago.tools/db2/SpellName/csv?build=1.60.1.70009"


def test_default_locale_needs_no_parameter():
    assert table_url("SpellName", LOCAL_VERSION, "enUS") == URL_NAME


def test_other_locale_is_in_url():
    url = table_url("SpellName", LOCAL_VERSION, "frFR")
    assert url.startswith(URL_NAME) and "frFR" in url and url != URL_NAME


def test_fetch_writes_csv_and_index(make_deps):
    deps = make_deps(http=FakeHttp(routes=routes()))
    result = fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    path = table_path(deps.cache_dir, LOCAL_VERSION, "enUS", "SpellName")
    assert path.read_bytes() == SPELLNAME  # octets tels que reçus (fins de ligne comprises)
    assert result == [
        {
            "table": "SpellName",
            "locale": "enUS",
            "url": URL_NAME,
            "sha256": hashlib.sha256(SPELLNAME).hexdigest(),
            "bytes": len(SPELLNAME),
            "fetched_at": "2026-09-27T12:00:00Z",
            "from_cache": False,
        }
    ]
    index = json.loads(index_path(deps.cache_dir, LOCAL_VERSION).read_text(encoding="utf-8"))
    assert index["version"] == LOCAL_VERSION
    entry = index["tables"]["enUS/SpellName"]
    assert entry["sha256"] == hashlib.sha256(SPELLNAME).hexdigest()
    assert entry["url"] == URL_NAME and entry["bytes"] == len(SPELLNAME)


def test_second_fetch_is_served_from_cache(make_deps):
    http = FakeHttp(routes=routes())
    deps = make_deps(http=http)
    fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    again = fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    assert len(http.calls) == 1
    assert again[0]["from_cache"] is True
    assert again[0]["sha256"] == hashlib.sha256(SPELLNAME).hexdigest()


def test_refresh_downloads_again(make_deps):
    http = FakeHttp(routes=routes())
    deps = make_deps(http=http)
    fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    again = fetch_tables(deps, LOCAL_VERSION, ["SpellName"], refresh=True)
    assert len(http.calls) == 2 and again[0]["from_cache"] is False


def test_altered_cache_is_downloaded_again(make_deps):
    http = FakeHttp(routes=routes())
    deps = make_deps(http=http)
    fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    table_path(deps.cache_dir, LOCAL_VERSION, "enUS", "SpellName").write_bytes(b"ID,Name_lang\n1,Altere\n")
    again = fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    assert len(http.calls) == 2 and again[0]["from_cache"] is False
    assert table_path(deps.cache_dir, LOCAL_VERSION, "enUS", "SpellName").read_bytes() == SPELLNAME


def test_locale_goes_to_its_own_folder(make_deps):
    url_fr = table_url("SpellName", LOCAL_VERSION, "frFR")
    deps = make_deps(http=FakeHttp(routes={url_fr: SPELLNAME}))
    result = fetch_tables(deps, LOCAL_VERSION, ["SpellName"], locales=("frFR",))
    assert result[0]["locale"] == "frFR" and result[0]["url"] == url_fr
    assert table_path(deps.cache_dir, LOCAL_VERSION, "frFR", "SpellName").is_file()


@pytest.mark.parametrize("name", ["error.html", "error.json"])
def test_non_csv_answer_is_refused_and_nothing_written(make_deps, name):
    deps = make_deps(http=FakeHttp(routes={URL_NAME: (FETCH / name).read_bytes()}))
    with pytest.raises(FetchFailedError) as info:
        fetch_tables(deps, LOCAL_VERSION, ["SpellName"])
    assert info.value.code == "fetch_failed" and "SpellName" in info.value.message
    assert not table_path(deps.cache_dir, LOCAL_VERSION, "enUS", "SpellName").exists()


def test_network_error_is_fetch_failed(make_deps):
    deps = make_deps(http=FakeHttp(routes={URL_NAME: OSError("coupure simulée")}))
    with pytest.raises(FetchFailedError):
        fetch_tables(deps, LOCAL_VERSION, ["SpellName"])


def test_partial_failure_keeps_downloaded_tables(make_deps):
    deps = make_deps(http=FakeHttp(routes=routes(**{URL_EFFECT: OSError("404 simulé")})))
    with pytest.raises(FetchFailedError) as info:
        fetch_tables(deps, LOCAL_VERSION, ["SpellName", "SpellEffect"])
    assert "SpellEffect" in info.value.message and "SpellName" not in info.value.message
    assert table_path(deps.cache_dir, LOCAL_VERSION, "enUS", "SpellName").read_bytes() == SPELLNAME
    index = json.loads(index_path(deps.cache_dir, LOCAL_VERSION).read_text(encoding="utf-8"))
    assert list(index["tables"]) == ["enUS/SpellName"]


def test_offline_makes_no_call(make_deps):
    http = FakeHttp(routes=routes())
    with pytest.raises(OfflineError) as info:
        fetch_tables(make_deps(http=http, offline=True), LOCAL_VERSION, ["SpellName"])
    assert http.calls == [] and info.value.code == "offline"


@pytest.mark.parametrize("version", ["1.60.x", "1.60.1", "../1.60.1.70009"])
def test_malformed_version_is_invalid_argument(make_deps, version):
    http = FakeHttp(routes=routes())
    with pytest.raises(InvalidArgumentError):
        fetch_tables(make_deps(http=http), version, ["SpellName"])
    assert http.calls == []


@pytest.mark.parametrize("table", ["../SpellName", "Spell Name", ""])
def test_malformed_table_is_invalid_argument(make_deps, table):
    http = FakeHttp(routes=routes())
    with pytest.raises(InvalidArgumentError):
        fetch_tables(make_deps(http=http), LOCAL_VERSION, [table])
    assert http.calls == []


def test_timeout_and_user_agent(make_deps):
    http = FakeHttp(routes=routes())
    fetch_tables(make_deps(http=http), LOCAL_VERSION, ["SpellName"])
    _, headers, timeout = http.calls[0]
    assert timeout == FETCH_TIMEOUT == 30.0
    assert headers.get("User-Agent")


def test_network_errors_exit_with_code_5():
    assert EXIT_NETWORK == 5
    assert OfflineError().exit_code == FetchFailedError("x").exit_code == EXIT_NETWORK


# --- Commande ------------------------------------------------------------------------------------


def test_cli_fetch_json(capsys, make_deps):
    deps = make_deps(http=FakeHttp(routes=routes()))
    code = main(["fetch", "--version", LOCAL_VERSION, "--tables", "SpellName,SpellEffect", "--json"], deps)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert [t["table"] for t in payload["tables"]] == ["SpellName", "SpellEffect"]
    assert payload["version"] == LOCAL_VERSION and payload["provenance"]["generated_at"] == "2026-09-27T12:00:00Z"


def test_cli_fetch_text(capsys, make_deps):
    deps = make_deps(http=FakeHttp(routes=routes()))
    code = main(["fetch", "--version", LOCAL_VERSION, "--tables", "SpellName"], deps)
    out = capsys.readouterr().out
    assert code == 0
    assert "SpellName" in out and out.rstrip().splitlines()[-1].startswith("Provenance")


def test_cli_fetch_failure_is_code_5(capsys, make_deps):
    deps = make_deps(http=FakeHttp.failing())
    code = main(["fetch", "--version", LOCAL_VERSION, "--tables", "SpellName", "--json"], deps)
    assert code == 5
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "fetch_failed"


def test_cli_fetch_offline_flag(capsys, make_deps):
    http = FakeHttp(routes=routes())
    code = main(
        ["fetch", "--version", LOCAL_VERSION, "--tables", "SpellName", "--offline", "--json"], make_deps(http=http)
    )
    assert code == 5 and http.calls == []
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "offline"


def test_cli_fetch_without_tables_needs_decode_rules(capsys, make_deps, data_copy):
    # sans --tables, la liste vient de decode_rules.json de la version locale la plus récente
    rules = data_copy / LOCAL_VERSION / "decode_rules.json"
    rules.unlink(missing_ok=True)
    http = FakeHttp(routes=routes())
    code = main(["fetch", "--version", LOCAL_VERSION, "--json"], make_deps(http=http, data_dir=data_copy))
    assert code == 2 and http.calls == []
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "invalid_argument"


def test_cli_fetch_locale_option(capsys, make_deps):
    url_fr = table_url("SpellName", LOCAL_VERSION, "frFR")
    deps = make_deps(http=FakeHttp(routes={url_fr: SPELLNAME}))
    code = main(["fetch", "--version", LOCAL_VERSION, "--tables", "SpellName", "--locale", "frFR", "--json"], deps)
    assert code == 0
    assert json.loads(capsys.readouterr().out)["tables"][0]["locale"] == "frFR"
