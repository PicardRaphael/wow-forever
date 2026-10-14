"""Métiers du personnage (RX1, bloc E, décision 254) : ForeverBridge 0.3.0 envoie `professions` (lignes de
compétence abandonnables : métiers principaux et secondaires, rang et rang maximal, sous `pcall`) ; le pont les relie,
les compare au profil et les écrit au clic (`apply_game_fields`, source `jeu`). Rangs et noms inventés pour le test."""

import pytest
from test_bridge_addon_lua import Game
from test_bridge_loop_p06b_c import setup  # noqa: F401 : fixture partagée
from test_bridge_profile_gap import context

from forever.bridge.context import load_context_data, professions_context, resolve
from forever.bridge.profile_gap import game_fields
from forever.profile import read_profile, set_character

SKILLS = """
skill_lines = {
    { "Professions", true, true, 0, 0, 0, 0, false },
    { "Herbalism", false, false, 12, 0, 0, 34, true },
    { "Alchemy", false, false, 5, 0, 0, 34, true },
    { "Secondary Skills", true, true, 0, 0, 0, 0, false },
    { "Cooking", false, false, 7, 0, 0, 34, true },
    { "Weapon Skills", true, true, 0, 0, 0, 0, false },
    { "Staves", false, false, 20, 0, 0, 20, false },
}
function GetNumSkillLines() return #skill_lines end
function GetSkillLineInfo(i) return unpack(skill_lines[i]) end
"""
EXPECTED = "Herbalism:12:34,Alchemy:5:34,Cooking:7:34"


def ctx_of(game):
    ctx = game.lua.globals().ForeverBridge_Message.Context()[0]
    return ctx["professions"]


def test_professions_in_context():
    assert ctx_of(Game(prelude=SKILLS)) == EXPECTED
    assert ctx_of(Game()) is None  # API absente : champ absent, aucune erreur
    broken = "function GetNumSkillLines() return 2 end\nfunction GetSkillLineInfo() error('API retirée') end"
    assert ctx_of(Game(prelude=broken)) is None


def test_professions_are_a_context_key():
    from forever.bridge.record import CONTEXT_KEYS

    assert "professions" in CONTEXT_KEYS
    keys = Game().lua.globals().ForeverBridge_Message.KEYS
    assert "professions" in [keys[i] for i in range(1, len(keys) + 1)]


def test_professions_resolved(make_deps):
    assert professions_context({"professions": EXPECTED}) == {"Herbalism": 12, "Alchemy": 5, "Cooking": 7}
    assert professions_context({}) is None
    assert professions_context({"professions": "Herbalism:x:34,Cooking:7:34"}) == {"Cooking": 7}
    resolved = resolve(load_context_data(make_deps()), {**context(), "professions": EXPECTED})
    assert game_fields(resolved)["professions"] == {"Herbalism": 12, "Alchemy": 5, "Cooking": 7}
    assert game_fields(resolve(load_context_data(make_deps()), context()))["professions"] is None


def test_professions_written_to_profile_on_click(setup):  # noqa: F811
    deps, data, _agent, send, cards = setup
    game = game_fields(resolve(data, context()))
    set_character(deps, "Jen", cls="Mage", race=game["race"], faction=game["faction"], level=game["level"])
    send(ctx={**context(), "professions": EXPECTED})
    (card,) = cards()
    assert any(line.startswith("métiers") for line in card.lines.values())
    assert read_profile(deps)["character"]["professions"] in ({}, None)  # rien d'écrit avant le clic
    send(flags={f"a=profile_apply:{card.id}"}, text="")
    c = read_profile(deps)["character"]
    assert c["professions"] == {"Herbalism": 12, "Alchemy": 5, "Cooking": 7}
    assert c["fields"]["professions"]["source"] == "jeu"


@pytest.mark.parametrize("field", ["professions"])
def test_professions_listed_among_gap_fields(field):
    from forever.bridge.profile_gap import FIELDS, LABELS

    assert field in FIELDS and LABELS[field] == "métiers"
