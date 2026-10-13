"""Objectifs de leveling sur le livre des donjons (DJ1, bloc E, registre I14, I16, I17) : un donjon par instance,
passage du modèle de `forever/engine/dungeon.py` (relevé, sinon formule), premier passage et passages suivants,
niveau de placement, phrase de conseil, bouton Leveling.

Fixtures : `tests/fixtures/addons/dungeons/` (addons synthétiques, passages relevés par Naowh Forever) ; données :
version du dépôt (`dungeons.json`, `mechanics.json`). Aucun chiffre de jeu ici."""

import re
import statistics

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.bridge.plans import OBJECTIVES_READ
from forever.engine.dungeon import run_defaults
from forever.sim.objectives import objectives

WOW = FIXTURES / "addons" / "dungeons"
VALUES = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
SECONDS_PER_MINUTE = 60.0  # conversion d'unité


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    deps = isolated_deps(tmp_path_factory.mktemp("objectives_dj1"))
    return objectives(deps, class_name="hunter", level=15, faction="horde", wow_dir=WOW)


def by_id(report, key):
    return next(d for d in report["dungeons"] if d["id"] == key)


def test_objectives_group_by_instance(report):
    ids = [d["id"] for d in report["dungeons"]]
    assert len(ids) == len(set(ids))
    assert ids.count("3065") == 1  # « Hall of Thanes » et « The Hall of Thanes » : une instance
    assert by_id(report, "389")["first_pass"]["quests"] >= 2


def test_measured_runs_drive_the_dungeon_time(report):
    rfc = by_id(report, "389")
    run = rfc["run"]
    assert run["source"] == "measured" and run["samples"] == 2 and run["certainty"] == "certain"
    assert run["minutes"] == pytest.approx(statistics.median([2360, 2400]) / SECONDS_PER_MINUTE)
    assert rfc["repeat"]["minutes"] == pytest.approx(run["minutes"])


def test_formula_when_no_run(report):
    thanes = by_id(report, "3065")
    assert thanes["run"]["source"] == "formula" and thanes["run"]["certainty"] == "suppose"
    p = run_defaults(VALUES)
    assert p["min_minutes"] <= thanes["run"]["minutes"] <= p["max_minutes"]


def test_first_pass_beats_repeat(report):
    rfc = by_id(report, "389")
    assert rfc["first_pass"]["xp"] > rfc["repeat"]["xp"] > 0
    assert rfc["first_pass"]["seconds"] > rfc["repeat"]["seconds"]


def test_dungeon_without_quests_has_repeat_only(report):
    ruins = by_id(report, "2999")
    assert ruins["first_pass"] is None and ruins["repeat"]["xp"] > 0


def test_closed_dungeons_are_left_out(report):
    names = {d["name"] for d in report["dungeons"]}
    assert "Alcaz Prison" not in names


def test_placement_level_is_reported(report):
    rfc = by_id(report, "389")
    placement = rfc["placement"]
    levels = rfc["levels"]
    assert levels["min"] <= placement["level"] <= levels["max"] and placement["share_h"] > 0
    assert all(levels["min"] <= lv <= levels["max"] for lv in placement["window"])


def test_dungeon_advice_repeats_the_numbers(report):
    advice = report["dungeon_advice"]
    assert isinstance(advice, str) and advice
    numbers = {int(n) for n in re.findall(r"\d+", advice.replace(" ", "").replace(" ", ""))}
    target = report["dungeon_target"]
    if target is not None:
        assert target["name"] in advice and target["placement"]["level"] in numbers


def test_leveling_button_names_placement():
    assert "dungeon_advice" in OBJECTIVES_READ and "placement" in OBJECTIVES_READ
