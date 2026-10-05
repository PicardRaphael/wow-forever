"""Définitions de structure (`.dbd`, T08c, bloc B) : lecture du format, choix du bloc du build (jamais un voisin),
noms des CSV, décodage des entrées de la fixture `DBCache.bin`, validation d'une disposition (taille exacte,
identifiant, en-tête du CSV, références, taux d'égalité avec les lignes du build).

Fixtures : un `.dbd` synthétique écrit ici (structure du format seulement) ; les dispositions de 1.60.1.70170
dérivées des `.dbd` de WoWDBDefs (`tests/fixtures/dbd/`, voir son README : structure seulement, sans texte du
dépôt) ; `tests/fixtures/hotfix/DBCache.bin` ; `tests/fixtures/wago/1.60.1.70170/` (lignes du build)."""

import csv
import struct

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.errors import DataSchemaError
from forever.pipeline.dbcache import Status, effective, known_tables, read_dbcache, table_names
from forever.pipeline.dbd import (
    csv_header,
    decode_record,
    layout_for,
    layouts_from_json,
    layouts_to_json,
    parse_dbd,
    validate_layout,
)

LAYOUTS_PATH = FIXTURES / "dbd" / "layouts-1.60.1.70170.json"
WAGO = FIXTURES / "wago" / "1.60.1.70170" / "enUS"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")

SYNTHETIC = """COLUMNS
int ID
int<Parent::ID> ParentID?
float Pos
locstring Name_lang // commentaire
int Flags? // &1 : drapeau
int Index

LAYOUT 11111111
BUILD 9.9.9.1-9.9.9.5
$id$ID<32>
Pos[2]
Flags<u8>

LAYOUT 22222222, 33333333
BUILD 1.60.1.70009, 1.60.1.70170
BUILD 1.15.1.1
COMMENT bloc synthétique
$noninline,id$ID<32>
Name_lang
Pos[2]
Flags<u16>
Index<8>
$noninline,relation$ParentID<32>
"""


@pytest.fixture(scope="module")
def synthetic():
    return parse_dbd(SYNTHETIC, "Synthetic")


@pytest.fixture(scope="module")
def layouts():
    return layouts_from_json(read_json(LAYOUTS_PATH))


@pytest.fixture(scope="module")
def applicable():
    cache = read_dbcache(FIXTURES / "hotfix" / "DBCache.bin")
    names = table_names(known_tables(RULES) | {"TraitNodeGroupXTraitNode"})
    return effective(cache.entries, names).applicable


def entries_of(applicable, table):
    return [e for (t, _), e in applicable.items() if t == table]


def decoded(layouts, applicable, table, rec_id):
    entry = applicable[(table, rec_id)]
    assert entry.status == Status.VALID
    return decode_record(layouts[table], entry.data, rec_id)


