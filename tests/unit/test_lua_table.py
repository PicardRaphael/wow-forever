"""Analyseur des tables Lua littérales générées par les addons (Questie, SavedVariables), sans exécuter de Lua."""

import pytest

from forever.pipeline.lua_table import parse_lua_assignments, parse_lua_value


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
