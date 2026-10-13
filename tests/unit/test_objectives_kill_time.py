"""Temps par monstre des objectifs (T04d, demande de l'utilisateur du 2026-10-13) : même règle pour le Mage que pour
le Chasseur : temps mesuré sur les relevés d'abord, moteur (Mage) ou estimation seulement à défaut ; le temps du
moteur reste rendu à côté d'une mesure. Mesures écrites dans le cache isolé du test (forme de `kill_time.json`)."""

import json

from conftest import FIXTURES, isolated_deps

from forever.kill_time import MEASURES_FILE
from forever.sim.objectives import objectives

WOW = FIXTURES / "addons" / "quests"


def write_measures(deps, cls, level, seconds, samples=50):
    band = {
        "class": cls,
        "level_min": level,
        "level_max": level,
        "method": "cadence",
        "samples": samples,
        "median_s": seconds,
        "low_s": seconds,
        "high_s": seconds,
    }
    path = deps.cache_dir / "measures" / MEASURES_FILE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"bands": [band], "unattributed": 0}), encoding="utf-8")


def test_mage_measure_wins_over_the_engine_which_stays_for_comparison(tmp_path):
    deps = isolated_deps(tmp_path)
    write_measures(deps, "mage", 16, 19.0)
    kt = objectives(deps, class_name="mage", level=16, faction="horde", wow_dir=WOW)["kill_time"]
    assert kt["source"] == "measured" and kt["seconds"] == 19.0 and kt["scope"] == "total"
    assert kt["engine"]["source"] == "engine" and kt["engine"]["scope"] == "total"


def test_journal_combat_time_is_marked_as_combat_only():
    from forever.kill_time import KillParams, kill_time

    params = KillParams(1, 5, 120.0, 10.0, 15.0, "test")
    band = {"class": "hunter", "level_min": 11, "level_max": 15, "method": "journaux", "samples": 3}
    band |= {"median_s": 11.0, "low_s": 10.0, "high_s": 12.0}
    assert kill_time(params, class_name="hunter", level=15, measures={"bands": [band]}).scope == "combat"
    assert kill_time(params, class_name="hunter", level=40, measures=None).scope == "combat"
