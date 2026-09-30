"""Planification et personnages prévus (demande de l'utilisateur du 2026-09-29, complément aux décisions 116 et 117).

- `forever_build` sans niveau : niveau maximal lu dans les données (`level_cap`), origine `default` dans `inputs`.
- Respec de leveling à un niveau plus haut que celui du build actuel : chemin conseillé projeté depuis ce build
  (`respec.projected`), pour que l'agent conseille sans redemander le build.
- Profil : neuf classes, personnages prévus (`planned`), champs manquants propres à un personnage prévu.
- Contrôle des chiffres : les lignes sourcées (avec une adresse) du rapport de `forever-web-researcher` sont des
  sources ; les autres lignes du rapport n'en sont pas."""

import asyncio
from dataclasses import replace

import pytest
from conftest import FIXTURES, isolated_deps
from mcp import Client

from forever import hooks
from forever.build import build_report
from forever.cli import build_parser, main
from forever.engine.talents import check_build
from forever.errors import InvalidArgumentError
from forever.gamedata import build_game_data
from forever.mcp_server import build_server
from forever.profile import read_profile, set_character
from forever.store import load_version

TRANSCRIPTS = FIXTURES / "transcripts"
CURRENT_11 = {"wandSpecialization": 2}  # deux points : build légal au niveau 11 (premier niveau de talent + 1)


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("planning"))


@pytest.fixture(scope="module")
def game_data(deps):
    return build_game_data(load_version(deps))


# --- Niveau par défaut -----------------------------------------------------------------------------------------------


def test_build_without_level_uses_the_level_cap_of_the_data(deps, game_data):
    rep = build_report(deps, "pvp-bg", None, preset="rapide", sensitivity=False)
    cap = game_data.level_cap
    assert rep["level"] == cap
    assert rep["inputs"]["level"] == {"value": cap, "origin": "default"}
    assert any("niveau maximal" in a and str(cap) in a for a in rep["assumptions"])
    assert check_build(game_data, rep["talents"], cap) == []


def test_mcp_and_cli_level_is_optional(deps):
    async def schema():
        async with Client(build_server(deps)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            return tools["forever_build"].input_schema

    assert "level" not in (asyncio.run(schema()).get("required") or [])
    assert build_parser().parse_args(["build", "pvp-bg"]).level is None


# --- Chemin projeté depuis le build actuel ---------------------------------------------------------------------------


def test_respec_projects_the_path_from_the_current_build(deps, game_data):
    rep = build_report(deps, "leveling", 16, preset="rapide", current=CURRENT_11, sensitivity=False)
    proj = rep["respec"]["projected"]
    first = game_data.constants.talents.first_level
    assert proj["from_level"] == rep["respec"]["current_level"] == first + 1
    assert proj["to_level"] == 16
    levels = [s["level"] for s in proj["steps"]]
    assert levels == sorted(levels) and all(proj["from_level"] < lv <= 16 for lv in levels)
    assert all(s["talent"] in game_data.talents for s in proj["steps"])
    talents = proj["talents"]
    assert all(talents.get(k, 0) >= v for k, v in CURRENT_11.items())  # le build actuel est gardé
    assert check_build(game_data, talents, 16) == []
    assert proj["points"]["total"] == sum(talents.values())


def test_no_projection_without_current_build(deps):
    rep = build_report(deps, "leveling", 12, preset="rapide", sensitivity=False)
    assert rep["respec"].get("projected") is None


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
