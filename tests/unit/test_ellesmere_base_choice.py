"""Profil de base EllesmereUI choisi par personnage (EX1, suite, décision 269) : gardé dans le profil forever
(`ellesmere_base`), choisi une fois par `forever profile set <nom> --ellesmere-base <profil>` ou en jeu par
`/fb base <profil>` (contexte `eui_base`, écrit au profil au clic sur « Exports ») ; le bouton Exports et
`forever export ellesmere` partent de ce profil, sinon du profil actif d'EllesmereUI, en le disant.

Valeurs : sauvegarde synthétique `tests/fixtures/exports/ellesmere_base.lua` (profils « Base », actif, et « Autre »),
contexte réel `tests/fixtures/bridge/contexts/mage19.txt`."""

import json
import shutil

import pytest
from conftest import FIXTURES

from forever.bridge.exports import exports_reply
from forever.bridge.record import CONTEXT_KEYS
from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.exports.ellesmere import ellesmere_export
from forever.profile import read_profile, set_character

CONTEXT = dict(
    line.split("=", 1)
    for line in (FIXTURES / "bridge" / "contexts" / "mage19.txt").read_text(encoding="utf-8").split("\n")
    if "=" in line
)
WHO, REALM = CONTEXT["name"], CONTEXT["realm"]


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    sv = root / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    shutil.copy(FIXTURES / "exports" / "ellesmere_base.lua", sv / "EllesmereUI.lua")
    return root


@pytest.fixture
def deps(wow, make_deps):
    return make_deps(wow_dir=wow)


def eui_line(text):
    return next(line for line in text.splitlines() if "EllesmereUI" in line)


def test_base_is_kept_per_character_in_the_profile(deps):
    set_character(deps, WHO, cls="Mage", ellesmere_base="Autre")
    set_character(deps, "Bob", cls="Hunter")
    assert read_profile(deps, WHO)["character"]["ellesmere_base"] == "Autre"
    assert read_profile(deps, "Bob")["character"]["ellesmere_base"] is None


def test_export_starts_from_the_character_base(deps):
    set_character(deps, WHO, cls="Mage", ellesmere_base="Autre")
    doc = ellesmere_export(deps, WHO, REALM, "Mage", 19, "dps")
    assert doc["base"]["name"] == "Autre"
    assert any("Autre" in a for a in doc["provenance"]["assumptions"])


def test_explicit_base_wins_over_the_profile(deps):
    set_character(deps, WHO, cls="Mage", ellesmere_base="Autre")
    assert ellesmere_export(deps, WHO, REALM, "Mage", 19, "dps", base_name="Base")["base"]["name"] == "Base"


def test_without_choice_the_active_profile_is_used_and_said(deps):
    doc = ellesmere_export(deps, WHO, REALM, "Mage", 19, "dps")
    assert doc["base"]["name"] == "Base"
    assert any("profil actif" in a and "--ellesmere-base" in a for a in doc["provenance"]["assumptions"])


def test_unknown_base_in_the_profile_is_refused_with_the_list(deps):
    set_character(deps, WHO, cls="Mage", ellesmere_base="Inconnu")
    with pytest.raises(InvalidArgumentError) as err:
        ellesmere_export(deps, WHO, REALM, "Mage", 19, "dps")
    assert "Inconnu" in err.value.message and "Autre" in err.value.action


def test_context_key_is_part_of_the_protocol():
    assert "eui_base" in CONTEXT_KEYS


def test_exports_button_uses_the_base_chosen_in_game_and_keeps_it(deps):
    text, _ = exports_reply(deps, {**CONTEXT, "role": "dps", "eui_base": "Autre"}, [])
    assert "« Autre »" in eui_line(text)
    character = read_profile(deps, WHO)["character"]
    assert character["ellesmere_base"] == "Autre" and character["fields"]["ellesmere_base"]["source"] == "jeu"
    text, _ = exports_reply(deps, {**CONTEXT, "role": "dps"}, [])
    assert "« Autre »" in eui_line(text)  # choisi une fois : gardé au profil


def test_exports_button_uses_the_profile_base(deps):
    set_character(deps, WHO, cls="Mage", ellesmere_base="Autre")
    text, links = exports_reply(deps, {**CONTEXT, "role": "dps"}, [])
    assert "« Autre »" in eui_line(text) and any(link["kind"] == "ellesmere" for link in links)


def test_exports_button_without_choice_says_how_to_choose(deps):
    text, _ = exports_reply(deps, {**CONTEXT, "role": "dps"}, [])
    line = eui_line(text)
    assert "« Base »" in line and "/fb base" in line


def test_exports_button_with_an_unknown_base_lists_the_profiles(deps):
    text, links = exports_reply(deps, {**CONTEXT, "role": "dps", "eui_base": "Inconnu"}, [])
    assert not any(link["kind"] == "ellesmere" for link in links)
    assert "Inconnu" in text and "Autre" in text
    assert WHO not in read_profile(deps)["characters"]


def test_cli_profile_set_and_export(deps, capsys):
    assert main(["profile", "set", WHO, "--class", "Mage", "--level", "19", "--ellesmere-base", "Autre"], deps) == 0
    capsys.readouterr()
    assert main(["export", "ellesmere", WHO, "--role", "dps", "--realm", REALM, "--json"], deps) == 0
    assert json.loads(capsys.readouterr().out)["base"]["name"] == "Autre"
