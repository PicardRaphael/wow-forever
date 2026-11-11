"""FR1 : découpage d'une ligne de guide RestedXP en ce qui ne se traduit jamais (commande, identifiants, coordonnées,
filtres `<<`, codes `|c…|r`, `|T…|t`, `|H…|h`, nombres) et ce qui se traduit (texte libre, noms) ; gabarit à jetons
pour qu'une même phrase serve à toutes les étapes.

Valeurs : lignes inventées pour le test (`tests/fixtures/rxp_fr/`), aucun texte de RestedXP."""

from pathlib import Path

import pytest

from forever.rxp_fr.tokens import fill, make_template, parse_line, placeholders

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr" / "AddOns" / "RXPGuides"


def _lines() -> list[str]:
    out: list[str] = []
    for path in sorted(FIXTURES.rglob("*.lua")):
        out += path.read_bytes().decode("utf-8").split("\r\n")
    return out


def test_every_fixture_line_is_rebuilt_exactly():
    for raw in _lines():
        assert parse_line(raw).render() == raw


def test_a_command_keeps_its_name_ids_and_filter_out_of_the_text():
    line = parse_line("    .accept 90001 >>Accept A Fresh Start << Alliance Mage")
    assert line.kind == "command" and line.command == "accept"
    assert line.prefix == "    .accept 90001 >>"
    assert line.text == "Accept A Fresh Start"
    assert line.suffix == " << Alliance Mage"


def test_text_lines_header_lines_and_steps():
    assert parse_line("    >>Talk to someone").kind == "text"
    assert parse_line("    +|cRXP_WARN_Keep 5 silver|r << Alliance").text == "|cRXP_WARN_Keep 5 silver|r"
    star = parse_line("    *|cRXP_WARN_Wait here|r")
    assert star.kind == "text" and star.prefix == "    *"
    head = parse_line("#next 5-10 Testing Isle << Alliance !Hunter")
    assert head.kind == "header" and head.command == "next" and head.text == "5-10 Testing Isle"
    assert head.suffix == " << Alliance !Hunter"
    assert parse_line("step << Mage").kind == "step"
    assert parse_line("--comment").kind == "comment"
    assert parse_line("    .goto 9001,40.10,20.20").text == ""


def test_a_command_without_text_has_nothing_to_translate():
    line = parse_line("    .complete 90001,1")
    assert line.kind == "command" and line.text == "" and line.render() == "    .complete 90001,1"


def test_template_replaces_names_icons_links_brackets_and_numbers_by_slots():
    text = "|Tinterface/x.blp:20|tKill 8 |cRXP_ENEMY_Glade Boars|r for |cRXP_LOOT_[Boar Tusk]|r and [Frost Spark]"
    tpl = make_template(text)
    assert tpl.pattern == "{1}Kill {2} {3} for {4} and {5}"
    assert [s.kind for s in tpl.slots] == ["icon", "number", "npc", "item", "bracket"]
    assert fill(tpl.pattern, [s.raw for s in tpl.slots]) == text


def test_warning_codes_stay_in_the_pattern_and_inner_names_become_slots():
    text = "|cRXP_WARN_Be careful as |cRXP_ENEMY_Marsh Lurkers|r hit hard|r"
    tpl = make_template(text)
    assert tpl.pattern == "|cRXP_WARN_Be careful as {1} hit hard|r"
    assert tpl.slots[0].name == "Marsh Lurkers"


def test_a_slot_name_keeps_its_id_apart():
    (slot,) = make_template("|cRXP_FRIENDLY_Brin Oakvale::900001|r").slots
    assert slot.kind == "npc" and slot.name == "Brin Oakvale" and slot.ident == 900001


def test_pick_and_buy_colours_are_items():
    tpl = make_template("|cRXP_BUY_Ale|r |cRXP_PICK_Old Crate|r")
    assert [s.kind for s in tpl.slots] == ["item", "pick"]


def test_literal_braces_survive_the_template():
    tpl = make_template("use {this} 3 times")
    assert fill(tpl.pattern, [s.raw for s in tpl.slots]) == "use {this} 3 times"


def test_placeholders_are_listed_and_fill_refuses_an_unknown_slot():
    assert placeholders("Parlez à {2} puis {1}") == [2, 1]
    with pytest.raises(ValueError):
        fill("Parlez à {3}", ["a", "b"])
