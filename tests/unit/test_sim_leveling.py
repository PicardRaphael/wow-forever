"""Simulateur de leveling (Monte Carlo) : reproductibilité à graine fixe (J2), options, erreurs ; mode seed (PV
d'ancrage du seed, dégâts des rangs) et mode par défaut (PV mesurés puis Questie corrigé, dégâts au niveau du
personnage). Valeur de référence du seed : L16, 5 Improved Frostbolt, n = 200, graine 1 -> 30.435373555182213."""

import pytest

from forever.sim.leveling_mc import mc

SEED_MODE = {"mob_source": "seed", "spell_level": "rank"}
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
    assert default["xp_h"] == pytest.approx(3600 * (45 + 5 * 12) / default["total"], rel=1e-12)  # leveling.mob_xp


def test_run_between_is_added_to_every_kill(game_data):
    base = mc(game_data, 12, {}, n=100, seed=3, **SEED_MODE)
    longer = mc(game_data, 12, {}, n=100, seed=3, run_between_s=10.0, **SEED_MODE)
    assert longer["combat"] == base["combat"] and longer["total"] == pytest.approx(base["total"] + 4.0, rel=1e-12)


def test_invalid_options_are_refused(game_data):
    with pytest.raises(ValueError, match="rotation"):
        mc(game_data, 12, {}, rotation="arcane", n=10)
    with pytest.raises(ValueError, match="n"):
        mc(game_data, 12, {}, n=0)
    with pytest.raises(ValueError, match="mob_source"):
        mc(game_data, 12, {}, n=10, mob_source="questie")
    with pytest.raises(ValueError, match="option"):
        mc(game_data, 12, {}, n=10, flee=True)
