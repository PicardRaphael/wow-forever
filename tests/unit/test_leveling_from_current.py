"""Chemin de leveling depuis le niveau et le build actuels (MAG19, décision 220, demande de l'utilisateur du 2026-10-09).

Le chemin minimise le temps cumulé à partir du niveau actuel du personnage et de son build : les niveaux déjà joués ne
comptent plus. Sans build actuel (personnage neuf ou prévu), il part du niveau 10. Le conseil de respec compare le
build actuel prolongé au build d'une respec (chemin libre depuis le niveau 10). Aucune valeur de jeu n'est affirmée."""

import pytest
from conftest import isolated_deps

from forever.bridge.context import Resolved, TalentReading
from forever.bridge.plans import button_plan
from forever.build import build_report
from forever.engine.talents import check_build

CURRENT = {"improvedFrostbolt": 3, "elementalPrecision": 1}  # 4 points : build légal au niveau 13


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("from-current"))


@pytest.fixture(scope="module")
def with_current(deps):
    return build_report(deps, "leveling", 16, preset="rapide", current=CURRENT, sensitivity=False)


def test_the_path_starts_from_the_current_level_and_build(with_current, game_data):
    rep = with_current
    assert all(rep["talents"].get(k, 0) >= v for k, v in CURRENT.items())
    steps = [s for s in rep["order"] if s["talent"]]
    assert steps and min(s["level"] for s in steps) == 14
    acc = dict(CURRENT)
    for s in steps:
        acc[s["talent"]] = acc.get(s["talent"], 0) + 1
        assert check_build(game_data, acc, s["level"]) == [], s
    assert acc == rep["talents"]
    assert rep["talents"] == rep["respec"]["projected"]["talents"]
    assert "niveau 14" in rep["departage"]["criterion"] and "cumulé" in rep["departage"]["criterion"]


def test_without_a_current_build_the_path_starts_at_level_ten(deps, game_data):
    rep = build_report(deps, "leveling", 12, preset="rapide", sensitivity=False)
    first = game_data.constants.talents.first_level
    assert min(s["level"] for s in rep["order"] if s["talent"]) == first
    assert f"niveau {first}" in rep["departage"]["criterion"]


def test_respec_compares_the_current_build_to_a_free_path(with_current):
    respec = with_current["respec"]
    versus = respec["versus_optimal"]
    assert versus["current"] == respec["projected"]["talents"]
    assert versus["optimal"] == respec["free"]["talents"]
    assert versus["optimal_rotation"] in ("frost", "fire", "arcane")
    assert versus["tie"] is (not versus["significant"] and versus["optimal"] != versus["current"])
    if versus["tie"] or versus["current_better"]:
        assert respec["verdict"] == "garder"


@pytest.mark.parametrize("key", ["talents", "leveling"])
def test_buttons_ask_the_path_from_the_current_build(key):
    mage = Resolved(
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
    plan = button_plan(key, mage, 30)
    build_call = next(c for c in plan.calls if c.tool == "forever_build")
    assert build_call.args["current"] == {"frostbite": 3} and build_call.args["level"] == 20
    text = " ".join(plan.read)
    assert "respec.versus_optimal.optimal_rotation" in text and "chemin" in text
