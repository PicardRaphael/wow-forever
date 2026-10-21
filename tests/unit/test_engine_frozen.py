"""Moteur du Mage gelé (décision 293, plan des simulateurs) : chaque réponse calculée par notre moteur le dit dans sa
provenance (gelé à la révision 7 de 1.60.1.70450, plus aucune mécanique ajoutée, au niveau 60 wowsims/forever répond
par `forever_simulate`), sans changer aucune valeur."""

import pytest

from forever.sims.report import MAGE_ENGINE_FROZEN


def frozen(provenance):
    return MAGE_ENGINE_FROZEN in provenance["assumptions"]


def test_leveling_simulation_says_the_engine_is_frozen(make_deps):
    from forever.leveling import simulate_leveling

    out = simulate_leveling(make_deps(), 20, n=5)
    assert frozen(out["provenance"])


def test_mage_weights_say_the_engine_is_frozen(make_deps):
    from forever.gear import mage_weights

    assert frozen(mage_weights(make_deps(), level=20)["provenance"])


@pytest.mark.slow
def test_build_says_the_engine_is_frozen(make_deps):
    from forever.build import build_report

    assert frozen(build_report(make_deps(), "leveling", 20, preset="rapide", sensitivity=False)["provenance"])
