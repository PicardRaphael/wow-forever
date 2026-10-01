"""Ratios du personnage décodés du client (T08b, bloc A) : `character_scaling.json`.

Valeurs attendues lues dans les fixtures (`tests/fixtures/wago/1.60.1.70124/`, extraites du cache de
`forever fetch` par `scripts/extract_class_fixtures.py`) : ligne et colonne nommées dans chaque test."""

import csv
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.pipeline.character_scaling import (
    CHARACTER_FILE,
    character_errors,
    decode_character_scaling,
    load_character_tables,
    load_gametables,
    read_gametable,
)
from forever.pipeline.decode import decode_version
from forever.pipeline.verify import verify_version

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
CAP = RULES["levels"]["level_cap"]
CLASSES = list(RULES["classes"])
GT_DIR = WAGO_70124 / "gametables"


def rows(table: str) -> list[dict[str, str]]:
    with (WAGO_70124 / "enUS" / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


CLASS_ID = {r["Name_lang"]: int(r["ID"]) for r in rows("ChrClasses")}


def pes(cls: str, level: int) -> dict[str, str]:
    return next(
        r for r in rows("PlayerExpectedStat") if int(r["ClassID"]) == CLASS_ID[cls] and int(r["Level"]) == level
    )


@pytest.fixture(scope="module")
def tables():
    return load_character_tables(WAGO_70124, RULES)


@pytest.fixture(scope="module")
def doc(tables):
    return decode_character_scaling(tables, RULES, load_gametables(GT_DIR, RULES), LOCAL_VERSION)


def test_nine_classes_every_level(doc):
    assert set(doc["classes"]) == set(CLASSES) and len(CLASSES) == 9
    assert doc["level_cap"] == CAP
    for cls, entry in doc["classes"].items():
        assert entry["class_id"] == CLASS_ID[cls]
        for key in ("base_mana", "spell_crit_per_intellect", "crit_per_agility", "hp_per_stamina"):
            assert len(entry[key]) == CAP, (cls, key)


@pytest.mark.parametrize("level", [1, 10, 30, CAP])
def test_mage_values_equal_player_expected_stat(doc, level):
    mage, row = doc["classes"]["Mage"], pes("Mage", level)
    assert mage["base_mana"][level - 1] == float(row["BaseMana"])
    assert mage["spell_crit_per_intellect"][level - 1] == float(row["SpellCritPerIntellect"])
    assert mage["crit_per_agility"][level - 1] == float(row["CritPerAgility"])
    assert mage["hp_per_stamina"][level - 1] == float(row["Field_1_60_1_69876_005"])


def test_class_without_mana_has_zero_base_mana(doc):
    assert all(float(pes("Warrior", lv)["BaseMana"]) == 0 for lv in (1, CAP))
    assert set(doc["classes"]["Warrior"]["base_mana"]) == {0.0}


def test_xp_to_next_equals_level_experience(doc):
    expected = {int(r["Level"]): int(r["Experience"]) for r in rows("LevelExperience")}
    assert doc["xp_to_next"] == [expected[lv] for lv in range(1, CAP)]


def test_rested_equals_exhaustion(doc):
    expected = [
        {
            "name": r["Name_lang"],
            "xp": int(r["Xp"]),
            "factor": float(r["Factor"]),
            "outdoor_hours": float(r["OutdoorHours"]),
            "inn_hours": float(r["InnHours"]),
            "threshold": float(r["Threshold"]),
        }
        for r in rows("Exhaustion")
    ]
    assert doc["rested"] == expected


def test_armor_constant_equals_expected_stat(doc):
    by_level = {int(r["Lvl"]): float(r["ArmorConstant"]) for r in rows("ExpectedStat") if r["ExpansionID"] == "-2"}
    assert doc["armor_constant"] == [by_level[lv] for lv in range(1, CAP + 1)]


@pytest.mark.parametrize("key", ["spirit_base", "spirit_extra"])
def test_hp_regen_curves_equal_curve_points(doc, key):
    curve_type = RULES["character_scaling"]["hp_regen_curve_types"][key]
    curve = next(
        int(r["CurveID"])
        for r in rows("GlobalCurve")
        if int(r["Type"]) == curve_type and int(r["Subtype"]) == CLASS_ID["Mage"]
    )
    points = sorted((r for r in rows("CurvePoint") if int(r["CurveID"]) == curve), key=lambda r: int(r["OrderIndex"]))
    assert doc["classes"]["Mage"]["hp_regen"][key] == [[float(p["Pos_0"]), float(p["Pos_1"])] for p in points]


def test_crosscheck_against_gametables(doc):
    status = {c["value"]: c["status"] for c in doc["crosscheck"]}
    assert status == {
        "base_mana": "concorde",
        "hp_per_stamina": "concorde",
        "xp_to_next": "concorde",
        "armor_constant": "ecart",  # armormitigationbylvl : table de retail (fixture, niveau 1)
    }
    armor = next(c for c in doc["crosscheck"] if c["value"] == "armor_constant")
    assert armor["gaps"] and armor["gaps"][0]["level"] == 1


def test_gametable_gap_is_reported_never_resolved(tables, tmp_path):
    shutil.copytree(GT_DIR, tmp_path / "gt")
    path = tmp_path / "gt" / "basemp.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    i = header.index("Mage")
    for n, line in enumerate(lines):
        cells = line.split("\t")
        if cells[0] == "10":
            cells[i] = str(float(cells[i]) + 1)
            lines[n] = "\t".join(cells)
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    doc = decode_character_scaling(tables, RULES, load_gametables(tmp_path / "gt", RULES), LOCAL_VERSION)
    mana = next(c for c in doc["crosscheck"] if c["value"] == "base_mana")
    assert mana["status"] == "ecart"
    assert [(g["class"], g["level"]) for g in mana["gaps"]] == [("Mage", 10)]
    assert doc["classes"]["Mage"]["base_mana"][9] == float(pes("Mage", 10)["BaseMana"])


def test_missing_gametable_is_absent(tables):
    gts = load_gametables(GT_DIR, RULES)
    gts["basemp"] = None
    doc = decode_character_scaling(tables, RULES, gts, LOCAL_VERSION)
    assert next(c for c in doc["crosscheck"] if c["value"] == "base_mana")["status"] == "absente"


def test_read_gametable_columns():
    table = read_gametable(GT_DIR / "xp.txt")
    assert table[0]["Level"] == 1 and len(table) == CAP


def test_character_errors(doc):
    assert character_errors(doc, CLASSES) == []
    broken = {**doc, "classes": {k: v for k, v in doc["classes"].items() if k != "Druid"}}
    assert any("Druid" in e for e in character_errors(broken, CLASSES))
    short = {**doc, "xp_to_next": doc["xp_to_next"][:-1]}
    assert any("xp_to_next" in e for e in character_errors(short, CLASSES))
    mage = {**doc["classes"]["Mage"], "base_mana": doc["classes"]["Mage"]["base_mana"][:-1]}
    gap = {**doc, "classes": {**doc["classes"], "Mage": mage}}
    assert any("Mage" in e and "base_mana" in e for e in character_errors(gap, CLASSES))


def test_decode_version_writes_character_file(tmp_path):
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand")
    vdir = candidate.root / LOCAL_VERSION
    assert (vdir / CHARACTER_FILE).is_file()
    sources = read_json(vdir / "sources.json")
    assert sources["files"][CHARACTER_FILE]["certainty"] == "certain"
    report = verify_version(isolated_deps(tmp_path), str(candidate.root))
    assert report["ok"], report["errors"]
    assert read_json(vdir / CHARACTER_FILE)["classes"]["Mage"]["base_mana"][0] == float(pes("Mage", 1)["BaseMana"])
