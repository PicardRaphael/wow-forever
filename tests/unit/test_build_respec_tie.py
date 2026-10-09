"""Conseil de respec du leveling face au build optimal (demande de l'utilisateur du 2026-10-09).

Installé avec 1.60.1.70291, le build de leveling 20 passe du Givre au Feu, à égalité statistique et de façon instable :
un Mage Givre ne doit pas être poussé à réinitialiser pour un gain non mesurable. Le rapport compare le build actuel
projeté (build actuel plus le chemin conseillé) au build optimal par Monte Carlo apparié (`respec.versus_optimal`) ;
un écart non significatif garde le build actuel. Les boutons Talents et Leveling du pont lisent cette égalité et la
stabilité du build optimal. Aucune valeur de jeu n'est affirmée ici : seuls des statuts et des liens entre champs."""

import pytest
from conftest import isolated_deps

import forever.build as build_module
from forever.bridge.context import Resolved, TalentReading
from forever.bridge.plans import button_plan
from forever.build import build_report
from forever.optimize.decide import Gap


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("respec-tie"))


@pytest.fixture(scope="module")
def report(deps):
    return build_report(deps, "leveling", 16, preset="rapide", current={"wandSpecialization": 2}, sensitivity=False)


def only_the_path_build(monkeypatch):
    """Départage final réduit au build du chemin : ces tests ne portent que sur le conseil de respec (décision 217) ;
    le départage a ses tests (`test_departage.py`)."""
    monkeypatch.setattr(build_module, "_departage_candidates", lambda m, build, *args, **kwargs: [build])


def test_versus_optimal_is_a_paired_gap_with_its_decision(report):
    versus = report["respec"]["versus_optimal"]
    assert {"mean", "low", "high", "confidence", "significant", "decided_by", "tie"} <= set(versus)
    assert versus["tie"] is (not versus["significant"])
    assert versus["low"] <= versus["mean"] <= versus["high"]
    assert versus["optimal"] == report["talents"]
    assert versus["current"] == report["respec"]["projected"]["talents"]


def test_a_gain_that_is_not_measurable_keeps_the_current_build(deps, monkeypatch):
    real = build_module.advise_respec

    def reset_advised(*args, **kwargs):
        return real(*args, **kwargs)._replace(verdict="réinitialiser")

    def tie(self, a, b, seed):
        return Gap(0.0, -1.0, 1.0, self.gd.build.confidence, False), "analytique", True

    monkeypatch.setattr(build_module, "advise_respec", reset_advised)
    only_the_path_build(monkeypatch)
    monkeypatch.setattr(build_module._Metric, "compare", tie)
    rep = build_report(deps, "leveling", 12, preset="rapide", current={"improvedFrostbolt": 2}, sensitivity=False)
    assert rep["respec"]["versus_optimal"]["tie"] is True
    assert rep["respec"]["verdict"] == "garder"
    assert "égalité" in rep["respec"]["reason"]


def test_a_measurable_gain_keeps_the_advice(deps, monkeypatch):
    real = build_module.advise_respec

    def reset_advised(*args, **kwargs):
        return real(*args, **kwargs)._replace(verdict="réinitialiser")

    def clear(self, a, b, seed):
        return Gap(-2.0, -3.0, -1.0, self.gd.build.confidence, True), "monte_carlo", True

    monkeypatch.setattr(build_module, "advise_respec", reset_advised)
    only_the_path_build(monkeypatch)
    monkeypatch.setattr(build_module._Metric, "compare", clear)
    rep = build_report(deps, "leveling", 12, preset="rapide", current={"improvedFrostbolt": 2}, sensitivity=False)
    assert rep["respec"]["versus_optimal"]["tie"] is False
    assert rep["respec"]["verdict"] == "réinitialiser"


MAGE19 = Resolved(
    class_token="MAGE",
    class_name="Mage",
    level=19,
    race=None,
    faction=None,
    zone=None,
    reading=TalentReading(),
    current={"frostbite": 3},
    target_class=None,
    target_level=None,
    target_races=(),
    gear=[],
    defects=[],
)


@pytest.mark.parametrize("key", ["talents", "leveling"])
def test_buttons_read_the_tie_and_the_stability(key):
    plan = button_plan(key, MAGE19, 30)
    assert plan is not None
    text = " ".join(plan.read)
    assert "respec.versus_optimal.tie" in text and "stability.stable" in text
    assert "garde" in text


def test_a_current_build_measurably_better_than_the_optimizer_choice_is_kept(deps, monkeypatch):
    """Relevé sur 1.60.1.70291 (leveling 20, préréglage rapide) : le build retenu par l'analytique est plus lent que
    le build actuel projeté au Monte Carlo ; le rapport le dit et garde le build actuel."""
    real = build_module.advise_respec

    def reset_advised(*args, **kwargs):
        return real(*args, **kwargs)._replace(verdict="réinitialiser")

    def current_better(self, a, b, seed):
        return Gap(2.0, 1.0, 3.0, self.gd.build.confidence, True), "monte_carlo", False

    monkeypatch.setattr(build_module, "advise_respec", reset_advised)
    only_the_path_build(monkeypatch)
    monkeypatch.setattr(build_module._Metric, "compare", current_better)
    rep = build_report(deps, "leveling", 12, preset="rapide", current={"improvedFrostbolt": 2}, sensitivity=False)
    versus = rep["respec"]["versus_optimal"]
    assert versus["tie"] is False and versus["optimal_better"] is False and versus["current_better"] is True
    assert rep["respec"]["verdict"] == "garder"
    assert "meilleur" in rep["respec"]["reason"]


def test_buttons_name_the_case_of_a_better_current_build():
    plan = button_plan("talents", MAGE19, 30)
    assert "respec.versus_optimal.current_better" in " ".join(plan.read)
