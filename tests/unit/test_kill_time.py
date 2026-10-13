"""Temps par monstre des classes sans moteur (T04d, bloc E) : durée des combats du journal (familier compris),
cadence de ForeverLogger, repli estimé des données.

Fixtures : `tests/fixtures/combatlog/synthetic/hunter_pet.txt` (deux combats du joueur, 12 s avec le familier et
10 s seul ; un monstre tué par un autre joueur ; un combat sans mort) et `tests/fixtures/addon/ForeverLoggerDB_killtime.lua`
(Chasseur de niveau 15, cinq gains d'XP de monstre en deux séances séparées d'une heure). Paramètres :
`mechanics.json` de la version du dépôt (`measures.kill_time`, `leveling.kill_time_estimate`)."""

import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.kill_time import (
    MEASURES_FILE,
    fight_durations,
    kill_cadence,
    kill_params,
    kill_time,
    load_kill_times,
    measure_kill_times,
    refresh_kill_times,
)
from forever.pipeline.addon_sv import read_logger_db
from forever.pipeline.combatlog import read_log

LOG = FIXTURES / "combatlog" / "synthetic" / "hunter_pet.txt"
SV = FIXTURES / "addon" / "ForeverLoggerDB_killtime.lua"
MINE = "Player-0000-00000000"


def params():
    return kill_params(read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"])


def test_fight_durations_include_the_pet():
    _, events = read_log(LOG)
    fights = fight_durations(list(events), MINE)
    assert [(f.seconds, f.pet) for f in fights] == [(12.0, True), (10.0, False)]


def test_kill_cadence_skips_long_pauses_and_other_gains():
    gains = read_logger_db(SV).characters[MINE].xp
    p = params()
    assert p.pause_s < 3600  # la pause d'une heure de la fixture est écartée
    assert kill_cadence(gains, pause_s=p.pause_s) == [28.0, 22.0, 18.0]


def test_measures_by_class_and_level_band():
    p = params()
    measures = measure_kill_times(p, logs=[LOG], loggers=[read_logger_db(SV)])
    bands = {(b["class"], b["method"]): b for b in measures["bands"]}
    log_band = bands[("hunter", "journaux")]
    assert log_band["samples"] == 2 and log_band["median_s"] == pytest.approx(11.0)
    assert log_band["level_min"] <= 15 <= log_band["level_max"]
    cadence = bands[("hunter", "cadence")]
    assert cadence["samples"] == 3 and cadence["median_s"] == pytest.approx(22.0)


def test_without_measures_the_estimate_is_a_range():
    p = params()
    est = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["leveling.kill_time_estimate"]
    result = kill_time(p, class_name="hunter", level=15, measures=None)
    assert result.source == "estimated" and result.certainty == "suppose"
    assert (result.low, result.high) == (est["value"]["low_s"], est["value"]["high_s"])
    assert result.low <= result.seconds <= result.high


def test_measured_when_enough_samples():
    p = params()
    durations = [11.0] * p.min_samples
    band = {
        "class": "hunter",
        "level_min": 11,
        "level_max": 15,
        "method": "journaux",
        "samples": len(durations),
        "median_s": 11.0,
        "low_s": 10.0,
        "high_s": 12.0,
    }
    result = kill_time(p, class_name="hunter", level=15, measures={"bands": [band]})
    assert result.source == "measured" and result.seconds == 11.0 and result.samples == p.min_samples
    few = {**band, "samples": p.min_samples - 1}
    assert kill_time(p, class_name="hunter", level=15, measures={"bands": [few]}).source == "estimated"
    other = kill_time(p, class_name="hunter", level=40, measures={"bands": [band]})
    assert other.source == "estimated"


def test_refresh_writes_only_in_the_cache(tmp_path):
    logs = tmp_path / "Logs"
    logs.mkdir()
    shutil.copyfile(LOG, logs / "WoWCombatLog-092726_100000.txt")
    sv = tmp_path / "SavedVariables"
    sv.mkdir()
    shutil.copyfile(SV, sv / "ForeverLogger.lua")
    deps = isolated_deps(tmp_path)
    out = refresh_kill_times(deps, logs_dir=logs, sv_dir=sv)
    assert out["bands"]
    assert (deps.cache_dir / "measures" / MEASURES_FILE).is_file()
    assert load_kill_times(deps) == out
    assert not list(DATA_DIR.rglob(MEASURES_FILE))
