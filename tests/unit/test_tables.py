"""Lecture typée des tables CSV du client : colonnes déclarées, types, erreurs de schéma nommées."""

import pytest
from conftest import WAGO_70009

from forever.errors import DataSchemaError
from forever.pipeline.tables import TABLES, read_table


def write_csv(tmp_path, name, text):
    path = tmp_path / f"{name}.csv"
    path.write_bytes(text.encode("utf-8"))
    return path


def test_fixture_rows_are_typed():
    rows = read_table(WAGO_70009 / "enUS" / "SpellName.csv", "SpellName")
    assert len(rows) == 217  # fixture extraite (README.md) : 217 sorts (armures ajoutées en T04c)
    first = rows[0]
    assert set(first) == {"ID", "Name_lang"}  # colonnes déclarées seulement
    assert isinstance(first["ID"], int) and isinstance(first["Name_lang"], str)


def test_float_and_negative_values():
    rows = read_table(WAGO_70009 / "enUS" / "SpellEffect.csv", "SpellEffect")
    by_spell = {(r["SpellID"], r["EffectIndex"]): r for r in rows if r["DifficultyID"] == 0}
    frostbolt_slow = by_spell[(116, 0)]  # fixture SpellEffect : Frostbolt rang 1, effet 0 (ralentissement)
    assert frostbolt_slow["EffectBasePointsF"] == -40.0
    assert isinstance(frostbolt_slow["Variance"], float)


def test_french_names_with_quotes():
    rows = {r["ID"]: r["Name_lang"] for r in read_table(WAGO_70009 / "frFR" / "SpellName.csv", "SpellName")}
    assert rows[116] == "Eclair de givre"  # fixture frFR/SpellName.csv (champ entre guillemets)


def test_comma_inside_quoted_text(tmp_path):
    path = write_csv(tmp_path, "SpellName", 'ID,Name_lang\n5,"Trait, de feu"\n')
    assert read_table(path, "SpellName") == [{"ID": 5, "Name_lang": "Trait, de feu"}]


def test_extra_columns_are_ignored(tmp_path):
    path = write_csv(tmp_path, "SpellName", "Autre,ID,Name_lang\nx,5,Nom\n")
    assert read_table(path, "SpellName") == [{"ID": 5, "Name_lang": "Nom"}]


def test_missing_column_names_table_and_column(tmp_path):
    path = write_csv(tmp_path, "SpellName", "ID\n1\n")
    with pytest.raises(DataSchemaError) as info:
        read_table(path, "SpellName")
    assert info.value.code == "data_schema"
    assert "SpellName" in info.value.message and "Name_lang" in info.value.message


def test_malformed_integer_names_the_line(tmp_path):
    path = write_csv(tmp_path, "SpellName", "ID,Name_lang\n1,Alpha\nx,Beta\n")
    with pytest.raises(DataSchemaError) as info:
        read_table(path, "SpellName")
    message = info.value.message
    assert "SpellName" in message and "ID" in message and "ligne 3" in message


def test_empty_integer_is_an_error(tmp_path):
    path = write_csv(tmp_path, "TraitEdge", "ID,LeftTraitNodeID,RightTraitNodeID\n1,,2\n")
    with pytest.raises(DataSchemaError):
        read_table(path, "TraitEdge")


def test_unknown_table_is_schema_error(tmp_path):
    path = write_csv(tmp_path, "Inconnue", "ID\n1\n")
    with pytest.raises(DataSchemaError):
        read_table(path, "Inconnue")


def test_every_rule_table_is_declared(decode_rules):
    assert set(decode_rules["tables"]) <= set(TABLES)
    for tables in decode_rules["localized_tables"].values():
        assert set(tables) <= set(TABLES)
