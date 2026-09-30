"""Races, raciaux et bijoux PvP décodés du client (PV1, bloc B2 ; décision 106 ; D5).

Fixture : `tests/fixtures/wago/1.60.1.70124/` (raciaux des 9 lignes raciales, cinq bijoux qui rompent un contrôle,
trois leurres). Valeurs attendues lues dans la fixture, dans `decode_rules.json` ou dans `racials.json` (relevé
communautaire, comparaison de D5), jamais écrites dans le test."""

import csv
from functools import cache

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, read_json

from forever.pipeline.decode import decode_pvp_items, decode_races


@cache
def csv_rows(name: str, locale: str = "enUS") -> tuple[dict[str, str], ...]:
    with (WAGO_70124 / locale / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


@pytest.fixture(scope="module")
def races(class_tables, decode_rules):
    return decode_races(class_tables, decode_rules, LOCAL_VERSION)["races"]


@pytest.fixture(scope="module")
def trinkets(class_tables, decode_rules):
    return decode_pvp_items(class_tables, decode_rules, LOCAL_VERSION)


def class_names():
    return {int(r["ID"]): r["Name_lang"] for r in csv_rows("ChrClasses")}


def classes_of_mask(mask: int):
    names = class_names()
    if mask in (0, -1):
        return None
    return sorted(n for i, n in names.items() if mask & (1 << (i - 1)))


def race_mask(row) -> int:
    low, high = int(row["RaceMasks_0"]), int(row["RaceMasks_1"])
    return -1 if low == -1 else (low & 0xFFFFFFFF) | (high << 32)


def test_races_and_allowed_classes_from_client(races, decode_rules):
    chr_races = {int(r["ID"]): r for r in csv_rows("ChrRaces")}
    french = {int(r["ID"]): r["Name_lang"] for r in csv_rows("ChrRaces", "frFR")}
    names = class_names()
    order = list(decode_rules["classes"])
    expected: dict[str, list[str]] = {}
    for r in csv_rows("CharBaseInfo"):
        race = chr_races[int(r["RaceID"])]["Name_lang"]
        expected.setdefault(race, []).append(names[int(r["ClassID"])])
    assert set(races) == set(expected)  # races jouables : celles de CharBaseInfo, sans liste de Classic
    for name, race in races.items():
        row = chr_races[race["id"]]
        assert row["Name_lang"] == name
        assert race["classes"] == sorted(set(expected[name]), key=order.index)
        assert race["client_file"] == row["ClientFileString"]
        assert race["name_fr"] == french[race["id"]]
        assert race["faction"] == decode_rules["race_factions"][row["Alliance"]]
    assert any(int(chr_races[r["id"]]["PlayableRaceBit"]) >= 32 for r in races.values())  # races de Forever


def test_racials_have_effect_cooldown_duration(races, decode_rules):
    chr_races = {int(r["ID"]): r for r in csv_rows("ChrRaces")}
    racial_lines = {str(i) for i in decode_rules["racial_skill_lines"]}
    abilities = [r for r in csv_rows("SkillLineAbility") if r["SkillLine"] in racial_lines]
    cooldowns = {r["SpellID"]: r for r in csv_rows("SpellCooldowns") if r["DifficultyID"] == "0"}
    misc = {r["SpellID"]: r for r in csv_rows("SpellMisc") if r["DifficultyID"] == "0"}
    durations = {r["ID"]: int(r["Duration"]) for r in csv_rows("SpellDuration")}
    effects = {}
    for e in csv_rows("SpellEffect"):
        if e["DifficultyID"] == "0":
            effects.setdefault(e["SpellID"], []).append(e)
    variants = 0
    for name, race in races.items():
        bit = 1 << int(chr_races[race["id"]]["PlayableRaceBit"])
        expected = {
            int(a["Spell"]): classes_of_mask(int(a["ClassMask"]))
            for a in abilities
            if race_mask(a) == -1 or race_mask(a) & bit
        }
        assert {r["spell_id"]: r["classes"] for r in race["racials"]} == expected, name
        assert race["racials"], name  # chaque race jouable a ses raciaux, Skyborne compris (RaceMasks_1)
        by_name: dict[str, list] = {}
        for r in race["racials"]:
            sid = str(r["spell_id"])
            passive = bool(int(misc[sid]["Attributes_0"]) & decode_rules["passive_attributes_0_mask"])
            assert r["passive"] is passive
            cd = cooldowns.get(sid)
            expected_cd = max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) / 1000 if cd else None
            assert r["cooldown_s"] == (expected_cd or None)
            index = int(misc[sid]["DurationIndex"])
            ms = durations[str(index)] if index else 0
            assert r["duration_s"] == (ms / 1000 if ms > 0 else None)  # -1 : jusqu'à annulation
            assert [(f["effect"], f["aura"]) for f in r["effects"]] == [
                (int(e["Effect"]), int(e["EffectAura"]))
                for e in sorted(effects[sid], key=lambda e: int(e["EffectIndex"]))
            ]
            by_name.setdefault(r["name"], []).append(r)
        for group in by_name.values():
            if len(group) > 1:  # variante par classe (Expansive Mind…) : classes disjointes
                variants += 1
                seen: set[str] = set()
                for r in group:
                    assert r["classes"] and not seen & set(r["classes"])
                    seen |= set(r["classes"])
    assert variants >= 1  # prémisse : la fixture porte un racial à variantes de classe


