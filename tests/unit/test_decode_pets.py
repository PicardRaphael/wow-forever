"""Système de familiers du Chasseur décodé du client (CH0, bloc A) : `pets.json`.

Valeurs attendues lues dans les fixtures (`tests/fixtures/wago/1.60.1.70124/`, extraites du cache de `forever fetch`
par `scripts/extract_class_fixtures.py`) : chaque valeur est retrouvée par nom (famille, capacité, « Rank N »)
dans les lignes de la fixture, jamais écrite dans le test. Règles de lecture : `decode_rules.json` (`pets`)."""

import csv
import json
import re

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, PREVIOUS_VERSION, WAGO_70009, WAGO_70124, isolated_deps, read_json

from forever.pipeline.decode import decode_version
from forever.pipeline.pets import PETS_FILE, decode_pets, load_pet_tables, pet_table_files
from forever.pipeline.verify import verify_version

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
PETS = RULES["pets"]
COST = PETS["training_cost_column"]


def rows(table: str, locale: str = "enUS") -> list[dict[str, str]]:
    with (WAGO_70124 / locale / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


NAMES = {r["ID"]: r["Name_lang"] for r in rows("SpellName")}
NAMES_FR = {r["ID"]: r["Name_lang"] for r in rows("SpellName", "frFR")}
SUBTEXT = {r["ID"]: r["NameSubtext_lang"] for r in rows("Spell")}
LINE_ID = {}
for _r in rows("SkillLine"):
    LINE_ID.setdefault(_r["DisplayName_lang"], []).append(_r["ID"])
SLA = rows("SkillLineAbility")
EFFECTS = [r for r in rows("SpellEffect") if r["DifficultyID"] == "0"]
FAMILY = {r["Name_lang"]: r for r in rows("CreatureFamily")}
FAMILY_FR = {r["ID"]: r["Name_lang"] for r in rows("CreatureFamily", "frFR")}


def key_of(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def hunter_lines() -> set[str]:
    return {r["SkillLine"] for r in SLA if NAMES.get(r["Spell"]) == PETS["hunter_marker"]}


def line_spell(line: str, name: str, rank: int) -> dict[str, str]:
    """Ligne de SkillLineAbility de la capacité `name` au rang `rank` dans la ligne `line`."""
    found = [
        r
        for r in SLA
        if r["SkillLine"] == line and NAMES.get(r["Spell"]) == name and SUBTEXT.get(r["Spell"]) == f"Rank {rank}"
    ]
    assert len(found) == 1, (line, name, rank)
    return found[0]


def ranks_in_line(line: str, name: str) -> list[int]:
    return sorted(
        int(SUBTEXT[r["Spell"]].split()[1])
        for r in SLA
        if r["SkillLine"] == line and NAMES.get(r["Spell"]) == name and SUBTEXT.get(r["Spell"], "").startswith("Rank ")
    )


def spell_level(spell: str) -> dict[str, str]:
    return next(r for r in rows("SpellLevels") if r["SpellID"] == spell and r["DifficultyID"] == "0")


WOLF_LINE = FAMILY["Wolf"]["SkillLine_0"]
CROC_LINE = FAMILY["Crocolisk"]["SkillLine_0"]


@pytest.fixture(scope="module")
def doc():
    return decode_pets(load_pet_tables(WAGO_70124, RULES), RULES, LOCAL_VERSION)


# --- Tables et familles ----------------------------------------------------------------------------


def test_pet_tables_come_from_the_rules():
    files = dict(pet_table_files(RULES))
    assert set(RULES["pet_tables"]) <= set(files) and files["CreatureFamily"] == "enUS/CreatureFamily.csv"
    assert files["frFR/CreatureFamily"] == "frFR/CreatureFamily.csv"


def test_families_are_the_hunter_lines_of_the_fixture(doc):
    expected = {key_of(name) for name, r in FAMILY.items() if r["SkillLine_0"] in hunter_lines()}
    assert set(doc["families"]) == expected and "wolf" in expected
    # ligne de démon (« Warlock Pet Scaling ») : famille du client, jamais familière du Chasseur
    assert key_of("Imp") not in doc["families"] and FAMILY["Imp"]["SkillLine_0"] in LINE_ID["Pet - Imp"]
    for key, fam in doc["families"].items():
        assert fam["abilities"], key


def test_family_key_names_and_lines(doc):
    wolf = doc["families"]["wolf"]
    assert wolf["family_id"] == int(FAMILY["Wolf"]["ID"])
    assert wolf["name"] == {"en": "Wolf", "fr": FAMILY_FR[FAMILY["Wolf"]["ID"]]}
    assert wolf["skill_lines"] == [int(FAMILY["Wolf"][c]) for c in ("SkillLine_0", "SkillLine_1")]
    assert wolf["skill_line_name"] == "Pet - Wolf"


def test_crocilisk_spelling_gap_is_an_alias_and_an_observation(doc):
    croc = doc["families"]["crocolisk"]
    assert croc["skill_line_name"] == "Pet - Crocilisk" and CROC_LINE in LINE_ID["Pet - Crocilisk"]
    assert doc["aliases"]["crocilisk"] == "crocolisk"
    assert any("Crocilisk" in o and "Crocolisk" in o for o in doc["observations"])


def test_orphan_skill_line_is_listed_not_merged(doc):
    targeted = {r["SkillLine_0"] for r in FAMILY.values()}
    orphans = [line for line in LINE_ID["Pet - Bat"] if line not in targeted]
    assert len(orphans) == 1
    listed = {o["skill_line"]: o for o in doc["orphan_skill_lines"]}
    assert int(orphans[0]) in listed and listed[int(orphans[0])]["name"] == "Pet - Bat"
    assert listed[int(orphans[0])]["abilities"]


# --- Capacités et rangs ----------------------------------------------------------------------------


def test_ranks_follow_the_rank_subtext(doc):
    bite = doc["abilities"]["bite"]
    expected = ranks_in_line(WOLF_LINE, "Bite")
    assert [r["rank"] for r in bite["ranks"]] == expected == list(range(1, len(expected) + 1))
    for r in bite["ranks"]:
        assert r["spell_id"] == int(line_spell(WOLF_LINE, "Bite", r["rank"])["Spell"])


def test_supercedes_spell_does_not_order_ranks(doc):
    # Bite rang 2 : SupercedesSpell renseigné dans la ligne du Loup, nul dans celle du Crocilisk ; le rang suit le
    # sous-titre du sort, la chaîne n'est qu'un recoupement.
    wolf2, croc2 = line_spell(WOLF_LINE, "Bite", 2), line_spell(CROC_LINE, "Bite", 2)
    assert wolf2["Spell"] == croc2["Spell"] and wolf2["SupercedesSpell"] != croc2["SupercedesSpell"]
    assert [r["rank"] for r in doc["abilities"]["bite"]["ranks"]][:2] == [1, 2]


def test_rank_level_is_the_spell_level(doc):
    dash1 = line_spell(WOLF_LINE, "Dash", 1)["Spell"]
    lv = spell_level(dash1)
    assert lv["BaseLevel"] != lv["SpellLevel"]  # la fixture distingue les deux colonnes
    rank1 = doc["abilities"]["dash"]["ranks"][0]
    assert rank1["level"] == int(lv[PETS["rank_level_field"]])


def test_training_cost_raw_per_family_and_common_value_per_rank(doc):
    def costs(line: str, name: str) -> list[int]:
        return [int(line_spell(line, name, n)[COST]) for n in ranks_in_line(line, name)]

    wolf, croc = doc["families"]["wolf"], doc["families"]["crocolisk"]
    assert wolf["training_costs"]["bite"] == costs(WOLF_LINE, "Bite")
    assert wolf["training_costs"]["dash"] == costs(WOLF_LINE, "Dash")
    assert croc["training_costs"]["dash"] == costs(CROC_LINE, "Dash")
    assert costs(WOLF_LINE, "Dash") != costs(CROC_LINE, "Dash")  # la fixture porte un coût qui diffère
    # rang : valeur commune à toutes les familles, sinon null (jamais un 0 interprété)
    assert [r["training_cost"] for r in doc["abilities"]["bite"]["ranks"]] == costs(WOLF_LINE, "Bite")
    assert all(r["training_cost"] is None for r in doc["abilities"]["dash"]["ranks"])
    assert doc["abilities"]["bite"]["certainty"]["training_cost"] == "probable"


def test_focus_cost_and_cooldown(doc):
    spell = line_spell(WOLF_LINE, "Bite", 1)["Spell"]
    power = next(
        r for r in rows("SpellPower") if r["SpellID"] == spell and int(r["PowerType"]) == PETS["focus_power_type"]
    )
    cd = next(r for r in rows("SpellCooldowns") if r["SpellID"] == spell and r["DifficultyID"] == "0")
    rank1 = doc["abilities"]["bite"]["ranks"][0]
    assert rank1["focus_cost"] == int(power["ManaCost"])
    assert rank1["cooldown_s"] == max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) / 1000


def test_ability_names_kind_and_families(doc):
    bite = doc["abilities"]["bite"]
    spell = line_spell(WOLF_LINE, "Bite", 1)["Spell"]
    assert bite["name"] == {"en": "Bite", "fr": NAMES_FR[spell]}
    assert bite["kind"] == "family" and {"wolf", "crocolisk"} <= set(bite["families"])
    assert "bite" in doc["families"]["wolf"]["abilities"]
    assert doc["abilities"]["growl"]["kind"] == "general"


def test_description_template_and_tooltip_values(doc):
    spell = line_spell(WOLF_LINE, "Bite", 1)["Spell"]
    template = next(r["Description_lang"] for r in rows("Spell") if r["ID"] == spell)
    rank1 = doc["abilities"]["bite"]["ranks"][0]
    assert rank1["description"] == template
    assert rank1["tooltip_values"] and all(isinstance(v, int | float) for v in rank1["tooltip_values"])


def test_trained_rank_points_to_its_beast_training_spell(doc):
    target = line_spell(WOLF_LINE, "Bite", 1)["Spell"]
    trained = set(LINE_ID["Beast Training"])
    teach = [
        e["SpellID"]
        for e in EFFECTS
        if e["EffectTriggerSpell"] == target
        and int(e["Effect"]) == RULES["pvp_classification"]["learn_spell_effect"]
        and any(r["SkillLine"] in trained and r["Spell"] == e["SpellID"] for r in SLA)
    ]
    assert len(teach) == 1
    assert doc["abilities"]["bite"]["ranks"][0]["teach_spell_id"] == int(teach[0])


def test_attack_speed_passives_ranked_by_roman_numeral(doc):
    faster = doc["abilities"]["faster-attack"]
    assert faster["kind"] == "attack_speed"
    ids = {n: s for s, n in NAMES.items() if n.startswith("Faster Attack ")}
    roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
    generic = set(LINE_ID["Pet - Generic"])
    in_line = {n for n, s in ids.items() if any(r["Spell"] == s and r["SkillLine"] in generic for r in SLA)}
    assert [r["rank"] for r in faster["ranks"]] == sorted(roman[n.split()[-1]] for n in in_line)
    first = faster["ranks"][0]
    effect = next(e for e in EFFECTS if e["SpellID"] == str(first["spell_id"]) and e["EffectIndex"] == "0")
    assert first["effects"][0] == {
        "aura": int(effect["EffectAura"]),
        "misc": int(effect["EffectMiscValue_0"]),
        "base_points": float(effect["EffectBasePointsF"]),
    }


# --- Bonus, régime, mise à l'échelle, cartes --------------------------------------------------------


def test_family_bonus_from_the_line_passive(doc):
    bonus_auras = PETS["family_bonus"]
    passives = [
        r["Spell"]
        for r in SLA
        if r["SkillLine"] == WOLF_LINE
        and NAMES.get(r["Spell"]) == PETS["family_passive"]
        and {int(e["EffectAura"]) for e in EFFECTS if e["SpellID"] == r["Spell"]}
        >= {v["aura"] for v in bonus_auras.values()}
    ]
    assert len(passives) == 1
    wolf = doc["families"]["wolf"]
    assert wolf["passive_spell"] == int(passives[0])
    for field, spec in bonus_auras.items():
        effect = next(e for e in EFFECTS if e["SpellID"] == passives[0] and int(e["EffectAura"]) == spec["aura"])
        assert wolf["bonus"][field] == float(effect["EffectBasePointsF"]), field
    assert wolf["certainty"]["bonus"] == "probable"


def test_diet_from_food_mask_bits(doc):
    foods = {int(r["ID"]): r["Name_lang"] for r in rows("ItemPetFood")}
    foods_fr = {int(r["ID"]): r["Name_lang"] for r in rows("ItemPetFood", "frFR")}
    for name in ("Wolf", "Crocolisk"):
        mask = int(FAMILY[name]["PetFoodMask"])
        expected = [{"id": i, "en": foods[i], "fr": foods_fr[i]} for i in sorted(foods) if mask & (1 << (i - 1))]
        fam = doc["families"][key_of(name)]
        assert fam["diet"] == expected and expected, name
        assert fam["food_mask"] == mask and fam["certainty"]["diet"] == "probable"


def test_hunter_pet_scaling_effects_listed_as_probable(doc):
    spell = next(s for s, n in NAMES.items() if n == PETS["hunter_marker"])
    effects = sorted((e for e in EFFECTS if e["SpellID"] == spell), key=lambda e: int(e["EffectIndex"]))
    scaling = doc["pet_scaling"]
    assert scaling["spell_id"] == int(spell) and scaling["certainty"] == "probable"
    assert scaling["effects"] == [
        {
            "aura": int(e["EffectAura"]),
            "misc": int(e["EffectMiscValue_0"]),
            "base_points": float(e["EffectBasePointsF"]),
        }
        for e in effects
    ]


def test_maps_names_and_continent_by_parent_chain(doc):
    maps = {r["Name_lang"]: r for r in rows("UiMap")}
    fr = {r["ID"]: r["Name_lang"] for r in rows("UiMap", "frFR")}
    barrens = maps["The Barrens"]
    entry = doc["maps"][barrens["ID"]]
    assert entry["name"] == {"en": "The Barrens", "fr": fr[barrens["ID"]]}
    assert entry["parent"] == int(barrens["ParentUiMapID"])
    continent = int(barrens["ParentUiMapID"])
    by_id = {r["ID"]: r for r in rows("UiMap")}
    while int(by_id[str(continent)]["Type"]) != PETS["map_types"]["continent"]:
        continent = int(by_id[str(continent)]["ParentUiMapID"])
    assert entry["continent"] == continent
    # carte sans continent dans sa chaîne de parents : continent null, jamais deviné
    orphan = next(
        r for r in rows("UiMap") if r["ParentUiMapID"] == "0" and int(r["Type"]) != PETS["map_types"]["continent"]
    )
    assert doc["maps"][orphan["ID"]]["continent"] is None


def test_hunter_spells_are_names_referring_to_classes_json(doc):
    assert doc["hunter_spells"] == {"file": "classes.json", "class": "Hunter", "names": PETS["hunter_spells"]}


def test_output_is_deterministic(doc):
    again = decode_pets(load_pet_tables(WAGO_70124, RULES), RULES, LOCAL_VERSION)
    assert json.dumps(again, sort_keys=True) == json.dumps(doc, sort_keys=True)
    assert doc["build"] == LOCAL_VERSION and doc["schema_version"] == 1


# --- Version candidate -----------------------------------------------------------------------------


def test_candidate_from_pet_tables_carries_pets_json(tmp_path):
    deps = isolated_deps(tmp_path)
    cand = decode_version(deps, LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand")
    path = cand.root / LOCAL_VERSION / PETS_FILE
    assert path.is_file() and read_json(path)["families"]
    entry = read_json(cand.root / LOCAL_VERSION / "sources.json")["files"][PETS_FILE]
    assert entry["certainty"] == "certain" and any("probable" in n for n in entry["notes"])
    report = verify_version(deps, str(cand.root))
    assert report["ok"], report["errors"]


def test_candidate_without_pet_tables_inherits_pets_json(tmp_path):
    deps = isolated_deps(tmp_path)
    cand = decode_version(deps, PREVIOUS_VERSION, csv_dir=WAGO_70009, out=tmp_path / "cand")
    assert read_json(cand.root / PREVIOUS_VERSION / PETS_FILE)["inherited_from"] == LOCAL_VERSION
    assert any(o.startswith(f"{PETS_FILE} hérité de {LOCAL_VERSION}") for o in cand.observations)


def test_read_pets_from_a_version(tmp_path):
    from forever.gamedata import read_pets
    from forever.store import VersionData, current_identity, read_sources

    deps = isolated_deps(tmp_path)
    cand = decode_version(deps, LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand")
    identity = current_identity(cand.root)
    version = VersionData(
        identity.game_version, identity.data_sha, cand.root / LOCAL_VERSION, read_sources(cand.root, LOCAL_VERSION)
    )
    assert read_pets(version)["families"]["wolf"]["name"]["en"] == "Wolf"
    (cand.root / LOCAL_VERSION / PETS_FILE).unlink()
    assert read_pets(version) is None
