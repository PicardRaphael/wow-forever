"""Talents : prérequis, légalité, points disponibles, répartition par arbre, valeur d'un rang (registre G3).

Sources : seed/forever-mage/tests/run_all.py (tests `prerequis` et `legalite`) ; valeurs et messages calculés avec
seed/forever-mage/scripts/fm.py le 2026-09-27 ; rangs de talents : seed/forever-mage/data/1.60.1.70009/talents.json."""

from forever.engine import check_build, legal_additions, points_available, talent_value, tree_split

LEGAL_AT_20 = {"improvedFrostbolt": 5, "elementalPrecision": 2, "frostbite": 3, "iceLance": 1}


def test_prerequisites(game_data):
    need = {
        "fingersOfFrost": "iceLance",
        "arcanePower": "presenceOfMind",
        "hotStreak": "pyroblast",
        "combustion": "criticalMass",
        "iceBarrier": "coldSnap",
    }
    for key, prereq_key in need.items():
        t = game_data.talents[key]
        assert t.prereq is not None, key
        assert game_data.talent_at[(t.tree, *t.prereq)] == prereq_key, key


def test_build_legality(game_data):
    assert check_build(game_data, {"improvedFrostbolt": 5, "iceLance": 1}, 20) == [
        "Ice Lance (palier 3) exige 10 points avant, 5 dépensés"
    ]
    assert check_build(game_data, LEGAL_AT_20, 20) == []
    assert check_build(game_data, LEGAL_AT_20, 19) == ["11 points pour 10 disponibles au niveau 19"]
    assert check_build(game_data, {"improvedFrostbolt": 6}, 20) == ["Improved Frostbolt : 6/5"]


def test_unknown_talent_is_reported(game_data):
    assert check_build(game_data, {"inconnu": 1}, 20) == ["talent inconnu : inconnu"]


def test_prerequisite_must_be_maxed(game_data):
    pts = {"improvedFrostbolt": 5, "elementalPrecision": 5, "frostbite": 3, "iceLance": 1, "fingersOfFrost": 1}
    errors = check_build(game_data, {**pts, "iceShards": 5, "piercingIce": 3}, 60)
    assert errors == []
    assert "Fingers of Frost exige Ice Lance au maximum" in check_build(
        game_data, {**pts, "iceLance": 0, "iceShards": 5, "piercingIce": 3}, 60
    )


def test_points_available(game_data):
    assert points_available(game_data, 20) == 11
    assert points_available(game_data, 10) == 1
    assert points_available(game_data, 9) == 0
    assert points_available(game_data, 1) == 0
    assert points_available(game_data, 9, talented_bonus=1) == 1


def test_legal_additions_tier_one(game_data):
    assert legal_additions(game_data, {}, 10) == [
        "wandSpecialization",
        "arcaneFocus",
        "improvedChanneling",
        "wakeOfFire",
        "incineration",
        "improvedFireball",
        "frostWarding",
        "improvedFrostbolt",
        "elementalPrecision",
    ]


def test_legal_additions_without_points(game_data):
    assert legal_additions(game_data, {"improvedFrostbolt": 1}, 10) == []


def test_tree_split(game_data):
    assert tree_split(game_data, {"improvedFrostbolt": 5, "arcaneFocus": 2}) == {"Arcane": 2, "Fire": 0, "Frost": 5}
    assert tree_split(game_data, {}) == {"Arcane": 0, "Fire": 0, "Frost": 0}


def test_talent_value(game_data):
    assert talent_value(game_data, {}, "improvedFrostbolt") == 0.0
    assert talent_value(game_data, {}, "improvedFrostbolt", default=-1.0) == -1.0
    assert talent_value(game_data, {"improvedFrostbolt": 3}, "improvedFrostbolt") == 0.3
    assert talent_value(game_data, {"improvedFrostbolt": 7}, "improvedFrostbolt") == 0.5  # dernier rang connu
    assert talent_value(game_data, {"improvedFrostbolt": 3}, "improvedFrostbolt", 1, default=9.0) == 9.0
    assert talent_value(game_data, {"iceLance": 1}, "iceLance", 2) == 300