def csv_table(table):
    with (WAGO / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = {int(r["ID"]): r for r in reader}
        return list(reader.fieldnames or []), rows


def known_ids(applicable):
    """Identifiants des tables du build (fixture) et des correctifs, par table référencée (`int<Table::ID>`)."""
    out = {}
    for table in ("TraitNode", "TraitNodeEntry", "TraitDefinition"):
        out[table] = set(csv_table(table)[1]) | {r for t, r in applicable if t == table}
    out["Spell"] = set(csv_table("SpellName")[1]) | {r for t, r in applicable if t in ("SpellName", "Spell")}
    curves = {int(r["CurveID"]) for r in csv_table("CurvePoint")[1].values()}
    out["Curve"] = curves | {r for t, r in applicable if t == "Curve"}
    return out


# --- Format ----------------------------------------------------------------------------------------------------


def test_parse_columns(synthetic):
    cols = synthetic.columns
    assert [c.kind for c in cols.values()] == ["int", "int", "float", "locstring", "int", "int"]
    assert cols["ParentID"].ref == "Parent" and cols["ID"].ref is None
    assert len(synthetic.blocks) == 2
    assert synthetic.blocks[1].layouts == ("22222222", "33333333")
    assert synthetic.blocks[1].builds == {"1.60.1.70009", "1.60.1.70170", "1.15.1.1"}
    assert synthetic.blocks[0].ranges == (("9.9.9.1", "9.9.9.5"),)


def test_parse_fields(synthetic):
    first = {f.name: f for f in synthetic.blocks[0].fields}
    assert first["ID"].is_id and first["ID"].inline and first["ID"].size == 32
    assert first["Pos"].kind == "float" and first["Pos"].array == 2 and first["Pos"].size is None
    assert first["Flags"].size == 8 and first["Flags"].signed is False
    second = {f.name: f for f in synthetic.blocks[1].fields}
    assert second["ID"].is_id and not second["ID"].inline
    assert second["Name_lang"].kind == "locstring"
    assert second["Flags"].size == 16 and second["Flags"].signed is False
    assert second["Index"].size == 8 and second["Index"].signed is True
    assert second["ParentID"].relation and not second["ParentID"].inline and second["ParentID"].ref == "Parent"


def test_layout_for_takes_only_the_named_build(synthetic):
    assert layout_for(synthetic, "1.60.1.70170").layout == "22222222"
    assert layout_for(synthetic, "1.15.1.1").layout == "22222222"
    assert layout_for(synthetic, "9.9.9.3").layout == "11111111"  # plage
    assert layout_for(synthetic, "9.9.9.9") is None
    assert layout_for(synthetic, "1.60.1.70171") is None  # build voisin : jamais emprunté


def test_csv_header_follows_wago_names(synthetic):
    assert csv_header(layout_for(synthetic, "1.60.1.70170")) == [
        "ID",
        "Name_lang",
        "Pos_0",
        "Pos_1",
        "Flags",
        "_Index",
        "ParentID",
    ]
    assert csv_header(layout_for(synthetic, "9.9.9.1")) == ["ID", "Pos_0", "Pos_1", "Flags"]


def test_decode_synthetic_record(synthetic):
    layout = layout_for(synthetic, "1.60.1.70170")
    data = "Épée".encode() + b"\0" + struct.pack("<ffHbi", 1.5, -2.0, 65535, -1, 77)
    assert decode_record(layout, data, 42) == {
        "ID": 42,
        "Name_lang": "Épée",
        "Pos_0": 1.5,
        "Pos_1": -2.0,
        "Flags": 65535,
        "_Index": -1,
        "ParentID": 77,
    }
    with pytest.raises(DataSchemaError):
        decode_record(layout, data + b"\0", 42)  # octet en trop
    with pytest.raises(DataSchemaError):
        decode_record(layout, data[:-2], 42)  # données coupées


def test_float32_reads_back_as_written_decimal(synthetic):
    layout = layout_for(synthetic, "9.9.9.1")
    data = struct.pack("<iffB", 7, 0.1, 2.5, 3)
    assert decode_record(layout, data, 7) == {"ID": 7, "Pos_0": 0.1, "Pos_1": 2.5, "Flags": 3}


# --- Dispositions de 1.60.1.70170 ------------------------------------------------------------------------------


def test_derived_layouts_roundtrip(layouts):
    doc = read_json(LAYOUTS_PATH)
    assert doc["build"] == LOCAL_VERSION and len(doc["commit"]) == 40
    assert layouts_to_json(layouts, doc["repo"], doc["commit"], doc["build"]) == doc
    assert {"TraitNode", "TraitEdge", "CurvePoint", "SpellName", "SpellLevels"} <= set(layouts)
    assert all(lay.build == LOCAL_VERSION for lay in layouts.values())


def test_headers_match_the_csv_of_the_build(layouts):
    for table in ("TraitNode", "TraitNodeXTraitNodeEntry", "CurvePoint", "SpellLevels", "SpellMisc", "SpellEffect"):
        header, _ = csv_table(table)
        assert csv_header(layouts[table]) == header, table


def test_decode_trait_records(layouts, applicable):
    node = decoded(layouts, applicable, "TraitNode", 105928)
    assert (node["ID"], node["TraitTreeID"], node["PosX"], node["PosY"]) == (105928, 1117, 5620, 5130)
    assert decoded(layouts, applicable, "TraitDefinition", 135484)["SpellID"] == 1323963
    entry = decoded(layouts, applicable, "TraitNodeEntry", 141191)
    assert (entry["TraitDefinitionID"], entry["MaxRanks"]) == (145863, 2)
    edge = decoded(layouts, applicable, "TraitEdge", 136735)
    assert (edge["LeftTraitNodeID"], edge["RightTraitNodeID"], edge["Type"]) == (105931, 113569, 2)
    link = decoded(layouts, applicable, "TraitNodeXTraitNodeEntry", 139873)
    assert (link["TraitNodeID"], link["TraitNodeEntryID"], link["_Index"]) == (113569, 141191, 100)


def test_decode_curve_point_and_spell_records(layouts, applicable):
    point = decoded(layouts, applicable, "CurvePoint", 334737)
    assert (point["CurveID"], point["Pos_0"], point["Pos_1"]) == (111755, 1.0, 10.0)
    assert decoded(layouts, applicable, "SpellName", 1680)["Name_lang"] == "Whirlwind"
    assert decoded(layouts, applicable, "SpellName", 1323964)["Name_lang"] == "Lingering Rage"
    levels = decoded(layouts, applicable, "SpellLevels", 103013)  # identifiant non intégré, relation à la fin
    assert (levels["ID"], levels["SpellID"], levels["BaseLevel"]) == (103013, 18499, 30)


def test_every_valid_entry_decodes_exactly(layouts, applicable):
    count = 0
    for (table, rec_id), entry in applicable.items():
        if entry.status != Status.VALID or table not in layouts or rec_id == 999901:
            continue
        row = decode_record(layouts[table], entry.data, rec_id)
        assert row["ID"] == rec_id
        count += 1
    assert count > 150


# --- Validation ------------------------------------------------------------------------------------------------


def test_true_layout_is_validated(layouts, applicable):
    header, rows = csv_table("TraitNode")
    check = validate_layout(
        layouts["TraitNode"], entries_of(applicable, "TraitNode"), header, rows, known_ids(applicable)
    )
    assert check.ok, check.reason
    assert check.decoded == 14 and check.compared == 12
    assert check.equal_ratio is not None and 0.5 <= check.equal_ratio < 1.0  # la refonte change des valeurs


def test_table_without_comparable_row_is_validated_by_references(layouts, applicable):
    header, rows = csv_table("TraitNodeEntry")
    check = validate_layout(
        layouts["TraitNodeEntry"], entries_of(applicable, "TraitNodeEntry"), header, rows, known_ids(applicable)
    )
    assert check.ok and check.compared == 0 and check.references_ok is True


def test_swapped_fields_are_refused(layouts, applicable):
    lay = layouts["TraitNodeEntry"]
    fields = list(lay.fields)
    i, j = [k for k, f in enumerate(fields) if f.name in ("TraitDefinitionID", "MaxRanks")]
    fields[i], fields[j] = fields[j], fields[i]  # deux entiers de même taille lus à la place l'un de l'autre
    header, rows = csv_table("TraitNodeEntry")
    check = validate_layout(
        lay._replace(fields=tuple(fields)),
        entries_of(applicable, "TraitNodeEntry"),
        header,
        rows,
        known_ids(applicable),
    )
    assert not check.ok and check.references_ok is False and "référence" in check.reason


def test_changed_size_is_refused(layouts, applicable):
    lay = layouts["TraitNode"]
    fields = tuple(f._replace(size=16) if f.name == "PosX" else f for f in lay.fields)
    header, rows = csv_table("TraitNode")
    check = validate_layout(
        lay._replace(fields=fields), entries_of(applicable, "TraitNode"), header, rows, known_ids(applicable)
    )
    assert not check.ok and "taille" in check.reason


def test_wrong_identifier_is_refused(layouts, applicable):
    lay = layouts["TraitNode"]
    fields = list(lay.fields)
    fields[0], fields[1] = fields[1], fields[0]  # identifiant lu à la place de TraitTreeID
    header, rows = csv_table("TraitNode")
    check = validate_layout(
        lay._replace(fields=tuple(fields)), entries_of(applicable, "TraitNode"), header, rows, known_ids(applicable)
    )
    assert not check.ok and "identifiant" in check.reason


def test_header_mismatch_is_refused(layouts, applicable):
    header, rows = csv_table("TraitNode")
    wrong = [("PosZ" if h == "PosY" else h) for h in header]
    check = validate_layout(
        layouts["TraitNode"], entries_of(applicable, "TraitNode"), wrong, rows, known_ids(applicable)
    )
    assert not check.ok and "en-tête" in check.reason


def test_noise_below_the_ratio_is_refused(layouts, applicable):
    header, rows = csv_table("TraitNode")
    noisy = {i: {k: ("-1" if k != "ID" else v) for k, v in r.items()} for i, r in rows.items()}
    check = validate_layout(
        layouts["TraitNode"], entries_of(applicable, "TraitNode"), header, noisy, known_ids(applicable)
    )
    assert not check.ok and check.equal_ratio is not None and check.equal_ratio < 0.5
