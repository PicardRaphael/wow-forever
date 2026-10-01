"""Guide d'apprivoisement et fiches des familiers (CH0, bloc D), en fonctions pures, sur fixtures.

Client : `pets.json` décodé des fixtures wago (familles, rangs, cartes) ; règles : `pet_rules.json` installé ;
addon : fixture synthétique `tests/fixtures/bestiary/` ; plages de niveau des zones : fixture Questie ; bande de
niveau : moteur (`level_band`). Valeurs attendues relues dans ces sources, jamais écrites ici."""

import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, read_json

from forever.engine.leveling import level_band
from forever.errors import InvalidArgumentError
from forever.pets import (
    ability_sheet,
    beast_sheet,
    family_sheet,
    normalize_text,
    resolve_name,
    resolve_zone,
    rules_sheet,
    tame_guide,
)
from forever.pipeline.bestiary import read_bestiary, read_bestiary_saved
from forever.pipeline.pets import decode_pets, load_pet_tables
from forever.pipeline.questie import npc_level_ranges, read_questie

RULES_DECODE = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
PET_RULES = read_json(DATA_DIR / LOCAL_VERSION / "pet_rules.json")
MARGIN = PET_RULES["rules"]["tame.level_margin"]["value"]
LEVEL = 10  # niveau d'essai : la fixture a une bête trop haute et une bête apprivoisable à ce niveau
SAVED = FIXTURES / "bestiary" / "ForeverBestiary.lua"


@pytest.fixture(scope="module")
def pets():
    return decode_pets(load_pet_tables(WAGO_70124, RULES_DECODE), RULES_DECODE, LOCAL_VERSION)


@pytest.fixture(scope="module")
def addon():
    return read_bestiary(FIXTURES / "bestiary" / "ForeverBestiary")


@pytest.fixture(scope="module")
def ranges():
    return npc_level_ranges(read_questie(FIXTURES / "questie" / "11.38.0"))


@pytest.fixture(scope="module")
def band(game_data):
    return level_band(game_data, LEVEL)


def guide(pets, addon, ranges, band, **kw):
    args = {"level": LEVEL, "zone": "Les Tarides", "band": band, "zone_levels": ranges, "ability": "Bite", "rank": 3}
    args.update(kw)
    return tame_guide(pets, PET_RULES, addon, **args)


def teaches(beast, ability, rank):
    return any(t["ability"] == ability and t["rank"] == rank for t in beast["taught"])


def map_of(pets, english):
    return next((k, m) for k, m in pets["maps"].items() if m["name"]["en"] == english)


# --- Résolution des noms ---------------------------------------------------------------------------


def test_text_normalisation_ignores_case_and_accents():
    assert normalize_text("Les Tarides") == normalize_text("les  TARIDES") == normalize_text("lés tarides")


def test_french_zone_resolves_through_the_client_map(pets):
    key, entry = map_of(pets, "The Barrens")
    zone = resolve_zone(pets, entry["name"]["fr"])
    assert zone["map_id"] == key and zone["name"]["en"] == "The Barrens" and zone["continent"] == entry["continent"]
    assert resolve_zone(pets, "the barrens")["map_id"] == key


def test_unknown_zone_lists_candidates(pets):
    with pytest.raises(InvalidArgumentError) as exc:
        resolve_zone(pets, "Les Taride")
    assert exc.value.suggestions and any("Tarides" in s for s in exc.value.suggestions)


def test_names_resolve_in_french_english_key_and_alias(pets, addon):
    wolf = pets["families"]["wolf"]
    assert resolve_name(pets, addon, wolf["name"]["fr"]) == {"kind": "family", "key": "wolf"}
    assert resolve_name(pets, addon, "Wolf") == {"kind": "family", "key": "wolf"}
    assert resolve_name(pets, addon, "crocilisk") == {"kind": "family", "key": "crocolisk"}
    bite = pets["abilities"]["bite"]
    assert resolve_name(pets, addon, bite["name"]["fr"]) == {"kind": "ability", "key": "bite"}
    beast = addon["beasts"][0]
    assert resolve_name(pets, addon, beast["name"]["en"]) == {"kind": "beast", "key": beast["id"]}


