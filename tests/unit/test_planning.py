"""Planification et personnages prévus (demande de l'utilisateur du 2026-09-29, complément aux décisions 116 et 117).

- Profil : neuf classes, personnages prévus (`planned`), champs manquants propres à un personnage prévu.
- Contrôle des chiffres : les lignes sourcées (avec une adresse) du rapport de `forever-web-researcher` sont des
  sources ; les autres lignes du rapport n'en sont pas."""

from dataclasses import replace

import pytest
from conftest import FIXTURES, isolated_deps

from forever import hooks
from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.profile import read_profile, set_character

TRANSCRIPTS = FIXTURES / "transcripts"


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("planning"))


# --- Profil : neuf classes et personnages prévus ---------------------------------------------------------------------


@pytest.fixture
def pdeps(make_deps, tmp_path):
    return replace(make_deps(), profile_path=tmp_path / "joueur" / "profile.json")


CLASSES_FR = {
    "Guerrier": "Warrior",
    "Paladin": "Paladin",
    "Chasseur": "Hunter",
    "Voleur": "Rogue",
    "Prêtre": "Priest",
    "Chaman": "Shaman",
    "Mage": "Mage",
    "Démoniste": "Warlock",
    "Druide": "Druid",
}


def test_all_nine_classes_are_accepted(pdeps):
    for i, (fr, en) in enumerate(CLASSES_FR.items()):
        doc = set_character(pdeps, f"P{i}", cls=fr, planned=True)
        assert doc["characters"][f"P{i}"]["class"]["value"] == en  # schéma 2 (PV1) : champ sourcé
        assert set_character(pdeps, f"E{i}", cls=en, planned=True)["characters"][f"E{i}"]["class"]["value"] == en
    with pytest.raises(InvalidArgumentError):
        set_character(pdeps, "X", cls="Chevalier de la mort")


def test_planned_character(pdeps):
    set_character(
        pdeps, "Futur", cls="Druide", race="Tauren", faction="Horde", professions={"Herboristerie": 0}, planned=True
    )
    view = read_profile(pdeps, "Futur")
    c = view["character"]
    assert c is not None and c["planned"] is True and c["class"] == "Druid" and c["level"] is None
    assert c["validated"] is True  # PV1 : 9 classes contrôlées ; Tauren permis pour le Druide (races.json)
    assert view["missing"] == []  # ni niveau ni talents attendus d'un personnage prévu
    set_character(pdeps, "Futur", planned=False)  # créé en jeu : niveau et talents attendus
    view = read_profile(pdeps, "Futur")
    assert view["character"] is not None and view["character"]["planned"] is False
    assert view["missing"] == ["level", "talents"]


def test_existing_characters_read_as_not_planned(pdeps):
    set_character(pdeps, "Givrelame", cls="Mage", race="Orc", faction="Horde", level=12)
    c = read_profile(pdeps, "Givrelame")["character"]
    assert c is not None and c["planned"] is False


def test_planned_mage_race_is_still_checked(pdeps):
    with pytest.raises(InvalidArgumentError, match="Race inconnue"):
        set_character(pdeps, "Futur", cls="Mage", race="Tauren", planned=True)


def test_cli_planned_and_created(pdeps, capsys):
    assert main(["profile", "set", "Futur", "--class", "Druide", "--race", "Tauren", "--planned"], pdeps) == 0
    out = capsys.readouterr().out
    assert "prévu" in out
    assert main(["profile", "set", "Futur", "--created", "--level", "5"], pdeps) == 0
    c = read_profile(pdeps, "Futur")["character"]
    assert c is not None and c["planned"] is False and c["level"] == 5


# --- Contrôle des chiffres : rapport du sous-agent de recherche ------------------------------------------------------


def test_sourced_lines_of_the_web_researcher_are_sources():
    lines = hooks.read_transcript(TRANSCRIPTS / "session_web_researcher.jsonl")
    ok = "Selon le guide (communautaire, 2026-09-20) : 31 points en Sacré et 17 points en Protection."
    assert hooks.unsourced_numbers(lines, ok) == []
    # « 45 points » figure dans le rapport, mais sur une ligne sans adresse : pas une source.
    assert hooks.unsourced_numbers(lines, "Il faudrait 45 points en Vindicte.") == ["45 points"]
