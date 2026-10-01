"""Recoupement client ↔ Forever Bestiary ↔ Questie (CH0, bloc C) : chaque écart listé avec ses deux valeurs et leurs
sources ; deux sources concordantes ne donnent aucun écart ; rapport Markdown déterministe.

Client : `pets.json` décodé des fixtures wago ; addon : fixture synthétique `tests/fixtures/bestiary/` ; Questie :
fixture `tests/fixtures/questie/11.38.0`. Valeurs attendues relues dans ces fixtures."""

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, read_json

from forever.pets import GAP_KINDS, crosscheck, render_crosscheck_markdown
from forever.pipeline.bestiary import read_bestiary
from forever.pipeline.pets import decode_pets, family_key, load_pet_tables
from forever.pipeline.questie import read_questie

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


@pytest.fixture(scope="module")
def pets():
    return decode_pets(load_pet_tables(WAGO_70124, RULES), RULES, LOCAL_VERSION)


@pytest.fixture(scope="module")
def addon():
    return read_bestiary(FIXTURES / "bestiary" / "ForeverBestiary")


@pytest.fixture(scope="module")
def questie():
    return read_questie(FIXTURES / "questie" / "11.38.0")


@pytest.fixture(scope="module")
def report(pets, addon, questie):
    return crosscheck(pets, addon, questie)


def gaps(report, kind):
    return [g for g in report["gaps"] if g["kind"] == kind]


def test_every_gap_has_two_values_and_their_sources(report):
    assert report["gaps"]
    for g in report["gaps"]:
        assert g["kind"] in GAP_KINDS and g["subject"]
        assert len(g["values"]) == 2 and set(g["values"]) == set(g["sources"]), g
        assert all(g["sources"].values()), g


def test_sources_name_versions(report, addon, questie):
    sources = report["sources"]
    assert LOCAL_VERSION in sources["client"]
    assert addon["info"]["version"] in sources["addon"] and addon["info"]["date"] in sources["addon"]
    assert questie.info.version in sources["questie"]


def test_family_missing_on_each_side(report, pets, addon):
    client, theirs = set(pets["families"]), set(addon["families"])
    assert {g["subject"] for g in gaps(report, "family_missing_addon")} == client - theirs
    assert {g["subject"] for g in gaps(report, "family_missing_client")} == theirs - client
    assert theirs - client  # la fixture porte une famille inconnue du client


def test_bonus_gap_listed_and_agreement_silent(report, pets, addon):
    listed = {(g["subject"], g["field"]): g for g in gaps(report, "family_bonus")}
    expected = set()
    for key in set(pets["families"]) & set(addon["families"]):
        for field, value in pets["families"][key]["bonus"].items():
            theirs = addon["families"][key]["bonus"][field]
            if theirs is not None and value is not None and float(theirs) != float(value):
                expected.add((key, field))
    assert set(listed) == expected and expected
    key, field = min(expected)
    some = listed[(key, field)]
    assert some["values"] == {
        "client": pets["families"][key]["bonus"][field],
        "addon": addon["families"][key]["bonus"][field],
    }
    # une famille dont les trois bonus concordent n'apparaît pas
    agreeing = [
        k
        for k in set(pets["families"]) & set(addon["families"])
        if all(float(addon["families"][k]["bonus"][f]) == float(v) for f, v in pets["families"][k]["bonus"].items())
    ]
    assert agreeing and not {k for k, _ in listed} & set(agreeing)


def test_rank_level_gap_listed_with_both_levels(report, pets, addon):
    listed = {(g["subject"], g["field"]): g for g in gaps(report, "rank_level")}
    expected = {}
    for name, ability in addon["abilities"].items():
        client = pets["abilities"].get(family_key(name))
        if client is None:
            continue
        levels = {r["rank"]: r["level"] for r in client["ranks"]}
        for r in ability["ranks"]:
            if r["level"] is not None and r["rank"] in levels and levels[r["rank"]] != r["level"]:
                expected[(family_key(name), f"rang {r['rank']}")] = (levels[r["rank"]], r["level"])
    assert expected and set(listed) == set(expected)
    for key, (client_level, addon_level) in expected.items():
        assert listed[key]["values"] == {"client": client_level, "addon": addon_level}


def test_beast_level_differs_from_questie(report, addon, questie):
    listed = {g["subject"]: g for g in gaps(report, "beast_level_questie")}
    expected = {}
    for b in addon["beasts"]:
        npc = questie.npc(b["id"])
        if npc is not None and [npc.min_level, npc.max_level] != b["level"]:
            expected[str(b["id"])] = ([npc.min_level, npc.max_level], b["level"])
    assert expected and set(listed) == set(expected)
    concordant = [
        b
        for b in addon["beasts"]
        if questie.npc(b["id"]) and [questie.npc(b["id"]).min_level, questie.npc(b["id"]).max_level] == b["level"]
    ]
    assert concordant and not {str(b["id"]) for b in concordant} & set(listed)
    for subject, (theirs, ours) in expected.items():
        assert listed[subject]["values"] == {"questie": theirs, "addon": ours}


def test_counts_of_compared_items(report, pets, addon):
    counts = report["counts"]
    assert counts["families_compared"] == len(set(pets["families"]) & set(addon["families"]))
    assert counts["beasts"] == len(addon["beasts"])


def test_markdown_is_deterministic_and_names_each_gap(report, pets, addon, questie):
    text = render_crosscheck_markdown(report)
    assert text == render_crosscheck_markdown(crosscheck(pets, addon, questie))
    assert text.startswith("# ") and text.endswith("\n")
    for g in report["gaps"]:
        assert g["subject"] in text


def test_without_questie_only_client_and_addon_are_compared(pets, addon):
    alone = crosscheck(pets, addon, None)
    assert not [g for g in alone["gaps"] if g["kind"].endswith("_questie")]
    assert alone["sources"]["questie"] is None
