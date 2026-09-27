"""Niveau du lanceur au fil du temps (décision 3 du plan T04b) : ForeverLoggerDB d'abord, carnet de Questie ensuite,
niveau saisi en dernier recours. Fixtures : `tests/fixtures/questie/journey/Questie.lua` (extrait anonymisé du carnet
du Mage, deux blocs `char` du même GUID) et `tests/fixtures/addon/ForeverLoggerDB.lua` (14 à 14:50, 15 à 15:33:20)."""

from datetime import datetime, timedelta

import pytest
from conftest import FIXTURES, MINE_GUID

from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.addon_sv import read_logger_db
from forever.pipeline.levels import (
    CasterLevels,
    LevelTimeline,
    from_logger_db,
    from_questie_journey,
    logger_utc_offset,
)
from forever.pipeline.questie import read_journey

JOURNEY = FIXTURES / "questie" / "journey" / "Questie.lua"
LOGGER = FIXTURES / "addon" / "ForeverLoggerDB.lua"
UTC_OFFSET = timedelta(hours=2)


def at(hour, minute, second=0):
    """Heure locale du client, sans fuseau (comme les journaux de combat)."""
    return datetime.fromisoformat(f"2026-09-27T{hour:02d}:{minute:02d}:{second:02d}")


def test_read_journey_merges_the_blocks_of_the_guid():
    assert read_journey(JOURNEY, MINE_GUID) == [
        (1790408574, 8),
        (1790423072, 11),
        (1790439092, 12),
        (1790497699, 13),
        (1790503381, 14),
        (1790515046, 15),
    ]
    assert read_journey(JOURNEY, "Player-0000-00000009") == []


def test_questie_timeline_in_local_time():
    timeline = from_questie_journey(JOURNEY, MINE_GUID, utc_offset=UTC_OFFSET)
    assert timeline.source == "questie"
    assert timeline.level_at(at(15, 17, 25)) == 14
    assert timeline.level_at(at(15, 17, 26)) == 15
    assert timeline.level_at(datetime.fromisoformat("2026-09-26T00:00:00")) is None


def test_logger_timeline_and_offset():
    db = read_logger_db(LOGGER)
    timeline = from_logger_db(db, MINE_GUID)
    assert timeline.source == "forever_logger"
    assert (timeline.level_at(at(14, 49)), timeline.level_at(at(15, 0)), timeline.level_at(at(15, 40))) == (
        None,
        14,
        15,
    )
    assert logger_utc_offset(db, MINE_GUID) == UTC_OFFSET  # time 1790513400 = localtime 14:50:00
    assert from_logger_db(db, "Player-0000-00000009").points == ()
    assert logger_utc_offset(db, "Player-0000-00000009") is None


def test_priority_logger_then_questie_then_fixed():
    logger = LevelTimeline(((at(15, 0), 20),), "forever_logger")
    questie = from_questie_journey(JOURNEY, MINE_GUID, utc_offset=UTC_OFFSET)
    levels = CasterLevels((logger, questie), fixed=30)
    assert levels.level_at(at(15, 30)) == (20, "forever_logger")
    assert levels.level_at(at(14, 0)) == (14, "questie")
    assert levels.level_at(datetime.fromisoformat("2026-09-01T00:00:00")) == (30, "--caster-level")
    assert CasterLevels().level_at(at(15, 0)) is None


def test_journey_reader_tolerates_binary_strings(tmp_path):
    """La vraie SavedVariable contient des chaînes compressées (octets non UTF-8, accolades, guillemets échappés)."""
    sv = tmp_path / "Questie.lua"
    sv.write_bytes(
        b'QuestieConfig = {\n["char"] = {\n["Moi - Royaume"] = {\n'
        b'["blob"] = "\xf7{\\"}\\\\\x00",\n["guid"] = "Player-0000-00000000",\n'
        b'["journey"] = {\n{\n["Timestamp"] = 100,\n["Event"] = "Level",\n["NewLevel"] = 5,\n},\n'
        b'{\n["Timestamp"] = 50,\n["Event"] = "Quest",\n["Level"] = 4,\n},\n},\n},\n},\n}\n'
        b'QuestieConfigCharacter = {\n["x"] = "}",\n}\n'
    )
    assert read_journey(sv, MINE_GUID) == [(100, 5)]


def test_journey_reader_errors(tmp_path):
    with pytest.raises(PathNotFoundError):
        read_journey(tmp_path / "absent.lua", MINE_GUID)
    other = tmp_path / "other.lua"
    other.write_text("ForeverLoggerDB = {}\n", encoding="utf-8")
    with pytest.raises(DataSchemaError, match="QuestieConfig"):
        read_journey(other, MINE_GUID)
