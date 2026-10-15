"""Suites de la relecture de RX1c : filtre de ligne après le texte `>>`, filtre des gardes, étapes `#hardcore`,
filtre de `#xprate` et de `#group`, signe du saut de `.xp`, objectif gardé quand sa dernière ligne est fermée ; profil
de base choisi en jeu dit « choisi en jeu », et une commande `--ellesmere-base` postérieure n'est pas écrasée par un
ancien choix du jeu renvoyé à chaque clic (décision 269).

Valeurs : guides fabriqués écrits ici (syntaxe seulement, quêtes de `tests/fixtures/route/route.json`), sauvegarde
synthétique `tests/fixtures/exports/ellesmere_base.lua`, contexte réel `tests/fixtures/bridge/contexts/mage19.txt`."""

import shutil

import pytest
from conftest import FIXTURES
from test_engine_route import CAP, make_world, start_state

from forever.bridge.exports import exports_reply
from forever.compare import replay_rxp
from forever.exports.ellesmere import ellesmere_export
from forever.profile import read_profile, set_character
from forever.rxp_guides import Who, parse_guide

MAGE = Who("Mage", "Orc", "Horde")


def guide(body: str):
    g = parse_guide("#forever\n#name 1-5 Fixture Review\n#group Fixture (H) << Horde\n\n" + body, "x.lua")
    assert g is not None
    return g


def kinds(g, who=MAGE, level=1, end=5, game_data=None):
    world, _ = make_world(game_data)
    rep = replay_rxp(game_data, world, [g], who, start_state(level=level), end_level=end, cap=CAP)
    return [(s.kind, s.ref) for s in rep.stops], rep


def test_line_filter_after_text_is_kept():
    g = guide("step\n    .accept 101 >>Fixture text << Warrior\n    .accept 102 >>Fixture text << Mage\n")
    actions = g.steps[0].actions
    assert [(a.ref, a.filter) for a in actions] == [(101, "Warrior"), (102, "Mage")]


def test_group_filter_is_not_part_of_the_group():
    assert guide("step\n    .accept 101\n").group == "Fixture (H)"


def test_guard_filter_is_kept(game_data):
    g = guide("step\n    .isOnQuest 999 << Warrior\n    .accept 101\n")
    stops, _ = kinds(g, game_data=game_data)
    assert ("accept", 101) in stops  # garde d'une autre classe : sans effet pour le Mage


def test_hardcore_steps_are_skipped(game_data):
    g = guide("step\n    #hardcore\n    .accept 101\nstep\n    .accept 102\n")
    stops, _ = kinds(g, game_data=game_data)
    assert ("accept", 101) not in stops and ("accept", 102) in stops


def test_xprate_filter_is_applied(game_data):
    g = guide("step\n    #xprate >1.99 << Warrior\n    .accept 101\n")
    stops, _ = kinds(g, game_data=game_data)
    assert ("accept", 101) in stops  # condition réservée au Guerrier : sans effet pour le Mage


def test_negative_skip_reverses_the_xp_guard(game_data):
    g = guide("step\n    .xp 3,-1\n    .accept 101\n")
    stops, _ = kinds(g, game_data=game_data)
    assert ("accept", 101) not in stops  # saut négatif : étape sautée sous le niveau 3


def test_objective_kept_when_its_last_line_is_closed(game_data):
    g = guide(
        "step\n    .accept 101\n    .complete 101,1\nstep\n    .xp <4,1\n    .complete 101,2\nstep\n    .turnin 101\n"
    )
    stops, rep = kinds(g, game_data=game_data)
    assert ("objective", 101) in stops and ("turnin", 101) in stops
    assert not rep.skipped


# --- profil de base choisi en jeu ------------------------------------------------------------------------------------

CONTEXT = dict(
    line.split("=", 1)
    for line in (FIXTURES / "bridge" / "contexts" / "mage19.txt").read_text(encoding="utf-8").split("\n")
    if "=" in line
)
CONTEXT["eui"] = "on"  # CJ1 (décision 274) : EllesmereUI rallumé par le joueur (/fb eui on)
WHO, REALM = CONTEXT["name"], CONTEXT["realm"]


@pytest.fixture
def deps(tmp_path, make_deps):
    root = tmp_path / "wow"
    sv = root / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    shutil.copy(FIXTURES / "exports" / "ellesmere_base.lua", sv / "EllesmereUI.lua")
    return make_deps(wow_dir=root)


def test_game_choice_is_said_chosen_in_game(deps):
    doc = ellesmere_export(deps, WHO, REALM, "Mage", 19, "dps", base_name="Autre", choice="jeu")
    assert doc["base"]["choice"] == "jeu"
    assert any("/fb base" in a for a in doc["provenance"]["assumptions"])


def test_later_command_is_not_overwritten_by_an_old_game_choice(deps):
    exports_reply(deps, {**CONTEXT, "role": "dps", "eui_base": "Autre"}, [])
    set_character(deps, WHO, ellesmere_base="Base")  # commande postérieure au choix fait en jeu
    text, _ = exports_reply(deps, {**CONTEXT, "role": "dps", "eui_base": "Autre"}, [])  # même valeur renvoyée
    assert read_profile(deps, WHO)["character"]["ellesmere_base"] == "Base"
    assert "« Base »" in next(line for line in text.splitlines() if "EllesmereUI" in line)
    exports_reply(deps, {**CONTEXT, "role": "dps", "eui_base": "Base"}, [])
    exports_reply(deps, {**CONTEXT, "role": "dps", "eui_base": "Autre"}, [])  # nouveau choix en jeu : il l'emporte
    assert read_profile(deps, WHO)["character"]["ellesmere_base"] == "Autre"
