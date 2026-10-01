"""Analyseur des tables Lua littérales générées par les addons (Questie, SavedVariables), sans exécuter de Lua."""

import pytest

from forever.pipeline.lua_table import parse_lua_assignments, parse_lua_value, parse_lua_value_at


def test_strings_single_and_double_quotes_with_escapes():
    assert parse_lua_value("'Dire Mottled Boar'") == "Dire Mottled Boar"
    assert parse_lua_value('"AH"') == "AH"
    assert parse_lua_value(r"'L\'ours \"brun\"\n\\'") == 'L\'ours "brun"\n\\'
    assert parse_lua_value(r'"\65\066"') == "AB"
    assert parse_lua_value('"Élève"') == "Élève"


def test_numbers():
    assert parse_lua_value("120") == 120
    assert parse_lua_value("-4713.24") == -4713.24
    assert parse_lua_value("0.5") == 0.5
    assert parse_lua_value("1e3") == 1000.0
    assert parse_lua_value("0x10") == 16


def test_keywords():
    assert parse_lua_value("nil") is None
    assert parse_lua_value("true") is True
    assert parse_lua_value("false") is False


def test_positional_table_is_a_list_with_nil_holes():
    assert parse_lua_value("{'Hare',8,nil,1,}") == ["Hare", 8, None, 1]
    assert parse_lua_value("{}") == []


def test_keyed_tables():
    assert parse_lua_value("{[14]={{52.03,49.96},{54.2,30.65}}}") == {14: [[52.03, 49.96], [54.2, 30.65]]}
    assert parse_lua_value('{name = "Moi", ["level"] = 14; [2] = true}') == {"name": "Moi", "level": 14, 2: True}
    assert parse_lua_value("{'a', x = 1}") == {1: "a", "x": 1}


def test_comments_are_skipped():
    text = "{\n    [788] = {2, 170}, -- Classic: 2: 170->170\n    --[[ bloc\n ]] [789] = {3, 250},\n}"
    assert parse_lua_value(text) == {788: [2, 170], 789: [3, 250]}


def test_long_string():
    assert parse_lua_value("[[return {1}]]") == "return {1}"


def test_error_is_located():
    with pytest.raises(ValueError, match=r"ligne 2, colonne 5"):
        parse_lua_value("{\n  1 +}")
    with pytest.raises(ValueError, match="chaîne non terminée"):
        parse_lua_value("'abc")
    with pytest.raises(ValueError, match="après la valeur"):
        parse_lua_value("1 2")


def test_saved_variables_file_assignments():
    text = 'ForeverLoggerDB = {\n\t["schema"] = 1,\n}\nAutre = "x" -- fin\n'
    assert parse_lua_assignments(text) == {"ForeverLoggerDB": {"schema": 1}, "Autre": "x"}
    with pytest.raises(ValueError, match="nom de variable"):
        parse_lua_assignments("= 1")


# --- CH0, bloc B : littéral à une position (fichiers d'addon : `ns.Data = {…}` suivi de code) -------------------


def test_value_at_a_position_returns_value_and_end():
    text = 'local _, ns = ...\nns.Data = { date = "2026-09-25", n = {1, 2} } -- fin\nns.Data.beasts = { {id = 7} }\n'
    start = text.index("=", text.index("ns.Data")) + 1
    value, end = parse_lua_value_at(text, start)
    assert value == {"date": "2026-09-25", "n": [1, 2]}
    assert text[end - 1] == "}" and text[end:].lstrip().startswith("-- fin")


def test_value_at_ignores_the_text_that_follows():
    text = "x = {a = 1}\nfunction f() return 1 end\n"
    value, end = parse_lua_value_at(text, text.index("{"))
    assert value == {"a": 1} and text[end:].startswith("\nfunction")


def test_value_at_reports_line_and_column_on_error():
    text = "ns.Data = {\n  a = ,\n}\n"
    with pytest.raises(ValueError, match="ligne 2"):
        parse_lua_value_at(text, text.index("{"))