def test_mage_racial_values_equal_the_community_record(races):
    """D5 : les trois grandeurs raciales du moteur du Mage, lues dans le client, égales au relevé de racials.json ;
    un écart ici changerait les builds de T05 (arrêt avant le commit)."""
    record = read_json(DATA_DIR / LOCAL_VERSION / "racials.json")["races"]
    expected: dict[str, dict[str, float]] = {}
    for race, traits in record.items():
        for key, trait in traits.items():
            if not isinstance(trait, dict):
                continue
            if key == "sword_spec":
                expected.setdefault(race, {})["sword_crit"] = trait["crit"]
            for field in ("spirit_pct", "mana_pct"):
                if field in trait:
                    expected.setdefault(race, {})[field] = trait[field]
    decoded = {name: race["mage_values"] for name, race in races.items() if race["mage_values"]}
    assert decoded == expected


def test_pvp_trinkets_have_use_spell_and_cooldown(trinkets, decode_rules):
    rules = decode_rules["pvp_trinkets"]
    items = {r["ID"]: r for r in csv_rows("Item")}
    sparse = {r["ID"]: r for r in csv_rows("ItemSparse")}
    links = {r["ItemID"]: r["ItemEffectID"] for r in csv_rows("ItemXItemEffect")}
    item_effects = {r["ID"]: r for r in csv_rows("ItemEffect")}
    mechanics = {int(r["ID"]): r["StateName_lang"] for r in csv_rows("SpellMechanic")}
    listed = {t["item_id"]: t for t in trinkets["trinkets"]}
    assert len(listed) >= 4
    for item_id, t in listed.items():
        key = str(item_id)
        assert int(items[key]["InventoryType"]) == rules["inventory_type"]
        assert t["name"] == sparse[key]["Display_lang"]
        effect = item_effects[links[key]]
        assert int(effect["TriggerType"]) == rules["use_trigger"]
        assert t["spell_id"] == int(effect["SpellID"])
        assert t["cooldown_s"] == int(effect["CoolDownMSec"]) / 1000
        category = int(effect["CategoryCoolDownMSec"])
        assert t["category_cooldown_s"] == (category / 1000 if category > 0 else None)
        assert t["classes"] == classes_of_mask(int(sparse[key]["AllowableClass"]))
        assert t["breaks"] and all(b["mechanic_name"] == mechanics[b["mechanic"]] for b in t["breaks"])
        assert {b["kind"] for b in t["breaks"]} <= {"immunity", "dispel"}
    kinds = {b["kind"] for t in listed.values() for b in t["breaks"]}
    assert kinds == {"immunity", "dispel"}  # Insignes (immunité) et Recombobulator (dissipation)
    assert trinkets["shared_cooldown_with_racials"] is None  # non décidé par le client (registre K4)
    assert any("K4" in n for n in trinkets["notes"])


def test_non_trinket_decoy_is_ignored(trinkets, decode_rules):
    rules = decode_rules["pvp_trinkets"]
    listed = {t["item_id"] for t in trinkets["trinkets"]}
    items = {r["ID"]: r for r in csv_rows("Item")}
    sparse = {r["ID"] for r in csv_rows("ItemSparse")}
    not_trinket = [i for i, r in items.items() if int(r["InventoryType"]) != rules["inventory_type"]]
    no_name = [i for i in items if i not in sparse]
    assert not_trinket and no_name  # prémisses : leurres présents dans la fixture
    assert not {int(i) for i in not_trinket + no_name} & listed
    trinkets_in_fixture = {int(i) for i, r in items.items() if int(r["InventoryType"]) == rules["inventory_type"]}
    assert trinkets_in_fixture - listed - {int(i) for i in no_name}  # un bijou sans rupture de contrôle écarté
