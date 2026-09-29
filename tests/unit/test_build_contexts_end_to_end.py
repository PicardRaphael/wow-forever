"""Rapport de build de bout en bout pour les contextes que test_build_report.py n'exécute pas (raid, PvP en monde
ouvert), et cohérence de la valeur analytique d'un contexte en rotation arcane (T05, suites de la relecture)."""

import pytest
from conftest import isolated_deps

from forever.build import build_report
from forever.engine.talents import check_build, points_available
from forever.optimize.endgame import context_analytic
from forever.provenance import validate_provenance
from forever.sim.encounter import encounter_analytic

ARC40 = {
    "arcaneFocus": 5,
    "improvedChanneling": 1,
    "arcaneConcentration": 5,
    "arcaneSubtlety": 2,
    "arcaneImpact": 3,
    "arcaneBlast": 1,
    "arcaneGeometry": 1,
    "arcaneMeditation": 3,
    "missileBarrage": 1,
    "presenceOfMind": 1,
    "arcaneMind": 4,
    "arcaneInstability": 3,
    "arcanePower": 1,
}


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("build_e2e"))


@pytest.mark.parametrize("context", ["raid", "pvp-world"])
def test_report_end_to_end(game_data, deps, context):
    rep = build_report(deps, context, 20, preset="rapide", sensitivity=False)
    validate_provenance(rep["provenance"])
    assert check_build(game_data, rep["talents"], 20) == []
    assert sum(rep["talents"].values()) == points_available(game_data, 20)
    assert rep["verifiable_in_game"] is True and rep["reasons"]
    mana = [a for a in rep["assumptions"] if "T05b" in a]  # mana des combats longs : affichée tant que T05b manque
    assert bool(mana) == (context == "raid")


def test_context_value_uses_the_effective_duration_in_the_arcane_rotation(game_data):
    """Sans fin de mana, la marche arcane rapporte ses dégâts à la fin du dernier lancer : la valeur du contexte doit
    rendre les mêmes dégâts par seconde que le scénario (réserve de test sans limite)."""
    over = {"mana": 1e6}  # réserve de test sans limite
    value, choices = context_analytic(game_data, "raid", 40, ARC40, over=over)
    c = choices["raid_boss"]
    r = encounter_analytic(game_data, "raid_boss", 40, ARC40, "Orc", c.rotation, over, **c.options())
    assert value == pytest.approx(r["dps"], rel=1e-12)
