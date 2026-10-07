"""Codec du code de build de Talents Forever, génération 6 (FA1, bloc A) : va-et-vient exact sur les 45 codes des
builds populaires (fixture `tests/fixtures/talents_forever/popular.json`), segment d'ordre (comptes partiels, symboles
`0` et `5` du Mage), segments vides et zéros finaux, lien, refus en français.

Dispositions (rangs maximaux par position de liste) rebâties par `tests/talents_forever_data.py` depuis
`classes.json` et `layout.json` ; aucun chiffre de jeu écrit ici hors des codes relevés de la fixture."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from talents_forever_data import load_fixture, max_ranks, position

from forever.tf_code import CODE_VERSION, SYMBOLS, TfPlan, code_of, decode, encode, link

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
POPULAR = load_fixture("popular.json")
MAGE = max_ranks(CLASSES, "MAGE")


def popular_codes():
    return [(file, b["code"], b["pts"]) for file, block in POPULAR["classes"].items() for b in block["top"]]


def frost_plan(level, ranks_by_key, steps=None):
    """Plan du Mage avec les seuls rangs donnés (clés de classes.json) et un ordre en clés."""
    ranks = [[0] * len(tree) for tree in MAGE]
    for key, rank in ranks_by_key.items():
        ti, i = position("MAGE", key)
        ranks[ti][i] = rank
    order = tuple(position("MAGE", k) for k in steps) if steps is not None else None
    return TfPlan("mage", level, tuple(tuple(t) for t in ranks), order)


def test_alphabet_and_generation():
    assert CODE_VERSION == "6"
    assert len(SYMBOLS) == 58 and len(set(SYMBOLS)) == 58
    assert not set("1234") & set(SYMBOLS)


def test_forty_five_popular_codes_round_trip_exactly():
    codes = popular_codes()
    assert len(codes) == 45
    for file, code, pts in codes:
        plan = decode(code, max_ranks(CLASSES, file))
        assert encode(plan) == code, code
        assert [sum(tree) for tree in plan.ranks] == pts, code
        assert plan.order is None and plan.legacy is None
        assert plan.class_slug == file.lower() and plan.level == 60


def test_mage_examples_points_by_tree():
    plan = decode("mage/60/-0055103013013304-00550003310003002-6", MAGE)
    assert [sum(t) for t in plan.ranks] == [0, 29, 22]
    plan = decode("mage/60/--0555323331321331251-6", MAGE)
    assert [sum(t) for t in plan.ranks] == [0, 0, 51]
    assert plan.ranks[0] == (0,) * len(MAGE[0])  # segment vide : arbre sans point, toutes positions à zéro
    assert len(plan.ranks[2]) == len(MAGE[2])


def test_trailing_zeros_are_removed_and_empty_tree_is_empty():
    plan = frost_plan(20, {"improvedFrostbolt": 5, "elementalPrecision": 3})
    assert encode(plan) == "mage/20/--053-6"


def test_order_with_partial_runs():
    steps = ["improvedFrostbolt"] * 2 + ["elementalPrecision"] + ["improvedFrostbolt"] * 3 + ["elementalPrecision"] * 2
    plan = frost_plan(20, {"improvedFrostbolt": 5, "elementalPrecision": 3}, steps)
    code = encode(plan)
    assert code == "mage/20/--053-k2l1kl-6"
    back = decode(code, MAGE)
    assert back.ranks == plan.ranks and back.order == plan.order


def test_symbols_zero_and_five_of_the_mage():
    assert position("MAGE", "wintersChill") == (2, 17) and SYMBOLS[52] == "0"
    assert position("MAGE", "iceBarrier") == (2, 18) and SYMBOLS[53] == "5"
    one_run = frost_plan(60, {"wintersChill": 5, "iceBarrier": 1}, ["wintersChill"] * 5 + ["iceBarrier"])
    code = encode(one_run)
    assert code.endswith("-05-6")
    back = decode(code, MAGE)
    assert back.order == one_run.order
    split = frost_plan(
        60, {"wintersChill": 5, "iceBarrier": 1}, ["wintersChill"] * 2 + ["iceBarrier"] + ["wintersChill"] * 3
    )
    code = encode(split)
    assert code.endswith("-0250-6")  # 2 : compte ; 5 : symbole ; dernier 0 : sans compte
    assert decode(code, MAGE).order == split.order


def test_code_without_order_has_none():
    assert decode("mage/20/0500050001---6", MAGE).order is None


def test_legacy_segments_are_kept_raw():
    plan = decode("mage/60/--0555323331321331251-a-b-c-6", MAGE)
    assert plan.legacy == ("a", "b", "c") and plan.order is None
    assert encode(plan) == "mage/60/--0555323331321331251-a-b-c-6"


def test_link():
    code = "mage/20/--053-k2l1kl-6"
    assert link(code) == "https://talentsforever.com/" + code
    assert "?a" not in link(code)
    assert code_of(link(code)) == code
    assert code_of(link(code) + "?a") == code
    assert code_of(link(code) + "#partage") == code
    assert code_of("  " + code + "\n") == code
    assert decode(link(code) + "?a", MAGE).order is not None


@pytest.mark.parametrize(
    ("code", "words"),
    [
        ("mage/60/--0555323331321331251-5", "génération"),
        ("mage/60/0-0-6", "forme"),
        ("mage/60/a1-0-0-6", "forme"),
        ("mage60--0555-6", "forme"),
        ("mage/xx/--0555-6", "forme"),
        ("mage/60/9--0555-6", "rang"),
        ("mage/60/--0555-ZZ-6", "ordre"),
        ("mage/60/" + "1" * 30 + "--6", "position"),
    ],
)
def test_refusals_in_french(code, words):
    with pytest.raises(ValueError, match=words):
        decode(code, MAGE)


def test_class_mismatch_is_refused():
    with pytest.raises(ValueError, match="classe"):
        decode("warrior/60/--05-6", MAGE, class_slug="mage")


def test_more_than_fifty_eight_positions_are_refused():
    big = ((1,) * 30, (1,) * 29, ())
    with pytest.raises(ValueError, match="58"):
        decode("x/60/1--6", big)
    with pytest.raises(ValueError, match="58"):
        encode(TfPlan("x", 60, ((1,) + (0,) * 29, (0,) * 29, ()), ((0, 0),)))


def test_incoherent_order_is_refused():
    with pytest.raises(ValueError, match="ordre"):
        encode(frost_plan(20, {"improvedFrostbolt": 2}, ["improvedFrostbolt"] * 3))
