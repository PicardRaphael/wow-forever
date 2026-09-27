"""Simulateur de leveling (Monte Carlo) : reproductibilité à graine fixe (J2), options, erreurs ; mode seed (PV
d'ancrage du seed, dégâts des rangs) et mode par défaut (PV mesurés puis Questie corrigé, dégâts au niveau du
personnage). Valeur de référence du seed : L16, 5 Improved Frostbolt, n = 200, graine 1 -> 30.435373555182213."""

import pytest

from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import mc

SEED_MODE = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}
IF5 = {"improvedFrostbolt": 5}


def test_monte_carlo_reproducible_seed_mode(game_data):
    """Test du seed (monte_carlo_reproductible) porté à l'identique, valeur du seed en plus."""
    a = mc(game_data, 16, IF5, n=200, seed=1, **SEED_MODE)["total"]
    b = mc(game_data, 16, IF5, n=200, seed=1, **SEED_MODE)["total"]
    assert a == b == pytest.approx(30.435373555182213, rel=1e-12)


def test_monte_carlo_reproducible_default_mode(game_data):
    a = mc(game_data, 16, IF5, n=200, seed=1)
    b = mc(game_data, 16, IF5, n=200, seed=1)
    assert a == b
    assert mc(game_data, 16, IF5, n=200, seed=2) != a  # la graine compte


def test_default_mode_uses_measured_hp_and_character_level(game_data):
    """Au niveau 12, PV mesurés 272 contre 247 pour le seed : le combat est plus long en mode par défaut."""
    default = mc(game_data, 12, {"improvedFrostbolt": 3}, n=300)
    seed = mc(game_data, 12, {"improvedFrostbolt": 3}, n=300, **SEED_MODE)
    assert default["combat"] > seed["combat"]
    one = mc(game_data, 12, {"improvedFrostbolt": 3}, n=1)
    assert one["xp_h"] == pytest.approx(3600 * (45 + 5 * 12) / one["total"], rel=1e-12)  # leveling.mob_xp


def test_run_between_is_added_to_every_kill(game_data):
    base = mc(game_data, 12, {}, n=100, seed=3, **SEED_MODE)
    longer = mc(game_data, 12, {}, n=100, seed=3, run_between_s=10.0, **SEED_MODE)
    assert longer["combat"] == base["combat"] and longer["total"] == pytest.approx(base["total"] + 4.0, rel=1e-12)


def test_invalid_options_are_refused(game_data):
    with pytest.raises(ValueError, match="rotation"):
        mc(game_data, 12, {}, rotation="shadow", n=10)
    with pytest.raises(ValueError, match="n"):
        mc(game_data, 12, {}, n=0)
    with pytest.raises(ValueError, match="mob_source"):
        mc(game_data, 12, {}, n=10, mob_source="questie")
    with pytest.raises(ValueError, match="option"):
        mc(game_data, 12, {}, n=10, flee=True)


# Cas des tests du seed (analytique_proche_du_monte_carlo)
SEED_CASES = [
    (12, "frost", {"improvedFrostbolt": 3}),
    (16, "frost", {"improvedFrostbolt": 5, "elementalPrecision": 2}),
    (
        24,
        "frost",
        {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceLance": 1, "frostChanneling": 3},
    ),
    (16, "fire", {"improvedFireball": 5, "elementalPrecision": 2}),
]
# Cas du test du seed calibrage_cible_blizzard (combat de 8 à 20 s, cible Blizzard de 10 à 15 s)
CALIBRATION = [
    (12, {"improvedFrostbolt": 3}),
    (20, {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 2, "iceLance": 1}),
]
MODES = {"seed": SEED_MODE, "par défaut": {}}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("level", "rotation", "pts"), SEED_CASES)
def test_analytic_close_to_monte_carlo(game_data, mode, level, rotation, pts):
    """Test du seed porté à l'identique : analytique à moins de 15 % du Monte Carlo (n = 600), dans les deux modes."""
    m = mc(game_data, level, pts, "Orc", rotation, 600, **MODES[mode])["total"]
    a = kill_analytic(game_data, level, pts, "Orc", rotation, **MODES[mode])["total"]
    assert abs(a / m - 1) < 0.15, (mode, level, rotation, round(m, 1), round(a, 1))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("level", "pts"), CALIBRATION)
def test_calibration_blizzard_target(game_data, mode, level, pts):
    """Test du seed porté à l'identique : combat entre 8 et 20 s (Monte Carlo, n = 600), dans les deux modes."""
    c = mc(game_data, level, pts, "Orc", "frost", 600, **MODES[mode])["combat"]
    assert 8 <= c <= 20, (mode, level, c)


def test_calibration_values_of_the_seed(game_data):
    got = [mc(game_data, level, pts, "Orc", "frost", 600, **SEED_MODE)["combat"] for level, pts in CALIBRATION]
    assert got == pytest.approx([11.716904761904743, 14.127405952380936], rel=1e-12)


def test_analytic_refuses_invalid_options(game_data):
    with pytest.raises(ValueError, match="rotation"):
        kill_analytic(game_data, 12, {}, rotation="shadow")
    with pytest.raises(ValueError, match="option"):
        kill_analytic(game_data, 12, {}, flee=True)
