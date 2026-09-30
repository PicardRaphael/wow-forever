"""Sorts des 9 classes et classement PvP décodés du client (PV1, bloc B3 ; décisions 31, 106).

Fixture : `tests/fixtures/wago/1.60.1.70124/` (sorts nommés de chaque classe et de ses familiers). Valeurs attendues
lues dans la fixture (CSV du client), dans `decode_rules.json` ou dans `spells.json` des données, jamais écrites
dans le test."""

import csv
import re
from collections import defaultdict
from functools import cache

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, read_json

from forever.pipeline.decode import decode_classes


@cache
def csv_rows(name: str) -> tuple[dict[str, str], ...]:
    with (WAGO_70124 / "enUS" / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


@cache
def by_spell(name: str) -> dict[str, dict[str, str]]:
    return {r["SpellID"]: r for r in csv_rows(name) if r.get("DifficultyID", "0") == "0"}


@cache
def effects() -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for e in csv_rows("SpellEffect"):
        if e["DifficultyID"] == "0":
            out[e["SpellID"]].append(e)
    return out


@pytest.fixture(scope="module")
def doc(class_tables, decode_rules):
    return decode_classes(class_tables, decode_rules, LOCAL_VERSION)


def class_spell_ids(decode_rules, cls, pets=False):
    spec = decode_rules["classes"][cls]
    lines = {str(i) for i in spec.get("pet_skill_lines" if pets else "skill_lines", [])}
    methods = {str(m) for m in decode_rules["spell_ranks"]["acquire_methods"]}
    return {
        int(r["Spell"])
        for r in csv_rows("SkillLineAbility")
        if r["SkillLine"] in lines and r["AcquireMethod"] in methods
    }


def ranks_of(spells):
    return [(key, s, r) for key, s in spells.items() for r in s["ranks"]]


def test_class_spells_have_ranks_cooldown_duration_school_range(doc, decode_rules):
    durations = {r["ID"]: int(r["Duration"]) for r in csv_rows("SpellDuration")}
    ranges = {r["ID"]: r for r in csv_rows("SpellRange")}
    casts = {r["ID"]: int(r["Base"]) for r in csv_rows("SpellCastTimes")}
    subtext = {r["ID"]: r["NameSubtext_lang"] for r in csv_rows("Spell")}
    rank_re = re.compile(decode_rules["spell_ranks"]["rank_subtext"])
    channel_mask = decode_rules["spell_ranks"]["channel_attributes_1_mask"]
    misc, cooldowns, levels = by_spell("SpellMisc"), by_spell("SpellCooldowns"), by_spell("SpellLevels")
    for cls, c in doc["classes"].items():
        got = {r["spell_id"] for _, _, r in ranks_of(c["spells"])}
        assert got == class_spell_ids(decode_rules, cls), cls  # lignes de la classe, méthodes d'acquisition retenues
        assert got, cls
        for _key, spell, r in ranks_of(c["spells"]):
            sid = str(r["spell_id"])
            m = misc[sid]
            match = rank_re.match(subtext.get(sid, ""))
            assert r["rank"] == (int(match[1]) if match else None)
            cd = cooldowns.get(sid)
            recovery = max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) if cd else 0
            assert r["cooldown_s"] == (recovery / 1000 if recovery > 0 else None)
            gcd = int(cd["StartRecoveryTime"]) if cd else 0
            assert r["gcd_s"] == (gcd / 1000 if gcd > 0 else None)
            ms = durations[m["DurationIndex"]] if m["DurationIndex"] != "0" else 0
            assert r["duration_s"] == (ms / 1000 if ms > 0 else None)
            assert r["school"] == int(m["SchoolMask"])
            if m["RangeIndex"] == "0":
                assert r["range_yd"] is None
            else:
                row = ranges[m["RangeIndex"]]
                assert r["range_yd"] == {"min": float(row["RangeMin_0"]), "max": float(row["RangeMax_0"])}
            channel = bool(int(m["Attributes_1"]) & channel_mask)
            expected_cast = ms / 1000 if channel and ms > 0 else casts.get(m["CastingTimeIndex"], 0) / 1000
            assert r["cast_s"] == expected_cast
            assert r["level"] == (int(levels[sid]["BaseLevel"]) if sid in levels else None)
        numbered = [r["rank"] for r in spell["ranks"] if r["rank"] is not None]
        assert numbered == sorted(numbered)


