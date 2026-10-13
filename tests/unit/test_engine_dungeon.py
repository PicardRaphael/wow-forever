"""Passage d'un donjon et niveau de placement (DJ1, bloc E, registre I16 et I17) : fonctions pures de
`forever/engine/dungeon.py`. Paramètres lus dans `mechanics.json` de la version du dépôt (`dungeon.run_defaults`,
formule de Factoruide) ; durées et XP synthétiques (entrées du test), aucune règle de jeu écrite ici."""

import re
import statistics

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.dungeon import first_pass, formula_run, placement_level, repeat_pass, run_defaults, run_model

VALUES = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
SECONDS_PER_MINUTE = 60.0  # conversion d'unité


@pytest.fixture
def params():
    return run_defaults(VALUES)


def expected_formula(p, mob_level):
    minutes = min(max(p["base_minutes"] + p["minutes_per_mob_level"] * mob_level, p["min_minutes"]), p["max_minutes"])
    return minutes, p["base_kills"] + p["kills_per_mob_level"] * mob_level


def test_defaults_come_from_mechanics(params):
    entry = VALUES["dungeon.run_defaults"]
    assert entry["certainty"] == "suppose" and "Factoruide" in entry["source"] and entry["registry"] == "I16"
    assert params == {k: float(v) for k, v in entry["value"].items()}


def test_factoruide_formula_bounds(params):
    low = int((params["min_minutes"] - params["base_minutes"]) / params["minutes_per_mob_level"]) - 1
    high = int((params["max_minutes"] - params["base_minutes"]) / params["minutes_per_mob_level"]) + 1
    middle = (low + high) // 2
    for mob_level in (low, middle, high):
        assert formula_run(params, mob_level) == pytest.approx(expected_formula(params, mob_level))
    assert formula_run(params, low)[0] == params["min_minutes"]
    assert formula_run(params, high)[0] == params["max_minutes"]
    assert params["min_minutes"] < formula_run(params, middle)[0] < params["max_minutes"]


def test_formula_is_the_last_resort(params):
    run = run_model(params, 20)
    assert run.source == "formula" and run.certainty == "suppose" and run.samples == 0
    assert (run.minutes, run.kills) == pytest.approx(expected_formula(params, 20))


def test_addon_kill_count_used_when_no_run(params):
    run = run_model(params, 20, addon_kills=77)
    assert run.source == "addon" and run.certainty == "suppose" and run.kills == 77
    assert run.minutes == pytest.approx(expected_formula(params, 20)[0])


def test_measured_run_wins(params):
    measured = [1800.0, 2400.0]
    run = run_model(params, 20, measured=measured, addon_kills=77)
    assert run.source == "measured" and run.certainty == "certain" and run.samples == 2
    assert run.minutes == pytest.approx(statistics.median(measured) / SECONDS_PER_MINUTE)
    assert run.kills == 77  # pas de compte relevé : celui de l'addon


def test_measured_kills_win_over_the_addon(params):
    run = run_model(params, 20, measured=[1800.0], measured_kills=[50], addon_kills=77)
    assert run.kills == 50


def test_first_pass_beats_repeat(params):
    run = run_model(params, 20)
    first = first_pass(run=run, kill_xp=100.0, quests_xp=5000.0, quests=4, travel_s=600.0, quest_overhead_s=90.0)
    repeat = repeat_pass(run=run, kill_xp=100.0)
    assert first.xp == pytest.approx(run.kills * 100.0 + 5000.0)
    assert first.seconds == pytest.approx(run.minutes * SECONDS_PER_MINUTE + 2 * 600.0 + 4 * 90.0)
    assert repeat.xp == pytest.approx(run.kills * 100.0)
    assert repeat.seconds == pytest.approx(run.minutes * SECONDS_PER_MINUTE)
    assert first.xp_h > repeat.xp_h


def test_placement_maximises_level_share():
    """XP par heure croissante puis grise (None) ; XP du niveau croissante : le niveau retenu maximise la part."""
    xp_h = {10: 4000.0, 11: 5000.0, 12: 6000.0, 13: None}
    level_xp = {10: 8000.0, 11: 9000.0, 12: 13000.0, 13: 14000.0}
    zone = {10: 4500.0, 11: 4500.0, 12: 4500.0, 13: 4500.0}
    placement = placement_level(range(10, 14), xp_h.get, level_xp.__getitem__, zone.get)
    shares = {lv: xp_h[lv] / level_xp[lv] for lv in (10, 11, 12)}
    assert placement.level == max(shares, key=shares.__getitem__)
    assert placement.share_h == pytest.approx(shares[placement.level])
    assert placement.window == [11, 12]  # niveaux où le premier passage bat la meilleure zone


def test_placement_tie_takes_lowest():
    placement = placement_level(range(5, 8), lambda lv: 1000.0, lambda lv: 2000.0, lambda lv: None)
    assert placement.level == 5 and placement.window == [5, 6, 7]


def test_placement_without_any_level_is_none():
    assert placement_level(range(5, 8), lambda lv: None, lambda lv: 2000.0, lambda lv: None) is None


def test_no_game_number_in_the_engine():
    source = (DATA_DIR.parent / "engine" / "dungeon.py").read_text(encoding="utf-8")
    for key, number in read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["dungeon.run_defaults"][
        "value"
    ].items():
        assert not re.search(rf"\b{number}\b", source), key
