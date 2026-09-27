"""Lecture de la SavedVariable ForeverLoggerDB et jointure avec les journaux (GUID, heure locale)."""

import json
from datetime import datetime

import pytest
from conftest import FIXTURES, MINE_GUID, REAL_LOG

from forever.cli import main
from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.addon_sv import read_logger_db

SAMPLE = FIXTURES / "addon" / "ForeverLoggerDB.lua"


def at(text):
    return datetime.strptime(text, "%m/%d/%Y %H:%M:%S")  # noqa: DTZ007 : heure locale du client, comme le journal


def test_read_sample():
    db = read_logger_db(SAMPLE)
    assert db.schema == 1
    me = db.characters[MINE_GUID]
    assert (me.name, me.realm, me.class_, me.race) == ("Moi", "Royaume", "MAGE", "Troll")
    assert [s.level for s in me.snapshots] == [14, 15]
    assert me.snapshots[0].talents == {80213: 2} and me.snapshots[0].reason == "connexion"
    assert len(me.xp) == 1 and me.xp[0].level == 14


def test_level_at_uses_latest_snapshot_before_the_time():
    db = read_logger_db(SAMPLE)
    assert db.level_at(MINE_GUID, at("09/27/2026 14:54:34")) == 14
    assert db.level_at(MINE_GUID, at("09/27/2026 16:00:00")) == 15
    assert db.level_at(MINE_GUID, at("09/27/2026 14:00:00")) is None
    assert db.level_at("Player-0000-99999999", at("09/27/2026 14:54:34")) is None


def test_errors(tmp_path):
    with pytest.raises(PathNotFoundError):
        read_logger_db(tmp_path / "absent.lua")
    bad = tmp_path / "bad.lua"
    bad.write_text("ForeverLoggerDB = {", encoding="utf-8")
    with pytest.raises(DataSchemaError):
        read_logger_db(bad)
    other = tmp_path / "other.lua"
    other.write_text("QuestieConfig = {}\n", encoding="utf-8")
    with pytest.raises(DataSchemaError, match="ForeverLoggerDB"):
        read_logger_db(other)


def test_logs_measure_joins_caster_level(capsys, make_deps):
    code = main(["logs", "measure", str(REAL_LOG), "--addon-sv", str(SAMPLE), "--json"], make_deps())
    assert code == 0
    (log,) = json.loads(capsys.readouterr().out)["logs"]
    assert log["caster_level"] == 14
    tally = {(h["school"], h["level_diff"]): (h["hits"], h["misses"]) for h in log["hit_tally"]}
    assert tally[("frost", -8)] == (3, 0) and tally[("arcane", -13)] == (1, 0)
    # Dernier champ du bloc avancé pour le joueur, à comparer au niveau connu (docs/OPEN_QUESTIONS.md)
    assert log["player_level_field"] == [7]