def test_mage_part_matches_spells_json(doc, decode_rules):
    reference = read_json(DATA_DIR / LOCAL_VERSION / "spells.json")
    fields = reference["rank_format"]
    mana_type = decode_rules["spell_ranks"]["mana_power_type"]
    mage = doc["classes"]["Mage"]["spells"]
    for key in decode_rules["spells"]:
        ref = reference["spells"][key]
        (spell,) = [s for s in mage.values() if s["name"] == decode_rules["spells"][key]]
        ranked = [r for r in spell["ranks"] if r["rank"] is not None]
        assert [r["spell_id"] for r in ranked] == ref["source"]["rank_spell_ids"], key
        for got, row in zip(ranked, ref["ranks"], strict=True):
            want = dict(zip(fields, row, strict=True))
            cost = got["cost"]
            mana = cost["amount"] if cost and cost["power_type"] == mana_type and cost["amount"] > 0 else None
            assert (got["level"], got["cast_s"], mana, got["cooldown_s"] or 0) == (
                want["level"],
                want["cast_s"],
                want["mana"],
                want["cooldown_s"],
            ), key


def test_pvp_duration_read_when_present(doc):
    durations = {r["ID"]: int(r["Duration"]) for r in csv_rows("SpellDuration")}
    misc = by_spell("SpellMisc")
    seen = 0
    for c in doc["classes"].values():
        for _, _, r in ranks_of(c["spells"]):
            index = misc[str(r["spell_id"])]["PvPDurationIndex"]
            if index not in ("", "0"):
                assert r["pvp_duration_s"] == durations[index] / 1000
                seen += 1
            else:
                assert r["pvp_duration_s"] is None
    assert seen >= 1  # prémisse : un sort de classe de la fixture porte une durée PvP


def test_trigger_spell_is_followed_once(doc, decode_rules):
    rules = decode_rules["pvp_classification"]
    controls = {int(k) for k in rules["control_auras"]}
    hostile = {str(t) for t in rules["hostile_targets"]}
    aura_effects = {str(e) for e in rules["aura_effects"]}

    def carries_control(spell_id: str) -> bool:
        return any(
            e["Effect"] in aura_effects
            and int(e["EffectAura"]) in controls
            and {e["ImplicitTarget_0"], e["ImplicitTarget_1"]} & hostile
            for e in effects().get(spell_id, [])
        )

    followed = 0
    for c in doc["classes"].values():
        for spells in (c["spells"], c.get("pet_spells", {})):
            for spell in spells.values():
                ids = [str(r["spell_id"]) for r in spell["ranks"]]
                direct = {e["EffectTriggerSpell"] for sid in ids for e in effects().get(sid, [])} - {"0"}
                via = {str(v) for v in spell["pvp"].get("via", [])}
                assert via <= direct  # un seul niveau : seuls les sorts déclenchés directement
                own = any(carries_control(sid) for sid in ids)
                if not own and any(carries_control(t) for t in direct):
                    assert "control" in spell["pvp"]["kinds"]
                    assert str(spell["pvp"]["control"]["via"]) in direct
                    followed += 1
    assert followed >= 1  # prémisse : Charge -> Charge Stun, Spell Lock…


def test_pet_spells_belong_to_their_class(doc, decode_rules):
    skill = {r["ID"]: r["DisplayName_lang"] for r in csv_rows("SkillLine")}
    for cls, c in doc["classes"].items():
        pet_lines = decode_rules["classes"][cls].get("pet_skill_lines", [])
        if not pet_lines:
            assert not c.get("pet_spells")
            continue
        got = {r["spell_id"] for _, _, r in ranks_of(c["pet_spells"])}
        assert got == class_spell_ids(decode_rules, cls, pets=True) and got
        families = {skill[str(i)] for i in pet_lines}
        for spell in c["pet_spells"].values():
            assert spell["pet_families"] and set(spell["pet_families"]) <= families
    assert any(s["name"] == "Seduction" for s in doc["classes"]["Warlock"]["pet_spells"].values())


