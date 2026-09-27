"""Niveau du lanceur au fil du temps, pour compter touchés et ratés par écart de niveau (décision 3 du plan T04b).

Sources, par priorité : `ForeverLoggerDB` (instantanés horodatés en heure locale), puis le carnet (`journey`) de la
SavedVariable de Questie (gains de niveau horodatés en heure Unix), puis un niveau saisi (`--caster-level`). Lecture
locale seulement, jamais par le réseau ; le carnet de Questie reste sur le disque de l'utilisateur.

Les journaux de combat sont en heure locale sans fuseau : une heure Unix s'y ramène par un décalage explicite
(celui d'un instantané ForeverLogger, qui porte les deux heures), sinon par le fuseau du système."""

from __future__ import annotations

from bisect import bisect_right
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from forever.pipeline.addon_sv import LoggerDB
from forever.pipeline.questie import read_journey

LOGGER_SOURCE = "forever_logger"
QUESTIE_SOURCE = "questie"
FIXED_SOURCE = "--caster-level"


class LevelTimeline(NamedTuple):
    """Points (instant local, niveau atteint), croissants ; `source` nomme leur origine."""

    points: tuple[tuple[datetime, int], ...]
    source: str

    def level_at(self, when: datetime) -> int | None:
        """Niveau du dernier point antérieur ou égal à `when` ; None avant le premier point."""
        i = bisect_right([t for t, _ in self.points], when)
        return self.points[i - 1][1] if i else None


class CasterLevels(NamedTuple):
    """Chronologies par priorité, puis niveau fixe de dernier recours."""

    timelines: tuple[LevelTimeline, ...] = ()
    fixed: int | None = None

    def level_at(self, when: datetime) -> tuple[int, str] | None:
        """(niveau, source) de la première chronologie qui connaît `when`, sinon le niveau fixe ; None sinon."""
        for timeline in self.timelines:
            level = timeline.level_at(when)
            if level is not None:
                return level, timeline.source
        return (self.fixed, FIXED_SOURCE) if self.fixed is not None else None


def _timeline(points: list[tuple[datetime, int]], source: str) -> LevelTimeline:
    return LevelTimeline(tuple(sorted(set(points))), source)


def from_logger_db(db: LoggerDB, guid: str) -> LevelTimeline:
    """Niveaux des instantanés ForeverLogger du personnage (heure locale) ; vide si le GUID est absent."""
    character = db.characters.get(guid)
    snapshots = character.snapshots if character else []
    points = [(s.localtime, s.level) for s in snapshots if s.localtime is not None and s.level is not None]
    return _timeline(points, LOGGER_SOURCE)


def logger_utc_offset(db: LoggerDB, guid: str) -> timedelta | None:
    """Décalage heure locale - heure UTC, lu sur le premier instantané qui porte les deux heures ; None sinon."""
    character = db.characters.get(guid)
    for s in character.snapshots if character else []:
        if s.time is not None and s.localtime is not None:
            return s.localtime - datetime.fromtimestamp(s.time, UTC).replace(tzinfo=None)
    return None


def _local(timestamp: int, utc_offset: timedelta | None) -> datetime:
    if utc_offset is None:
        return datetime.fromtimestamp(timestamp)  # noqa: DTZ006 : fuseau du système, comme l'heure du journal
    return datetime.fromtimestamp(timestamp, UTC).replace(tzinfo=None) + utc_offset


def from_questie_journey(sv: Path, guid: str, *, utc_offset: timedelta | None) -> LevelTimeline:
    """Gains de niveau du carnet de Questie, ramenés à l'heure locale (`utc_offset`, sinon fuseau du système)."""
    points = [(_local(ts, utc_offset), level) for ts, level in read_journey(sv, guid)]
    return _timeline(points, QUESTIE_SOURCE)