def test_ambiguous_name_lists_its_candidates(pets, addon):
    # un nom porté exactement par deux entités (une famille et une bête ajoutée à la copie de l'addon)
    shared = dict(addon)
    shared["beasts"] = [*addon["beasts"], {**addon["beasts"][0], "id": 999999, "name": {"en": "Wolf", "es": None}}]
    with pytest.raises(InvalidArgumentError) as exc:
        resolve_name(pets, shared, "Wolf")
    assert len(exc.value.suggestions) >= 2


# --- Guide ---------------------------------------------------------------------------------------------


def test_guide_lists_beasts_of_the_zone_teaching_the_rank(pets, addon, ranges, band):
    out = guide(pets, addon, ranges, band)
    first = out["zones"][0]
    assert first["requested"] is True and first["name"]["en"] == "The Barrens"
    expected = {b["id"] for b in addon["beasts"] if "The Barrens" in b["zones"] and teaches(b, "Bite", 3)}
    assert {b["id"] for b in first["beasts"]} == expected and expected


def test_tameable_now_or_level_where_it_becomes_tameable(pets, addon, ranges, band):
    out = guide(pets, addon, ranges, band)
    beasts = {b["id"]: b for z in out["zones"] for b in z["beasts"]}
    for raw in addon["beasts"]:
        if raw["id"] not in beasts:
            continue
        b = beasts[raw["id"]]
        now = raw["level"][0] <= LEVEL + MARGIN
        assert b["tameable_now"] is now, raw["id"]
        assert b["tameable_at"] == (None if now else raw["level"][0] - MARGIN), raw["id"]
    assert any(not b["tameable_now"] for b in beasts.values())  # la fixture a une bête trop haute
    assert out["certainty"]["tameable_now"] == PET_RULES["rules"]["tame.level_margin"]["certainty"]


def test_neighbour_zones_same_continent_overlapping_the_band(pets, addon, ranges, band):
    out = guide(pets, addon, ranges, band)
    _, barrens = map_of(pets, "The Barrens")
    names = [z["name"]["en"] for z in out["zones"][1:]]
    expected = set()
    for b in addon["beasts"]:
        for zone in b["zones"]:
            if zone == "The Barrens" or not teaches(b, "Bite", 3):
                continue
            entry = next((m for m in pets["maps"].values() if m["name"]["en"] == zone), None)
            lo_hi = ranges.get(zone)
            if (
                entry
                and entry["continent"] == barrens["continent"]
                and lo_hi
                and lo_hi[0] <= band[1]
                and lo_hi[1] >= band[0]
            ):
                expected.add(zone)
    assert set(names) == expected and expected
    for z in out["zones"][1:]:
        assert z["levels"] == ranges[z["name"]["en"]] and z["requested"] is False


def test_zone_of_another_continent_is_excluded(pets, addon, ranges, band):
    out = guide(pets, addon, ranges, band)
    _, barrens = map_of(pets, "The Barrens")
    far = [
        b
        for b in addon["beasts"]
        if teaches(b, "Bite", 3)
        and any(
            m["name"]["en"] == z and m["continent"] != barrens["continent"]
            for z in b["zones"]
            for m in pets["maps"].values()
        )
    ]
    assert far  # la fixture porte une bête sur un autre continent
    listed = {b["id"] for z in out["zones"] for b in z["beasts"]}
    assert not {b["id"] for b in far} & listed


def test_highest_rank_reachable_at_the_level(pets, addon, ranges, band):
    out = guide(pets, addon, ranges, band)
    levels = {r["rank"]: r["level"] for r in pets["abilities"]["bite"]["ranks"]}
    assert out["highest_rank"] == max(r for r, lv in levels.items() if lv <= LEVEL)
    assert out["target"]["rank_level"] == levels[3]
    assert out["target"]["reachable"] is (levels[3] <= LEVEL)


