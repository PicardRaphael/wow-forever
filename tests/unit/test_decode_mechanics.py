"""Mécaniques décodées du client (T08b, bloc B) : aura d'Ignite (durée, période, cumul), Winter's Chill (critique
par cumul, cumuls), premier niveau à points de talent (`NumTalentsAtLevel`) et points par palier (`TraitCond`).

Valeurs attendues lues dans les fixtures (`tests/fixtures/wago/1.60.1.70124/`), ligne et colonne nommées."""

import csv

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, read_json

from forever.pipeline.character_scaling import decode_character_scaling, load_character_tables, load_gametables
from forever.pipeline.decode import decode_scaling, load_class_tables

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


def rows(table: str) -> list[dict[str, str]]:
    with (WAGO_70124 / "enUS" / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def spell_id(name: str, aura: int) -> int:
    """Identifiant du sort nommé `name` qui porte l'aura `aura` (SpellName, SpellEffect des fixtures)."""
    ids = {r["ID"] for r in rows("SpellName") if r["Name_lang"] == name}
    return next(int(r["SpellID"]) for r in rows("SpellEffect") if r["SpellID"] in ids and int(r["EffectAura"]) == aura)


@pytest.fixture(scope="module")
def scaling():
    return decode_scaling(load_class_tables(WAGO_70124, RULES), RULES, LOCAL_VERSION)


@pytest.fixture(scope="module")
def character():
    tables = load_character_tables(WAGO_70124, RULES)
    return decode_character_scaling(tables, RULES, load_gametables(WAGO_70124 / "gametables", RULES), LOCAL_VERSION)


def test_ignite_aura_equals_client_rows(scaling):
    spec = RULES["mechanic_auras"]["ignite"]
    sid = spell_id(spec["aura_spell"], spec["periodic_aura"])
    effect = next(
        r for r in rows("SpellEffect") if int(r["SpellID"]) == sid and int(r["EffectAura"]) == spec["periodic_aura"]
    )
    misc = next(r for r in rows("SpellMisc") if int(r["SpellID"]) == sid)
    duration = next(int(r["Duration"]) for r in rows("SpellDuration") if r["ID"] == misc["DurationIndex"])
    options = next(r for r in rows("SpellAuraOptions") if int(r["SpellID"]) == sid)
    ignite = scaling["auras"]["ignite"]
    assert ignite == {
        "spell_id": sid,
        "duration_ms": duration,
        "period_ms": int(effect["EffectAuraPeriod"]),
        "cumulative": int(options["CumulativeAura"]),
    }


def test_winters_chill_equals_client_rows(scaling):
    spec = RULES["target_auras"]["winters_chill"]  # même lecture que Fire Vulnerability (aura posée par le talent)
    talent_ids = {r["ID"] for r in rows("SpellName") if r["Name_lang"] == spec["talent"]}
    trigger = next(
        int(r["EffectTriggerSpell"])
        for r in rows("SpellEffect")
        if r["SpellID"] in talent_ids and int(r["EffectTriggerSpell"]) != 0
    )
    effect = next(
        r for r in rows("SpellEffect") if int(r["SpellID"]) == trigger and int(r["EffectAura"]) == spec["aura"]
    )
    options = next(r for r in rows("SpellAuraOptions") if int(r["SpellID"]) == trigger)
    wc = scaling["auras"]["winters_chill"]
    assert (wc["spell_id"], wc["max_stacks"]) == (trigger, int(options["CumulativeAura"]))
    assert wc["pct_per_stack"] == float(effect["EffectBasePointsF"])


def test_first_talent_level_equals_num_talents_at_level(character):
    first = min(int(r["ID"]) for r in rows("NumTalentsAtLevel") if int(r["NumTalents"]) > 0)
    assert character["talents"]["first_level"] == first


def test_points_per_tier_equals_trait_cond_step(character):
    lines = {str(v) for v in RULES["skill_lines"].values()}
    tree = next(r["TraitTreeID"] for r in rows("SkillLineXTraitTree") if r["SkillLineID"] in lines)
    spent = sorted({int(r["SpentAmountRequired"]) for r in rows("TraitCond") if r["TraitTreeID"] == tree} - {0})
    step = spent[0]
    assert spent == [step * (i + 1) for i in range(len(spent))]
    assert character["talents"]["points_per_tier"]["Mage"] == step