def test_every_spell_is_classified_or_unresolved(doc, decode_rules):
    rules = decode_rules["pvp_classification"]
    neutral = {str(m) for m in rules["neutral_mechanics"]} | {"0"}
    summons = set(rules["summon_effects"])
    categories = by_spell("SpellCategories")

    def marked(spell_id: str) -> bool:
        cat = categories.get(spell_id, {})
        if cat.get("Mechanic", "0") not in neutral or cat.get("DiminishType", "0") != "0":
            return True
        return any(e["EffectMechanic"] not in neutral or e["Effect"] in summons for e in effects().get(spell_id, []))

    unresolved_seen = 0
    for c in doc["classes"].values():
        listed = {u["key"]: u for u in c["unresolved_spells"]}
        for spells in (c["spells"], c.get("pet_spells", {})):
            for key, spell in spells.items():
                if any(marked(str(r["spell_id"])) for r in spell["ranks"]):
                    assert spell["pvp"]["kinds"] or key in listed, (key, spell["name"])
        for key, u in listed.items():
            assert key in c["spells"] or key in c.get("pet_spells", {})
            assert u["reason"]
            unresolved_seen += 1
    assert unresolved_seen >= 1  # prémisse : Freezing Trap (objet invoqué), Grounding Totem (créature)


def test_classification_certainty_per_field(doc):
    categories = by_spell("SpellCategories")
    checked = 0
    for c in doc["classes"].values():
        for spell in c["spells"].values():
            assert spell["certainty"] == f"FC-{LOCAL_VERSION}"  # champs du client : certains
            assert spell["pvp"]["certainty"] == "probable"  # classement par la table des règles
            control = spell["pvp"].get("control")
            if control is not None and control["via"] is None:
                top = str(spell["ranks"][-1]["spell_id"])
                assert control["diminish"] == int(categories.get(top, {}).get("DiminishType", 0))
                assert control["mechanic"] == int(categories.get(top, {}).get("Mechanic", 0)) or control["mechanic"]
                checked += 1
    assert checked >= 5


def test_known_roles_of_sample_spells(doc):
    """Rôles attendus de quelques sorts nommés de la fixture (échantillon du plan) : le classement suit la table."""

    def spell(cls, name, pets=False):
        pool = doc["classes"][cls]["pet_spells" if pets else "spells"]
        (found,) = [s for s in pool.values() if s["name"] == name]
        return found["pvp"]["kinds"]

    assert "control" in spell("Rogue", "Kidney Shot")
    assert "interrupt" in spell("Rogue", "Kick")
    assert "defensive" in spell("Paladin", "Divine Shield")
    assert "dispel" in spell("Paladin", "Cleanse")
    assert "mobility" in spell("Mage", "Blink")
    assert "control" not in spell("Mage", "Ice Block")  # contrôle sur soi : pas un contrôle
    assert "control" in spell("Warlock", "Seduction", pets=True)


def test_community_positions_are_separate_and_probable(doc, decode_rules):
    positions = decode_rules["community_positions"]
    for cls, c in doc["classes"].items():
        talents = {t["key"]: t for tree in c["trees"] for t in tree["talents"]}
        wanted = {k: v for k, v in positions.get(cls, {}).items() if isinstance(v, dict)}
        for key, t in talents.items():
            if key in wanted:
                assert t["tier"] is None and t["unresolved"]  # le palier décodé reste inconnu
                assert t["tier_community"] == {
                    "tier": wanted[key]["tier"],
                    "sources": wanted[key]["sources"],
                    "certainty": "probable",
                }
            else:
                assert "tier_community" not in t
    assert positions["Warlock"]


def test_dispels_carry_their_direction(doc):
    """Relecture de PV1 : une dissipation vise un allié (Cleanse) ou un ennemi (Purge), d'après ses cibles."""
    paladin = {s["name"]: s for s in doc["classes"]["Paladin"]["spells"].values()}
    shaman = {s["name"]: s for s in doc["classes"]["Shaman"]["spells"].values()}
    assert paladin["Cleanse"]["pvp"]["dispel"]["targets"] == ["allié"]
    assert shaman["Purge"]["pvp"]["dispel"]["targets"] == ["ennemi"]
