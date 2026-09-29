"""Parité du profil PvP et de l'optimiseur PvP glouton avec seed/forever-mage/scripts/pvp.py et optimize.py (lecture
seule, importés par importlib), en mode seed (`rules="seed"`). Test reporté du seed `pvp_et_respec` (partie PvP :
score > 0, statut EST). Valeurs de référence relevées par `repr()` sur le seed (plan T05) et recalculées ici par le
seed lui-même."""

import importlib.util
import sys

import pytest
from conftest import REPO_ROOT

from forever.engine.pvp import pvp_score, seed_rounded
from forever.optimize.endgame import seed_pvp_greedy

SEED_SCRIPTS = REPO_ROOT / "seed" / "forever-mage" / "scripts"
BUILD_20 = {"improvedFrostbolt": 5, "frostbite": 3, "elementalPrecision": 2, "iceLance": 1}
BUILD_60 = {"improvedFrostbolt": 5, "frostbite": 3, "elementalPrecision": 3, "iceShards": 5}


def _load(name):
    spec = importlib.util.spec_from_file_location(f"seed_{name}_pvp_parity", SEED_SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def seed():
    sys.path.insert(0, str(SEED_SCRIPTS))
    try:
        yield _load("pvp"), _load("optimize")
    finally:
        sys.path.remove(str(SEED_SCRIPTS))


def test_pvp_et_respec_pvp_part(game_data):
    p20 = seed_rounded(pvp_score(game_data, BUILD_20, 20, "Orc", rules="seed"))
    assert p20 == {
        "score": 45.1,
        "burst_seq": "Givre : Éclair, Nova, Javelot(s) sur gel",
        "burst": 208.4,
        "control": 41.0,
        "survival": 8.3,
        "sustain": 26.0,
        "statut": "EST",
    }
    p60 = seed_rounded(pvp_score(game_data, BUILD_60, 60, "Orc", rules="seed"))
    assert (p60["score"], p60["burst"], p60["control"], p60["survival"], p60["sustain"]) == (
        82.0,
        1878.4,
        65.0,
        8.3,
        263.5,
    )


@pytest.mark.parametrize(
    ("pts", "level", "race"),
    [
        (BUILD_20, 20, "Orc"),
        (BUILD_60, 60, "Orc"),
        ({"improvedFireball": 5, "ignite": 5, "pyroblast": 1, "presenceOfMind": 1, "arcaneFocus": 5}, 40, "Human"),
        ({"arcaneFocus": 5, "arcaneConcentration": 5, "arcaneBlast": 1, "arcanePower": 1}, 60, "Undead"),
        ({"iceBlock": 1, "coldSnap": 1, "iceBarrier": 1, "improvedFrostNova": 2, "permafrost": 3}, 50, "Gnome"),
        ({"combustion": 1, "blastWave": 1, "impact": 3, "improvedCounterspell": 2, "frostWarding": 2}, 45, "Troll"),
    ],
)
def test_profile_matches_the_seed(game_data, seed, pts, level, race):
    pv, _ = seed
    assert seed_rounded(pvp_score(game_data, pts, level, race, rules="seed")) == pv.score(pts, level, race)


def test_seed_pvp_greedy_parity(game_data, seed):
    _, op = seed
    ours = seed_pvp_greedy(game_data, 20, "Orc", beam=2)
    theirs = op.pvp(None, 20, "Orc", beam=2)
    assert ours.points == theirs["points"]
    assert ours.points == {
        "frostWarding": 2,
        "arcaneFocus": 4,
        "elementalPrecision": 1,
        "wandSpecialization": 2,
        "arcaneResilience": 2,
    }
    assert seed_rounded(pvp_score(game_data, ours.points, 20, "Orc", rules="seed"))["score"] == 38.6
