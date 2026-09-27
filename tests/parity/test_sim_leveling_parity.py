"""Parité du simulateur de leveling porté avec seed/forever-mage/scripts/sim_leveling.py (lecture seule, importé par
importlib), en mode seed : PV d'ancrage du seed (`mob_source="seed"`) et dégâts des rangs (`spell_level="rank"`).

Écart de niveau négatif exclu : le seed lit la ligne « - » (4 %) de la table de toucher, le moteur applique la règle
Classic des cibles plus basses (A3, décision 4 du plan T04b).

Même graine, même ordre des tirages : chaque champ est égal à celui du seed à 1e-12 (le critère de la feuille de
route, ±1 % au niveau 12 avec 3 Improved Frostbolt, est donc couvert). Valeurs de référence relevées par `repr()`
sur le seed (plan T04b)."""

import importlib.util
import math
import sys

import pytest
from conftest import LOCAL_VERSION, REPO_ROOT

from forever.sim.leveling_mc import kill_mc, mc

SEED_SCRIPTS = REPO_ROOT / "seed" / "forever-mage" / "scripts"
SEED_MODE = {"mob_source": "seed", "spell_level": "rank"}
FIELDS = ("combat", "mana", "taken", "downtime", "total", "xp_h")
# (niveau, rotation, talents, total Monte Carlo du seed à n = 600, graine 12345)
CASES = [
    (12, "frost", {"improvedFrostbolt": 3}, 25.51026932538584),
    (16, "frost", {"improvedFrostbolt": 5, "elementalPrecision": 2}, 29.895997677896577),
    (
        24,
        "frost",
        {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceLance": 1, "frostChanneling": 3},
        32.33266309936493,
    ),
    (16, "fire", {"improvedFireball": 5, "elementalPrecision": 2}, 30.93969370799394),
]
# Talents qui exercent toutes les branches du Monte Carlo (build non vérifié, comme le seed le permet).
FROST_ALL = {
    "improvedFrostbolt": 5,
    "frostbite": 3,
    "iceLance": 1,
    "fingersOfFrost": 2,
    "wintersChill": 5,
    "permafrost": 3,
    "arcticReach": 2,
    "improvedFrostNova": 2,
    "arcaneConcentration": 5,
    "masterOfElements": 3,
    "arcaneMeditation": 3,
}
FIRE_ALL = {"improvedFireball": 5, "ignite": 5, "burningSoul": 3, "wakeOfFire": 2, "masterOfElements": 3}


@pytest.fixture(scope="module")
def seed_sim():
    sys.path.insert(0, str(SEED_SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("seed_sim_leveling_parity", SEED_SCRIPTS / "sim_leveling.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SEED_SCRIPTS))
    module.fm.data(LOCAL_VERSION)
    return module


def same(ours, theirs, case):
    for field in FIELDS:
        assert math.isclose(ours[field], theirs[field], rel_tol=1e-12, abs_tol=1e-12), (case, field)


@pytest.mark.parametrize(("level", "rotation", "pts", "total"), CASES)
def test_mc_matches_the_seed(game_data, seed_sim, level, rotation, pts, total):
    ours = mc(game_data, level, pts, "Orc", rotation, 600, **SEED_MODE)
    same(ours, seed_sim.mc(level, pts, "Orc", rotation, 600), (level, rotation))
    assert ours["total"] == pytest.approx(total, rel=1e-12)


def test_mc_default_n_matches_the_seed(game_data, seed_sim):
    """n = 1500 (défaut de `mc`), niveau 12, 3 Improved Frostbolt : critère de la feuille de route."""
    ours = mc(game_data, 12, {"improvedFrostbolt": 3}, **SEED_MODE)
    same(ours, seed_sim.mc(12, {"improvedFrostbolt": 3}), "L12 n=1500")
    assert ours["total"] == pytest.approx(25.48655329665798, rel=1e-12)
    assert ours["xp_h"] == pytest.approx(14897.22498356594, rel=1e-12)


@pytest.mark.parametrize(
    ("level", "rotation", "pts", "options"),
    [
        (40, "frost", FROST_ALL, {"nova": True}),
        (40, "frost", FROST_ALL, {"nova": True, "nova_break": 0.5, "level_diff": 2, "run_between_s": 4.0}),
        (30, "fire", FIRE_ALL, {}),
        (8, "frost", {}, {}),
    ],
)
def test_every_branch_matches_the_seed(game_data, seed_sim, level, rotation, pts, options):
    seed_options = {("run_between" if k == "run_between_s" else k): v for k, v in options.items()}
    ours = mc(game_data, level, pts, "Orc", rotation, 200, seed=7, **SEED_MODE, **options)
    same(ours, seed_sim.mc(level, pts, "Orc", rotation, 200, seed=7, **seed_options), (level, rotation, options))


def test_character_overrides_reach_the_simulation(game_data, seed_sim):
    over = {"intellect": 180, "sp": 120, "hp": 900, "armor": 400}
    seed_over = {("int" if k == "intellect" else k): v for k, v in over.items()}
    ours = mc(game_data, 20, {"improvedFrostbolt": 5}, "Troll", "frost", 150, over=over, **SEED_MODE)
    same(ours, seed_sim.mc(20, {"improvedFrostbolt": 5}, "Troll", "frost", 150, over=seed_over), "fiche")


def test_single_kill_with_an_injected_generator(game_data, seed_sim):
    import random

    from forever.engine import character

    ours = kill_mc(
        game_data, 16, {"improvedFrostbolt": 5}, character(game_data, 16), "frost", random.Random(3), **SEED_MODE
    )
    theirs = seed_sim.kill_mc(16, {"improvedFrostbolt": 5}, seed_sim.fm.character(16, "Orc"), "frost", random.Random(3))
    same(ours, theirs, "un combat")
