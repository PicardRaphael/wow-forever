"""Bonus d'XP décodés du client (`xp_bonuses.json`), T04f, bloc A.

Valeurs attendues lues dans les fixtures `tests/fixtures/wago/xp_bonuses/enUS/` (lignes des tables de 1.60.1.70338
extraites par `scripts/extract_xp_bonus_fixtures.py`) ; les identifiants désignent des lignes du client. Aucun réseau."""

import csv
import re
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.pipeline.decode import decode_version
from forever.pipeline.verify import verify_version
from forever.pipeline.xp_bonuses import (
    XP_BONUS_FILE,
    decode_xp_bonuses,
    load_xp_bonus_tables,
    xp_bonus_gate_files,
    xp_bonuses_errors,
)

CSV_DIR = FIXTURES / "wago" / "xp_bonuses"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
WELL_RESTED, TRACKING, UNROLL, BAG = 429959, 429960, 429961, 211527
FOOD_XP, CONDITION = 1243969, 142418
LEGACY_RESTED = 1225478
NO_SOURCE = (436412, 335924, 362859, 430496)
TENT = 1307230


def rows(table):
    with (CSV_DIR / "enUS" / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def spell_rows(table, spell):
    return [r for r in rows(table) if int(r["SpellID"]) == spell]


def duration_ms(spell):
    index = spell_rows("SpellMisc", spell)[0]["DurationIndex"]
    return int(next(r for r in rows("SpellDuration") if r["ID"] == index)["Duration"])


def base_points(spell):
    return {int(r["EffectAura"]): float(r["EffectBasePointsF"]) for r in spell_rows("SpellEffect", spell)}


@pytest.fixture(scope="module")
def doc():
    return decode_xp_bonuses(load_xp_bonus_tables(CSV_DIR, RULES), RULES, LOCAL_VERSION)


def aura(doc, spell):
    return next(a for a in doc["auras"] if a["spell_id"] == spell)


def test_document_is_well_formed(doc):
    assert doc["build"] == LOCAL_VERSION
    assert xp_bonuses_errors(doc) == []
    assert xp_bonuses_errors([]) != []


def test_every_xp_aura_of_the_fixture_is_listed(doc):
    codes = {int(c) for c in RULES["xp_bonuses"]["aura_codes"]}
    apply_aura = int(RULES["xp_bonuses"]["apply_aura_effect"])
    expected = {
        int(r["SpellID"])
        for r in rows("SpellEffect")
        if int(r["Effect"]) == apply_aura and int(r["EffectAura"]) in codes
    }
    assert {a["spell_id"] for a in doc["auras"]} == expected
    assert {WELL_RESTED, FOOD_XP, LEGACY_RESTED, *NO_SOURCE} <= expected


def test_well_rested_duration_stacks_and_values_come_from_the_client(doc):
    a = aura(doc, WELL_RESTED)
    stacks = int(spell_rows("SpellAuraOptions", WELL_RESTED)[0]["CumulativeAura"])
    assert a["duration_ms"] == duration_ms(WELL_RESTED) and a["max_stacks"] == stacks
    values = {e["aura"]: e["base_points"] for e in a["effects"]}
    assert values == {k: v for k, v in base_points(WELL_RESTED).items()}
    assert {e["key"] for e in a["effects"]} == {"kill_xp_pct", "quest_xp_pct"}
    assert a["access"] == "item" and [i["item"] for i in a["items"]] == [BAG]
    assert a["certainty"]["values"] == "certain" and a["certainty"]["meaning"] == "probable"


def test_food_xp_boost_is_a_kill_bonus_reached_by_nutritious_food(doc):
    a = aura(doc, FOOD_XP)
    nonzero = {e["key"]: e["base_points"] for e in a["effects"] if e["base_points"]}
    kill_code = next(int(c) for c, s in RULES["xp_bonuses"]["aura_codes"].items() if s["key"] == "kill_xp_pct")
    assert nonzero == {"kill_xp_pct": base_points(FOOD_XP)[kill_code]}
    assert a["access"] == "food" and a["condition"] == CONDITION
    assert a["duration_ms"] is None and a["permanent"] is True
    referencing = {int(r["ID"]) for r in rows("Spell") if f"$@spelldesc{FOOD_XP}" in r["Description_lang"]}
    assert {f["spell"] for f in doc["food"]} <= referencing and doc["food"]
    sparse = {int(r["ID"]): r for r in rows("ItemSparse")}
    for food in doc["food"]:
        assert food["required_level"] == int(sparse[food["item"]]["RequiredLevel"])
        assert food["xp_aura"] == FOOD_XP and food["buff_duration_ms"] == duration_ms(food["buff_spell"])


def test_condition_of_the_food_bonus_is_decoded_without_guessing(doc):
    row = next(r for r in rows("PlayerCondition") if int(r["ID"]) == CONDITION)
    cond = doc["conditions"][str(CONDITION)]
    fields = cond["fields"]
    assert fields["WorldStateExpressionID"]["value"] == int(row["WorldStateExpressionID"])
    assert fields["Flags"]["value"] == int(row["Flags"]) and fields["Flags"]["meaning"] == "inconnu"
    assert "MinLevel" not in fields  # valeur nulle : non listée
    assert cond["readable_in_client"] is False


def test_legacy_well_rested_ranks_come_from_the_curves(doc):
    a = aura(doc, LEGACY_RESTED)
    assert a["access"] == "legacy"
    legacy = a["legacy"]
    node_entries = {r["TraitNodeEntryID"] for r in rows("TraitNodeXTraitNodeEntry")}
    entry = next(
        r
        for r in rows("TraitNodeEntry")
        if r["ID"] in node_entries and int(r["TraitDefinitionID"]) == legacy["trait_definition"]
    )
    assert legacy["max_ranks"] == int(entry["MaxRanks"])
    points = [
        r for r in rows("TraitDefinitionEffectPoints") if int(r["TraitDefinitionID"]) == legacy["trait_definition"]
    ]
    curves = {r["EffectIndex"]: r["CurveID"] for r in points}
    for index, curve in curves.items():
        expected = [
            float(p["Pos_1"])
            for p in sorted((p for p in rows("CurvePoint") if p["CurveID"] == curve), key=lambda p: float(p["Pos_0"]))
        ]
        assert legacy["ranks"][index] == expected
    tree = next(r for r in rows("TraitNode") if int(r["ID"]) == legacy["node"])["TraitTreeID"]
    assert legacy["tree"] == int(tree)
    assert {e["key"] for e in a["effects"]} >= {"rested_rate_pct", "rested_cap_pct"}


def test_bonuses_without_a_player_source_are_not_accessible(doc):
    for spell in NO_SOURCE:
        assert aura(doc, spell)["access"] == "none", spell


def test_sleeping_bag_chain_is_read_from_the_client(doc):
    bag = doc["sleeping_bag"]
    effect = next(r for r in rows("ItemEffect") if int(r["SpellID"]) == UNROLL)
    tracking = next(r for r in spell_rows("SpellEffect", TRACKING) if int(r["EffectTriggerSpell"]) == WELL_RESTED)
    assert (bag["item"], bag["use_spell"], bag["tracking_aura"], bag["aura"]) == (BAG, UNROLL, TRACKING, WELL_RESTED)
    assert bag["item_cooldown_ms"] == int(effect["CategoryCoolDownMSec"])
    assert bag["bag_duration_ms"] == duration_ms(UNROLL)
    assert bag["stack_period_ms"] == int(tracking["EffectAuraPeriod"])
    assert bag["max_stacks"] == aura(doc, WELL_RESTED)["max_stacks"]
    name = next(r for r in rows("ItemSparse") if int(r["ID"]) == BAG)["Display_lang"]
    assert bag["name"] == name


def test_camp_tent_threshold_and_benefits_without_xp(doc):
    camp = doc["camp"]
    index = int(RULES["xp_bonuses"]["camp"]["tent_threshold_effect"])
    effect = next(r for r in spell_rows("SpellEffect", TENT) if int(r["EffectIndex"]) == index)
    assert camp["tent"]["spell"] == TENT
    assert camp["tent"]["threshold_pct_of_level"] == float(effect["EffectBasePointsF"])
    cooldown = int(RULES["xp_bonuses"]["camp"]["shared_cooldown"])
    assert camp["shared_cooldown"]["duration_ms"] == duration_ms(cooldown)
    assert camp["benefits"]["xp_bonus"] is False
    assert camp["fires"] and all(f["name"] for f in camp["fires"])


def test_no_game_number_in_the_decoder():
    source = (DATA_DIR.parent / "pipeline" / "xp_bonuses.py").read_text(encoding="utf-8")
    for number in (str(WELL_RESTED), str(BAG), str(FOOD_XP), str(TENT), str(CONDITION)):
        assert not re.search(rf"\b{number}\b", source), number


def test_gate_is_the_player_condition_table():
    assert [t for t, _ in xp_bonus_gate_files(RULES)] == RULES["xp_bonus_tables"] == ["PlayerCondition"]


def test_decode_version_writes_xp_bonuses_when_player_condition_is_present(tmp_path):
    csv_dir = tmp_path / "csv"
    shutil.copytree(WAGO_70124, csv_dir)
    shutil.copyfile(CSV_DIR / "enUS" / "PlayerCondition.csv", csv_dir / "enUS" / "PlayerCondition.csv")
    candidate = decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=csv_dir, out=tmp_path / "cand")
    vdir = candidate.root / LOCAL_VERSION
    written = read_json(vdir / XP_BONUS_FILE)
    assert "inherited_from" not in written and xp_bonuses_errors(written) == []
    sources = read_json(vdir / "sources.json")
    assert sources["files"][XP_BONUS_FILE]["certainty"] == "certain"
    report = verify_version(isolated_deps(tmp_path), str(candidate.root))
    assert report["ok"], report["errors"]


def test_installed_xp_bonuses_are_well_formed():
    doc = read_json(DATA_DIR / LOCAL_VERSION / XP_BONUS_FILE)
    assert xp_bonuses_errors(doc) == []
    assert aura(doc, WELL_RESTED)["max_stacks"] == int(spell_rows("SpellAuraOptions", WELL_RESTED)[0]["CumulativeAura"])
