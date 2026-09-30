"""Rangs des 15 sorts suivis décodés des tables du client (fixtures wago 1.60.1.70009).

Référence : forever/data/1.60.1.70009/spells.json. Un null de référence (coût non publié) n'est pas un écart :
la valeur du client est une observation. Les autres écarts sont comparés à confirmed_changes.json dans les deux
sens."""

import pytest
from conftest import (
    DATA_DIR,
    LOCAL_VERSION,
    PREVIOUS_VERSION,
    change_key,
    client_vs_reference,
    format_changes,
    read_json,
)

from forever.pipeline.decode import decode_spells

REFERENCE = read_json(DATA_DIR / LOCAL_VERSION / "spells.json")
DECODED_FIELDS = {"ranks", "name", "name_fr", "spell_ids"}


@pytest.fixture(scope="module")
def decoded(client_tables, decode_rules):
    # Les fixtures wago sont les tables de 1.60.1.70009 : c'est ce build qu'on décode ici.
    return decode_spells(client_tables, decode_rules, REFERENCE, PREVIOUS_VERSION)


@pytest.fixture(scope="module")
def spells(decoded):
    return decoded["spells"]


def test_fifteen_spells_ninety_nine_ranks(spells):
    assert list(spells) == list(REFERENCE["spells"])
    assert len(spells) == 15
    assert sum(len(s["ranks"]) for s in spells.values()) == 99


@pytest.mark.parametrize(
    ("key", "rank", "row"),
    [  # spells.json (rank_format : niveau, min, max, dot_total, dot_duration, cast_s, mana, cooldown_s)
        ("frostbolt", 2, [8, 34, 38, 0, 0, 1.8, 35, 0]),
        ("frostbolt", 11, [60, 457, 493, 0, 0, 3.0, 290, 0]),
        ("fireball", 3, [12, 48, 66, 6, 6, 2.5, 65, 0]),
        ("fireball", 1, [1, 16, 25, 2, 4, 1.5, 30, 0]),
        ("frostfire_bolt", 1, [40, 102, 119, 27, 9, 3.0, 205, 0]),
        ("arcane_missiles", 1, [8, 75, 75, 0, 0, 3.0, 85, 0]),
        ("blizzard", 1, [20, 200, 200, 0, 0, 8.0, 320, 0]),
        ("flamestrike", 1, [16, 55, 71, 44, 8, 3.0, 195, 0]),
        ("frost_nova", 1, [10, 21, 24, 0, 0, 0, 55, 25]),
        ("fire_blast", 1, [6, 27, 35, 0, 0, 0, 40, 8]),
        ("arcane_blast", 2, [30, 131, 152, 0, 0, 2.5, None, 0]),
    ],
)
def test_rank_values(spells, key, rank, row):
    assert REFERENCE["spells"][key]["ranks"][rank - 1] == row
    assert spells[key]["ranks"][rank - 1] == row


def test_fireball_has_two_level_60_ranks(spells):
    ranks = spells["fireball"]["ranks"]
    assert len(ranks) == 12 and [r[0] for r in ranks].count(60) == 2


def test_rank_count_per_spell(spells):
    assert {k: len(s["ranks"]) for k, s in spells.items()} == {
        k: len(s["ranks"]) for k, s in REFERENCE["spells"].items()
    }


def test_rows_follow_rank_format(decoded, spells):
    assert decoded["rank_format"] == REFERENCE["rank_format"]
    assert all(len(r) == len(decoded["rank_format"]) for s in spells.values() for r in s["ranks"])


def test_other_fields_are_inherited(decoded, spells):
    for key, ref in REFERENCE["spells"].items():
        kept = {k: v for k, v in spells[key].items() if k not in DECODED_FIELDS}
        assert kept == {k: v for k, v in ref.items() if k != "ranks"}, key
    assert decoded["utility"] == REFERENCE["utility"]
    assert decoded["inherited_from"] == PREVIOUS_VERSION
    assert decoded["build"] == PREVIOUS_VERSION


def test_names_and_client_ids(spells):
    assert spells["frostbolt"]["name"] == "Frostbolt"
    assert spells["frostbolt"]["name_fr"] == "Eclair de givre"  # fixture frFR/SpellName.csv
    assert spells["frostbolt"]["spell_ids"][0] == 116  # fixture SkillLineAbility
    assert all(s["name_fr"] for s in spells.values())
    assert all(len(s["spell_ids"]) == len(s["ranks"]) for s in spells.values())


def test_ranks_come_from_mage_skill_lines_only(client_tables, decode_rules, spells):
    lines = set(decode_rules["skill_lines"].values())
    methods = set(decode_rules["spell_ranks"]["acquire_methods"])
    allowed = {
        r["Spell"]
        for r in client_tables["SkillLineAbility"]
        if r["SkillLine"] in lines and r["AcquireMethod"] in methods
    }
    ids = {i for s in spells.values() for i in s["spell_ids"]}
    assert ids <= allowed
    names = {r["ID"]: r["Name_lang"] for r in client_tables["SpellName"]}
    homonyms = {i for i, n in names.items() if n == "Frostbolt"} - set(spells["frostbolt"]["spell_ids"])
    assert homonyms  # la fixture garde un Frostbolt de PNJ, écarté
    skipped = {r["Spell"] for r in client_tables["SkillLineAbility"] if names.get(r["Spell"]) == "Fire Blast"} - allowed
    assert skipped and not skipped & set(spells["fire_blast"]["spell_ids"])  # doublons AcquireMethod 3


# --- Écarts client ↔ référence -------------------------------------------------------------------


def test_null_reference_values_are_observations(candidate):
    _, observations, _ = client_vs_reference(candidate, "spell")
    assert {(c["key"], c["field"]) for c in observations} == {
        ("pyroblast", "ranks[1].mana"),
        ("ice_lance", "ranks[1].mana"),
        ("blast_wave", "ranks[1].mana"),
    }
    assert all(isinstance(c["new"], int) for c in observations)


def test_installed_observations_are_recorded(candidate):
    """T06b : les observations installées en révision 2 figurent dans confirmed_changes.json (nature client)."""
    _, observations, _ = client_vs_reference(candidate, "spell")
    recorded = [
        c for c in read_json(DATA_DIR / LOCAL_VERSION / "confirmed_changes.json")["changes"] if c["old"] is None
    ]
    assert sorted(map(change_key, recorded)) == sorted(map(change_key, observations))
    assert {c["nature"] for c in recorded} == {"client"}
    assert all(c["applied_in_revision"] == 2 for c in recorded)


def test_every_confirmed_spell_change_exists(candidate):
    gaps, _, confirmed = client_vs_reference(candidate, "spell")
    observed = {change_key(c) for c in gaps}
    missing = [c for c in confirmed if change_key(c) not in observed]
    assert not missing, "changements confirmés absents du décodage :\n" + format_changes(missing)


def test_no_other_spell_difference(candidate):
    gaps, _, confirmed = client_vs_reference(candidate, "spell")
    known = {change_key(c) for c in confirmed}
    unexpected = [c for c in gaps if change_key(c) not in known]
    assert not unexpected, f"{len(unexpected)} écart(s) client ↔ spells.json :\n" + format_changes(unexpected)
