"""Parité du conseil de respec avec seed/forever-mage/scripts/respec.py (lecture seule, importé par importlib), en mode
seed : `rules="seed"`, PV d'ancrage du seed, dégâts des rangs. Test reporté du seed `pvp_et_respec` (partie respec :
verdict « réinitialiser » ou « garder »). Valeurs de référence relevées par `repr()` sur le seed (plan T05)."""

import importlib.util
import sys

import pytest
from conftest import REPO_ROOT

from forever.engine.respec import gold_per_hour, respec_cost
from forever.optimize.respec import advise_leveling

SEED_SCRIPTS = REPO_ROOT / "seed" / "forever-mage" / "scripts"
SEED_MODE = {"mob_source": "seed", "spell_level": "rank"}


@pytest.fixture(scope="module")
def seed_respec():
    sys.path.insert(0, str(SEED_SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("seed_respec_parity", SEED_SCRIPTS / "respec.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(SEED_SCRIPTS))


def test_pvp_et_respec_respec_part(seed_game_data):
    r = advise_leveling(
        seed_game_data, 20, {"improvedFireball": 5}, {"improvedFrostbolt": 5}, 5, rules="seed", **SEED_MODE
    )
    assert (r["xp_h_actuel"], r["xp_h_cible"], r["heures_gagnees"], r["cout_po"], r["bilan_po_equiv"]) == (
        17643,
        16537,
        -0.31,
        1,
        -2.7,
    )
    assert r["verdict"] == "garder"
    assert [respec_cost(seed_game_data, i) for i in range(12)] == [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 50]


@pytest.mark.parametrize(
    ("level", "current", "target", "hours", "n", "gph"),
    [
        (20, {"improvedFireball": 5}, {"improvedFrostbolt": 5}, 5, 0, None),
        (20, {"improvedFrostbolt": 5}, {"improvedFireball": 5}, 10, 3, None),
        (30, {"wandSpecialization": 2}, {"improvedFrostbolt": 5, "elementalPrecision": 3}, 8, 1, 12.0),
        (45, {}, {"improvedFireball": 5, "ignite": 5, "incineration": 3}, 20, 12, None),
    ],
)
def test_advice_matches_the_seed(seed_game_data, seed_respec, level, current, target, hours, n, gph):
    ours = advise_leveling(seed_game_data, level, current, target, hours, "Orc", n, gph, rules="seed", **SEED_MODE)
    theirs = seed_respec.advise_leveling(level, current, target, hours, "Orc", n, gph=gph)
    keys = ("xp_h_actuel", "xp_h_cible", "heures_gagnees", "cout_po", "bilan_po_equiv", "verdict")
    assert {k: ours[k] for k in keys} == {k: theirs[k] for k in keys}


def test_cost_and_gold_per_hour_match_the_seed(seed_game_data, seed_respec):
    for i in range(15):
        assert respec_cost(seed_game_data, i) == seed_respec.cost(i)
    for level in range(1, 61):
        assert gold_per_hour(seed_game_data, level) == seed_respec.gold_per_hour(level)
