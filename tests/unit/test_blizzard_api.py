"""Sonde de l'API Blizzard (T08b, point 10, décision 149) : espaces de noms de Forever seulement (jamais retail, Classic
Era, Classic ni TBC), jeton par *client credentials*, clés jamais affichées, couverture (Game Data, Profile, hôtel des
ventes, PvP) et corps d'issue quand un espace répond. Réseau simulé : jeton et réponses inventés."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, FakeHttp, read_json

from forever.cli import main
from forever.errors import InvalidArgumentError, OfflineError
from forever.pipeline.blizzard_api import (
    TOKEN_URL,
    candidate_namespaces,
    is_forever_namespace,
    load_keys,
    probe,
    probe_issue_body,
)

SECRET = "secret-de-test-0123"
CLIENT = "client-de-test"
TOKEN = "jeton-de-test-abcdef"
KEYS = {"BLIZZARD_CLIENT_ID": CLIENT, "BLIZZARD_CLIENT_SECRET": SECRET}
ITEM = read_json(DATA_DIR / LOCAL_VERSION / "pvp_items.json")["trinkets"][0]["item_id"]


class FakePost:
    def __init__(self, body: bytes = json.dumps({"access_token": TOKEN, "expires_in": 86399}).encode()):
        self.body = body
        self.calls = []

    def __call__(self, url, headers, data, timeout):
        self.calls.append((url, dict(headers), data))
        return self.body


def no_sleep(_s: float) -> None:
    pass


def test_candidates_are_forever_namespaces_only():
    for region in ("eu", "us"):
        names = candidate_namespaces(region)
        assert names and all(is_forever_namespace(n) for n in names)
    for other in (
        "static-eu",
        "dynamic-us",
        "static-classic1x-eu",
        "static-classic-eu",
        "dynamic-classicann-us",
        "static-tbc-eu",
    ):
        assert not is_forever_namespace(other), other


def test_probe_reports_coverage_and_never_leaks_keys(make_deps):
    static = candidate_namespaces("eu")[0]
    ok = f"https://eu.api.blizzard.com/data/wow/playable-class/index?namespace={static}&locale=en_US"
    http = FakeHttp(exc=OSError("404"), routes={ok: b'{"classes": []}'})
    post = FakePost()
    result = probe(make_deps(http=http), KEYS, regions=("eu",), http_post=post, sleep=no_sleep)
    assert post.calls[0][0] == TOKEN_URL and post.calls[0][2] == b"grant_type=client_credentials"
    assert all(f"namespace={n}" in c[0] for c in http.calls for n in [c[0].split("namespace=")[1].split("&")[0]])
    assert all(is_forever_namespace(c[0].split("namespace=")[1].split("&")[0]) for c in http.calls)
    assert all(c[1].get("Authorization") == f"Bearer {TOKEN}" for c in http.calls)
    assert any(f"/data/wow/item/{ITEM}?" in c[0] for c in http.calls)
    assert result["responding"] == [static]
    assert result["coverage"]["game_data"] is True and result["coverage"]["auction_house"] is False
    text = json.dumps(result, ensure_ascii=False) + probe_issue_body(result)
    assert SECRET not in text and TOKEN not in text and CLIENT not in text


def test_nothing_responding_needs_no_issue(make_deps):
    result = probe(
        make_deps(http=FakeHttp(exc=OSError("404"))), KEYS, regions=("eu",), http_post=FakePost(), sleep=no_sleep
    )
    assert result["responding"] == [] and result["issue_needed"] is False


def test_missing_keys_make_no_call(make_deps):
    http, post = FakeHttp(body=b"{}"), FakePost()
    with pytest.raises(InvalidArgumentError) as info:
        probe(make_deps(http=http), {}, regions=("eu",), http_post=post, sleep=no_sleep)
    assert http.calls == [] and post.calls == []
    assert "BLIZZARD_CLIENT_ID" in info.value.message


def test_offline_makes_no_call(make_deps):
    post = FakePost()
    with pytest.raises(OfflineError):
        probe(make_deps(offline=True), KEYS, regions=("eu",), http_post=post, sleep=no_sleep)
    assert post.calls == []


def test_token_failure_message_hides_the_keys(make_deps):
    def failing(url, headers, data, timeout):
        raise OSError(f"401 pour {url}")

    with pytest.raises(Exception) as info:
        probe(make_deps(), KEYS, regions=("eu",), http_post=failing, sleep=no_sleep)
    assert SECRET not in str(info.value) and CLIENT not in str(info.value)


def test_keys_from_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        f'# commentaire\nBLIZZARD_CLIENT_ID={CLIENT}\nBLIZZARD_CLIENT_SECRET="{SECRET}"\nAUTRE=1\n', encoding="utf-8"
    )
    assert load_keys({}, env) == KEYS
    assert (
        load_keys({"BLIZZARD_CLIENT_ID": "env", "BLIZZARD_CLIENT_SECRET": "env2"}, env)["BLIZZARD_CLIENT_ID"] == "env"
    )


def test_issue_body_names_the_coverage(make_deps):
    static = candidate_namespaces("eu")[0]
    ok = f"https://eu.api.blizzard.com/data/wow/playable-class/index?namespace={static}&locale=en_US"
    result = probe(
        make_deps(http=FakeHttp(exc=OSError("404"), routes={ok: b"{}"})),
        KEYS,
        regions=("eu",),
        http_post=FakePost(),
        sleep=no_sleep,
    )
    body = probe_issue_body(result)
    assert result["issue_needed"] is True
    for word in ("Game Data", "Profile", "hôtel des ventes", "PvP", "EC1", static):
        assert word in body


def test_cli_probe_without_keys_is_a_usage_error(make_deps, capsys, monkeypatch):
    monkeypatch.delenv("BLIZZARD_CLIENT_ID", raising=False)
    monkeypatch.delenv("BLIZZARD_CLIENT_SECRET", raising=False)
    code = main(["api", "probe", "--json", "--env-file", "absent.env"], make_deps())
    assert code == 2
