"""Consultation des sorts (critère 1). Valeurs attendues : seed/forever-mage/data/1.60.1.70009/spells.json."""

import pytest
from conftest import LOCAL_VERSION, MANIFEST_CORRUPTIONS, corrupt_manifest, tamper

from forever.errors import DataIntegrityError, ForeverError
from forever.lookup import lookup_spell
from forever.provenance import validate_provenance


def test_frostbolt_rank_2(make_deps):
    r = lookup_spell(make_deps(), "frostbolt", 2)
    assert r["kind"] == "spell"
    assert r["id"] == "frostbolt"
    assert r["school"] == "frost"
    assert r["range_yd"] == 30
    assert r["ranks_total"] == 11
    assert r["total"] == 1 and r["next_offset"] is None
    (rank,) = r["ranks"]
    assert rank == {
        "rank": 2,
        "level": 8,
        "damage_min": 34,
        "damage_max": 38,
        "dot_total": 0,
        "dot_duration_s": 0,
        "cast_time_s": 1.8,
        "mana": 35,
        "mana_pct_base": None,
        "cooldown_s": 0,
    }
    assert r["details"] is None
    p = r["provenance"]
    assert validate_provenance(p) == []
    assert p["game_version"] == LOCAL_VERSION
    assert p["certainty"] == "certain"


def test_all_ranks_without_rank(make_deps):
    r = lookup_spell(make_deps(), "frostbolt")
    assert r["total"] == 11
    assert [x["rank"] for x in r["ranks"]] == list(range(1, 12))
    assert r["ranks"][0]["level"] == 4
    assert r["next_offset"] is None


def test_pagination(make_deps):
    r = lookup_spell(make_deps(), "frostbolt", limit=4, offset=4)
    assert [x["rank"] for x in r["ranks"]] == [5, 6, 7, 8]
    assert r["total"] == 11
    assert r["next_offset"] == 8
    last = lookup_spell(make_deps(), "frostbolt", limit=4, offset=8)
    assert [x["rank"] for x in last["ranks"]] == [9, 10, 11]
    assert last["next_offset"] is None


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Frostbolt", "frostbolt"),
        ("FROSTBOLT", "frostbolt"),
        ("fire blast", "fire_blast"),
        ("Fire-Blast", "fire_blast"),
    ],
)
def test_name_normalization(make_deps, name, expected):
    assert lookup_spell(make_deps(), name, 1)["id"] == expected


def test_unknown_rank(make_deps):
    with pytest.raises(ForeverError) as e:
        lookup_spell(make_deps(), "frostbolt", 12)
    assert e.value.code == "unknown_rank"
    assert "1-11" in e.value.message
    assert e.value.exit_code == 4


def test_rank_zero_is_unknown(make_deps):
    with pytest.raises(ForeverError) as e:
        lookup_spell(make_deps(), "frostbolt", 0)
    assert e.value.code == "unknown_rank"


def test_unknown_spell_suggests(make_deps):
    with pytest.raises(ForeverError) as e:
        lookup_spell(make_deps(), "frostbollt")
    assert e.value.code == "unknown_spell"
    assert "frostbolt" in e.value.suggestions
    assert e.value.exit_code == 4
    assert e.value.action


def test_talent_rank_mana_from_the_client(make_deps):
    """T06b, révision 2 : coût du rang 1 de Pyroblast lu dans le client (SpellPower.ManaCost), plus de null."""
    r = lookup_spell(make_deps(), "pyroblast", 1)
    assert r["ranks"][0]["mana"] == 125
    assert r["provenance"]["certainty"] == "certain"


def test_mana_pct_base(make_deps):
    r = lookup_spell(make_deps(), "arcane_blast", 1)
    assert r["ranks"][0]["mana_pct_base"] == 0.15


def test_detail_exposes_projectile_speed_and_lowers_certainty(make_deps):
    r = lookup_spell(make_deps(), "frostbolt", 2, detail=True)
    assert r["details"] is not None
    assert r["details"]["projectile_speed"] == 28
    assert r["details"]["slow"] == 0.4
    assert "ranks" not in r["details"]
    assert r["provenance"]["certainty"] == "suppose"
    assert any("projectile" in a for a in r["provenance"]["assumptions"])


def test_utility_spell_is_unsupported(make_deps):
    with pytest.raises(ForeverError) as e:
        lookup_spell(make_deps(), "blink")
    assert e.value.code == "unsupported_kind"
    assert "frostbolt" in e.value.suggestions


def test_invalid_pagination(make_deps):
    with pytest.raises(ForeverError) as e:
        lookup_spell(make_deps(), "frostbolt", limit=0)
    assert e.value.code == "invalid_argument"
    assert e.value.exit_code == 2


def test_tampered_data_refuses_to_answer(make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    with pytest.raises(DataIntegrityError) as e:
        lookup_spell(make_deps(data_dir=data_copy), "frostbolt", 2)
    assert e.value.code == "data_integrity"
    assert e.value.exit_code == 3
    assert "manifest --update" in e.value.action


def test_missing_manifest_refuses_to_answer(make_deps, data_copy):
    (data_copy / "manifest.json").unlink(missing_ok=True)
    with pytest.raises(ForeverError) as e:
        lookup_spell(make_deps(data_dir=data_copy), "frostbolt", 2)
    assert e.value.code == "manifest_missing"
    assert e.value.exit_code == 3


@pytest.mark.parametrize("kind", MANIFEST_CORRUPTIONS)
def test_corrupt_manifest_refuses_to_answer(make_deps, data_copy, kind):
    corrupt_manifest(data_copy, kind)
    with pytest.raises(DataIntegrityError) as e:
        lookup_spell(make_deps(data_dir=data_copy), "frostbolt", 2)
    assert e.value.code == "data_integrity"
    assert e.value.exit_code == 3
    assert "manifest --update" in e.value.action


def test_stale_cache_adds_assumption(make_deps, tmp_path):
    from datetime import timedelta

    from conftest import NOW, PREFIX, PRODUCT, FakeHttp

    from forever.freshness import check_freshness

    cache = tmp_path / "shared-cache"
    check_freshness(
        make_deps(http=FakeHttp.fixture("builds_stale.json"), now=NOW - timedelta(hours=1), cache_dir=cache),
        LOCAL_VERSION,
        product=PRODUCT,
        prefix=PREFIX,
        allow_network=True,
    )
    r = lookup_spell(make_deps(cache_dir=cache), "frostbolt", 2)
    assert r["provenance"]["freshness"] == "stale"
    assert r["provenance"]["certainty"] == "certain"  # T01 : stale ne dégrade pas la certitude
    assert any("1.60.1.70250" in a for a in r["provenance"]["assumptions"])
