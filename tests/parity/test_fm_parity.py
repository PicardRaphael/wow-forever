"""Parité du moteur porté avec seed/forever-mage/scripts/fm.py (lecture seule, importé par importlib).

Le seed lit ses propres données (seed/forever-mage/data/1.60.1.70009/), copiées octet pour octet dans forever/data/.
Tolérance relative 1e-12 sur chaque champ ; les chaînes d'erreur de légalité sont identiques."""

import importlib.util
import itertools
import math
import random

import pytest
from conftest import LOCAL_VERSION, REPO_ROOT

from forever.engine import best_rank, character, check_build, coefficient, expected_cast, legal_additions

SEED_FM = REPO_ROOT / "seed" / "forever-mage" / "scripts" / "fm.py"
RACES = ["Orc", "Undead", "Troll", "Human", "Gnome"]
LEVELS = [10, 20, 40, 60]
BUFFS = [{}, {"crit": 0.05, "dmg": 0.1, "haste": 0.1, "cost": -0.1, "sp_pct": 0.1, "sp_flat": 50.0}]
# Surcharges de fiche : clé du moteur -> clé du seed
OVERRIDE_KEYS = {"intellect": "int"}
CHARACTER_FIELDS = {
    "intellect": "int",
    "spirit": "spirit",
    "sp": "sp",
    "base_mana": "base_mana",
    "mana": "mana",
    "crit": "crit",
    "hit_gear": "hit_gear",
    "haste": "haste",
    "hp": "hp",
    "armor": "armor",
    "spirit_regen": "spirit_regen",
}
CAST_FIELDS = {
    "hit": "hit",
    "crit": "crit",
    "crit_mult": "crit_mult",
    "dmg_mult": "dmg_mult",
    "dmg": "dmg",
    "direct_per_hit": "direct_per_hit",
    "dot": "dot",
    "ignite": "ignite",
    "mana": "mana",
    "cast_s": "cast",
    "range_yd": "range",
    "cooldown_s": "cooldown",
}
OVERRIDE_SETS = [
    None,
    {"sword": True, "crit_gear": 0.03, "hit_gear": 0.01, "haste": 0.05},
    {"intellect": 200, "spirit": 150, "sp": 300, "base_mana": 1000, "mana": 5000, "spell_crit": 0.12},
    {"hp": 2000, "armor": 500, "sp": 450},
]


@pytest.fixture(scope="module")
def fm():
    spec = importlib.util.spec_from_file_location("seed_forever_mage_fm", SEED_FM)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.data(LOCAL_VERSION)
    return module


def seed_overrides(overrides):
    return {OVERRIDE_KEYS.get(k, k): v for k, v in (overrides or {}).items()}


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def talent_sets(fm):
    by_tree = {}
    for key, t in fm.data().T.items():
        by_tree.setdefault(t["tree"], {})[key] = t["max"]
    spells = {s["talent"]: 1 for s in fm.data().spells.values() if "talent" in s}
    everything = {k: t["max"] for k, t in fm.data().T.items()}
    return [{}, by_tree["Frost"], by_tree["Fire"], by_tree["Arcane"], spells, everything]


def test_character_parity(game_data, fm):
    for level, race, overrides in itertools.product(range(1, 61), RACES, OVERRIDE_SETS):
        ours = character(game_data, level, race, overrides)
        theirs = fm.character(level, race, seed_overrides(overrides))
        for field, seed_field in CHARACTER_FIELDS.items():
            assert close(getattr(ours, field), theirs[seed_field]), (level, race, overrides, field)


def test_expected_cast_parity(game_data, fm):
    spells = sorted(fm.data().spells)
    assert len(spells) >= 15
    count = 0
    for pts, level in itertools.product(talent_sets(fm), LEVELS):
        chars = [
            (o, character(game_data, level, "Human", o), fm.character(level, "Human", seed_overrides(o)))
            for o in (None, OVERRIDE_SETS[1])
        ]
        for key, diff, frozen, wc, buffs, (_, ours_ch, seed_ch) in itertools.product(
            spells, (0, 3), (False, True), (0, 5), BUFFS, chars
        ):
            ours = expected_cast(game_data, key, level, pts, ours_ch, diff, frozen=frozen, wc_stacks=wc, buffs=buffs)
            theirs = fm.expected_cast(key, level, pts, seed_ch, diff, frozen, wc, buffs)
            case = (key, level, sorted(pts), diff, frozen, wc, bool(buffs))
            if theirs is None:
                assert ours is None, case
                continue
            assert ours is not None, case
            count += 1
            assert list(ours["rank"][1:]) == theirs["rank"], case
            assert ours["key"] == theirs["key"] and ours["school"] == theirs["school"], case
            for field, seed_field in CAST_FIELDS.items():
                assert close(ours[field], theirs[seed_field]), (case, field, ours[field], theirs[seed_field])
    assert count > 5000


def test_rank_and_coefficient_parity(game_data, fm):
    for key, spell in fm.data().spells.items():
        for i, seed_rank in enumerate(spell["ranks"]):
            ours_rank = game_data.spells[key].ranks[i]
            assert ours_rank.position == i + 1
            assert list(ours_rank[1:]) == seed_rank
            assert close(coefficient(game_data, key, ours_rank), fm.coefficient(key, seed_rank)), (key, i)
        for level, pts in itertools.product(range(1, 61), ({}, {spell.get("talent", "x"): 1})):
            ours = best_rank(game_data, key, level, pts)
            theirs = fm.best_rank(key, level, pts)
            assert (None if ours is None else list(ours[1:])) == theirs, (key, level, pts)


def test_build_parity(game_data, fm):
    rng = random.Random(70009)
    keys = list(fm.data().T)
    builds = [{}, {"improvedFrostbolt": 5, "iceLance": 1}, {"improvedFrostbolt": 6}, {"inconnu": 2}]
    while len(builds) < 20:
        build = {}
        for _ in range(rng.randint(1, 12)):
            key = rng.choice(keys)
            build[key] = rng.randint(0, fm.data().T[key]["max"] + 1)
        builds.append(build)
    for build, level in itertools.product(builds, (10, 19, 20, 30, 45, 60)):
        assert check_build(game_data, build, level) == fm.check_build(build, level), (build, level)
        if "inconnu" not in build:
            assert legal_additions(game_data, build, level) == fm.legal_additions(build, level), (build, level)
