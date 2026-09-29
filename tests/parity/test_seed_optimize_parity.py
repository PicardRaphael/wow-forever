"""Parité de l'optimiseur de leveling porté avec seed/forever-mage/scripts/optimize.py (lecture seule, importé par
importlib), en mode seed : `rules="seed"`, PV d'ancrage du seed (`mob_source="seed"`), dégâts des rangs
(`spell_level="rank"`). Test reporté du seed `optimiseur_legal` (tests/run_all.py) : ordre légal à chaque niveau,
`leveling("Orc", 10, 14, beam=2, depth=2, mc_n=40)`.

Valeurs de référence relevées par `repr()` sur le seed (plan T05) et recalculées ici par le seed lui-même."""

import importlib.util
import sys

import pytest
from conftest import REPO_ROOT

from forever.engine.talents import check_build
from forever.optimize.leveling import level_weight, optimize_leveling, score_plan

SEED_SCRIPTS = REPO_ROOT / "seed" / "forever-mage" / "scripts"
SEED_MODE = {"mob_source": "seed", "spell_level": "rank"}
HOURS = 3.411975105216378
POINTS = {"improvedFrostbolt": 4, "elementalPrecision": 1}
STEPS = [
    (10, "improvedFrostbolt", 23.83, "frost"),
    (11, "improvedFrostbolt", 23.68, "frost"),
    (12, "improvedFrostbolt", 25.44, "frost"),
    (13, "elementalPrecision", 27.52, "frost"),
    (14, "improvedFrostbolt", 26.68, "frost"),
]


@pytest.fixture(scope="module")
def seed_optimize():
    sys.path.insert(0, str(SEED_SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("seed_optimize_parity", SEED_SCRIPTS / "optimize.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(SEED_SCRIPTS))


@pytest.fixture(scope="module")
def ported(seed_game_data):
    return optimize_leveling(seed_game_data, "Orc", 10, 14, beam=2, depth=2, mc_n=40, rules="seed", **SEED_MODE)


def test_optimiseur_legal(seed_game_data, ported):
    assert ported.hours_equiv == pytest.approx(HOURS, rel=1e-12)
    assert ported.points == POINTS
    assert [(s.level, s.talent, s.time_s, s.rotation) for s in ported.steps] == STEPS
    pts: dict[str, int] = {}
    for s in ported.steps:
        if s.talent:
            pts[s.talent] = pts.get(s.talent, 0) + 1
        assert check_build(seed_game_data, pts, s.level) == [], s


def test_leveling_matches_the_seed(ported, seed_optimize):
    r = seed_optimize.leveling("Orc", 10, 14, beam=2, depth=2, mc_n=40)
    assert ported.hours_equiv == pytest.approx(r["hours_equiv"], rel=1e-12)
    assert ported.points == r["points"]
    assert [(s.level, s.talent, s.time_s, s.rotation) for s in ported.steps] == [tuple(x) for x in r["steps"]]


def test_level_weight_matches_the_seed(seed_game_data, seed_optimize):
    for level in range(1, 61):
        assert level_weight(seed_game_data, level) == pytest.approx(seed_optimize.level_weight(level), rel=1e-12), level
    assert level_weight(seed_game_data, 60) == 0.0


def test_score_plan_matches_the_seed(seed_game_data, seed_optimize):
    plan = [(s[0], s[1]) for s in STEPS]
    r = seed_optimize.score_plan(plan, "Orc")
    ours = score_plan(seed_game_data, plan, "Orc", rules="seed", **SEED_MODE)
    assert ours.hours_equiv == pytest.approx(r["hours_equiv"], rel=1e-12)
    assert list(ours.steps) == [tuple(x) for x in r["steps"]]
    assert ours.points == r["points"]


def test_illegal_plan_is_refused(seed_game_data):
    with pytest.raises(ValueError, match="illégal au niveau 10"):
        score_plan(seed_game_data, [(10, "iceLance")], "Orc", rules="seed", **SEED_MODE)
