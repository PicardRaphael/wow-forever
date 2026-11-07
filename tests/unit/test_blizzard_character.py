"""Fiche d'un personnage par l'API Blizzard (EC1a, décision 304) : espace `profile-forever-<région>` seulement,
personnage sans royaume (`nom-surnom` en minuscules), équipement rangé par emplacement du jeu, clés jamais affichées,
personnage absent expliqué (niveau 10, déconnexion), écriture dans le profil sous la source `api`. Réseau simulé :
réponses inventées (`tests/fixtures/blizzard_api/`)."""

import json

import pytest
from conftest import FIXTURES, FakeHttp

from forever import profile
from forever.cli import main
from forever.errors import FetchFailedError, InvalidArgumentError, OfflineError
from forever.pipeline import blizzard_api
from forever.pipeline.blizzard_api import TOKEN_URL, character_slug, fetch_character

SECRET = "secret-de-test-0123"
CLIENT = "client-de-test"
TOKEN = "jeton-de-test-abcdef"
KEYS = {"BLIZZARD_CLIENT_ID": CLIENT, "BLIZZARD_CLIENT_SECRET": SECRET}
HOST = "https://eu.api.blizzard.com/profile/wow/character/judy-testeuse"
QUERY = "?namespace=profile-forever-eu&locale=fr_FR"
PROFILE = (FIXTURES / "blizzard_api" / "character_profile.json").read_bytes()
EQUIPMENT = (FIXTURES / "blizzard_api" / "character_equipment.json").read_bytes()
ROUTES = {f"{HOST}{QUERY}": PROFILE, f"{HOST}/equipment{QUERY}": EQUIPMENT}


class FakePost:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, data, timeout):
        self.calls.append((url, dict(headers), data))
        return json.dumps({"access_token": TOKEN}).encode()


def test_slug_is_name_and_surname_in_lowercase():
    assert character_slug("Rose-Krypto") == "rose-krypto"
    assert character_slug("Rose Krypto") == "rose-krypto"
    assert character_slug(" judy-TESTEUSE ") == "judy-testeuse"
    for bad in ("Rose", "", "rose-krypto/../x", "a-b-c"):
        with pytest.raises(InvalidArgumentError):
            character_slug(bad)


def test_fetch_reads_profile_and_equipment_of_forever_only(make_deps):
    http, post = FakeHttp(exc=OSError("404"), routes=ROUTES), FakePost()
    result = fetch_character(make_deps(http=http), KEYS, "Judy-Testeuse", region="eu", http_post=post)
    assert post.calls[0][0] == TOKEN_URL
    assert [c[0] for c in http.calls] == [f"{HOST}{QUERY}", f"{HOST}/equipment{QUERY}"]
    assert all(c[1]["Authorization"] == f"Bearer {TOKEN}" for c in http.calls)
    assert result["namespace"] == "profile-forever-eu" and result["slug"] == "judy-testeuse"
    c = result["character"]
    assert (c["name"], c["surname"], c["level"], c["experience"]) == ("Judy", "Testeuse", 20, 1651)
    assert (c["class"], c["race"], c["faction"], c["ruleset"]) == ("Mage", "Gnome", "Alliance", "JcJ")
    assert c["last_login"] == "2026-11-07T09:35:12Z"
    gear = result["gear"]
    assert sorted(gear) == ["11", "16", "18", "5"]  # emplacements du jeu : torse, doigt 1, main droite, distance
    assert gear["5"] == {
        "item": 900001,
        "enchant": 4242,
        "gems": [],
        "suffix": 0,
        "unique": 0,
        "name": "Robe de test",
        "quality": "RARE",
        "item_level": 23,
        "stats": ["+10 Intelligence"],
    }
    assert gear["16"]["suffix"] == 77 and gear["11"]["enchant"] == 0
    text = json.dumps(result, ensure_ascii=False)
    assert SECRET not in text and TOKEN not in text and CLIENT not in text


def test_absent_character_is_explained(make_deps):
    http = FakeHttp(exc=OSError("HTTP Error 404: Not Found"))
    with pytest.raises(FetchFailedError) as info:
        fetch_character(make_deps(http=http), KEYS, "Judy-Testeuse", region="eu", http_post=FakePost())
    hint = info.value.message + " " + info.value.action
    assert "niveau 10" in hint and "déconnexion" in hint
    assert TOKEN not in hint


def test_offline_and_missing_keys_make_no_call(make_deps):
    post = FakePost()
    with pytest.raises(OfflineError):
        fetch_character(make_deps(offline=True), KEYS, "Judy-Testeuse", http_post=post)
    with pytest.raises(InvalidArgumentError):
        fetch_character(make_deps(), {}, "Judy-Testeuse", http_post=post)
    assert post.calls == []


def test_unknown_region_is_refused(make_deps):
    with pytest.raises(InvalidArgumentError):
        fetch_character(make_deps(), KEYS, "Judy-Testeuse", region="cn", http_post=FakePost())


def test_cli_character_shows_and_saves_to_profile(make_deps, capsys, monkeypatch):
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", CLIENT)
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", SECRET)
    monkeypatch.setattr(blizzard_api, "_default_post", lambda: FakePost())
    deps = make_deps(http=FakeHttp(exc=OSError("404"), routes=ROUTES))
    code = main(["api", "character", "Judy-Testeuse", "--save", "--json"], deps)
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["character"]["level"] == 20 and "provenance" in out and out["saved"] == "Judy"
    doc = profile.load_profile(deps.profile_path)
    judy = doc["characters"]["Judy"]
    assert judy["gear"]["source"] == "api" and judy["gear"]["value"]["5"]["item"] == 900001
    assert judy["level"]["value"] == 20 and judy["level"]["at"] == "2026-11-07T09:35:12Z"
    assert judy["class"]["value"] == "Mage"
    text = deps.profile_path.read_text(encoding="utf-8")
    assert SECRET not in text and TOKEN not in text


def test_cli_character_without_save_writes_nothing(make_deps, capsys, monkeypatch):
    monkeypatch.setenv("BLIZZARD_CLIENT_ID", CLIENT)
    monkeypatch.setenv("BLIZZARD_CLIENT_SECRET", SECRET)
    monkeypatch.setattr(blizzard_api, "_default_post", lambda: FakePost())
    deps = make_deps(http=FakeHttp(exc=OSError("404"), routes=ROUTES))
    assert main(["api", "character", "Judy-Testeuse"], deps) == 0
    shown = capsys.readouterr().out
    assert "Robe de test" in shown and "niveau 20" in shown
    assert not deps.profile_path.exists()