def test_coordinates_carry_their_source_and_date(pets, addon, ranges, band):
    saved = read_bestiary_saved(SAVED)
    out = guide(pets, addon, ranges, band, saved=saved)
    barrens_key, _ = map_of(pets, "The Barrens")
    beast = next(b for b in out["zones"][0]["beasts"] if b["id"] in {int(k) for k in addon["community"]["beasts"]})
    sources = {c["source"] for c in beast["coords"]}
    assert "addon" in sources and "community" in sources and "mine" in sources
    community = next(c for c in beast["coords"] if c["source"] == "community")
    assert community["date"] == addon["info"]["community_date"] and community["map_id"] == barrens_key
    assert beast["reporters"] == addon["community"]["beasts"][str(beast["id"])]["reporters"]
    assert all(c.get("date") for c in beast["coords"])


def test_family_target_includes_community_finds(pets, addon, ranges, band):
    out = guide(pets, addon, ranges, band, ability=None, rank=None, family="wolf")
    ids = {b["id"] for z in out["zones"] for b in z["beasts"]}
    found = [int(k) for k, o in addon["community"]["beasts"].items() if o.get("family") == "wolf"]
    assert found and set(found) <= ids


def test_missing_level_is_refused(pets, addon, ranges, band):
    with pytest.raises(InvalidArgumentError):
        guide(pets, addon, ranges, band, level=None)


def test_no_third_party_string_in_the_guide(pets, addon, ranges, band):
    saved = read_bestiary_saved(SAVED)
    text = json.dumps(guide(pets, addon, ranges, band, saved=saved), ensure_ascii=False)
    raw = (FIXTURES / "bestiary" / "ForeverBestiary.lua").read_text(encoding="utf-8")
    for leak in ("JoueurTiersInvente", "PairInvente", "GUIDINVENTE", "rpbbbb01", "rpaaaa01", "rplike001", "rpvote001"):
        assert leak in raw or leak in (FIXTURES / "bestiary" / "ForeverBestiary" / "Data" / "Community.lua").read_text(
            encoding="utf-8"
        )
        assert leak not in text


# --- Fiches --------------------------------------------------------------------------------------------


def test_rules_sheet_lists_every_rule_with_its_source():
    sheet = rules_sheet(PET_RULES)
    assert [r["key"] for r in sheet["rules"]] == list(PET_RULES["rules"])
    for r in sheet["rules"]:
        assert r["source"] and r["certainty"] and r["registry"]
    assert sheet["reported_bugs"] == PET_RULES["reported_bugs"]


def test_family_sheet_with_ranks_and_family_costs(pets):
    sheet = family_sheet(pets, "wolf")
    wolf = pets["families"]["wolf"]
    assert sheet["name"] == wolf["name"] and sheet["bonus"] == wolf["bonus"] and sheet["diet"] == wolf["diet"]
    dash = next(a for a in sheet["abilities"] if a["key"] == "dash")
    assert [r["training_cost"] for r in dash["ranks"]] == wolf["training_costs"]["dash"]
    assert [r["level"] for r in dash["ranks"]] == [r["level"] for r in pets["abilities"]["dash"]["ranks"]]
    assert sheet["certainty"]["training_cost"] == "probable"


def test_ability_sheet_counts_teaching_beasts_per_rank(pets, addon):
    sheet = ability_sheet(pets, "bite", addon)
    counts = {r["rank"]: r["beasts"] for r in sheet["ranks"]}
    for rank, count in counts.items():
        assert count == sum(1 for b in addon["beasts"] if teaches(b, "Bite", rank))
    detailed = ability_sheet(pets, "bite", addon, rank=3, detail=True)
    assert [r["rank"] for r in detailed["ranks"]] == [3]
    assert {b["id"] for b in detailed["ranks"][0]["teachers"]} == {
        b["id"] for b in addon["beasts"] if teaches(b, "Bite", 3)
    }


def test_beast_sheet_with_marks_and_community(pets, addon, ranges):
    raw = next(b for b in addon["beasts"] if str(b["id"]) in addon["community"]["beasts"])
    sheet = beast_sheet(addon, raw["id"], pets, questie_levels=[1, 2])
    assert sheet["family"]["key"] == raw["family"] and sheet["level"]["addon"] == raw["level"]
    assert sheet["level"]["questie"] == [1, 2]
    assert sheet["taught"] == raw["taught"] and sheet["confirmation"] == raw["confirmation"]
    assert sheet["community"]["reporters"] == addon["community"]["beasts"][str(raw["id"])]["reporters"]
