"""Niveau du lanceur au fil du temps, pour compter touchés et ratés par écart de niveau (décision 3 du plan T04b).

Sources, par priorité : `ForeverLoggerDB` (instantanés horodatés en heure locale), puis le carnet (`journey`) de la
SavedVariable de Questie (gains de niveau horodatés en heure Unix), puis un niveau saisi (`--caster-level`). Lecture
locale seulement, jamais par le réseau ; le carnet de Questie reste sur le disque de l'utilisateur."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from forever.pipeline.addon_sv import LoggerDB


class LevelTimeline(NamedTuple):
    """Points (instant local, niveau atteint), croissants ; `source` nomme leur origine."""

    points: tuple[tuple[datetime, int], ...]
    source: str

    def level_at(self, when: datetime) -> int | None:
        """Niveau du dernier point antérieur ou égal à `when` ; None avant le premier point."""
        raise NotImplementedError


class CasterLevels(NamedTuple):
    """Chronologies par priorité, puis niveau fixe de dernier recours."""

    timelines: tuple[LevelTimeline, ...] = ()
    fixed: int | None = None

    def level_at(self, when: datetime) -> tuple[int, str] | None:
        """(niveau, source) de la première chronologie qui connaît `when`, sinon le niveau fixe ; None sinon."""
        raise NotImplementedError


def from_logger_db(db: LoggerDB, guid: str) -> LevelTimeline:
    raise NotImplementedError


def logger_utc_offset(db: LoggerDB, guid: str) -> timedelta | None:
    raise NotImplementedError


def from_questie_journey(sv: Path, guid: str, *, utc_offset: timedelta | None) -> LevelTimeline:
    raise NotImplementedError
