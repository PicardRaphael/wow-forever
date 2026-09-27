"""`forever measures refresh` : relance toutes les mesures sur les journaux et SavedVariables présents sur disque,
compare au `monsters.json` installé, aux preuves du registre et au dernier instantané, puis écrit après accord.

Écritures (après confirmation seulement) : `monsters.json` de la version installée et le manifeste, instantané des
autres mesures dans le cache (`<cache>/measures/last.json`, état de l'outil). Les preuves du registre ne sont jamais
écrites : l'écart et le bloc `preuves` proposé s'affichent. Les PNJ d'un journal disparu du dossier sont conservés.
Lecture sur disque uniquement, jamais de réseau."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any, NamedTuple

from forever.engine.model import GameData
from forever.pipeline.questie import QuestieDB
from forever.registry import Mechanic

SNAPSHOT_DIR = "measures"
SNAPSHOT_NAME = "last.json"
SV_NAMES = ("ForeverLogger.lua", "Questie.lua")

MeasureSnapshot = dict[str, Any]
RefreshDiff = dict[str, Any]


class RefreshSources(NamedTuple):
    logs: tuple[Path, ...]
    saved_variables: tuple[Path, ...]


def collect_sources(logs_dir: Path, sv_dir: Path | None = None) -> RefreshSources:
    """Journaux (`WoWCombatLog-*.txt[.gz]`) et SavedVariables utiles (ForeverLogger, Questie) trouvés."""
    raise NotImplementedError


def remeasure(
    gd: GameData,
    sources: RefreshSources,
    questie: QuestieDB | None,
    *,
    version: str,
    installed: Mapping[str, Any] | None = None,
    fit_exclude: Collection[int] = (),
    utc_offset: timedelta | None = None,
) -> MeasureSnapshot:
    """Nouvelles mesures : table des monstres (PNJ des journaux disparus conservés), B1, A3, coûts, incantations,
    critiques, épisodes d'Ignite."""
    raise NotImplementedError


def compare(
    installed_monsters: Mapping[str, Any],
    registry: Sequence[Mechanic],
    previous: MeasureSnapshot | None,
    new: MeasureSnapshot,
) -> RefreshDiff:
    """Changements à écrire (`changed`) et écarts à afficher."""
    raise NotImplementedError


def read_snapshot(cache_dir: Path) -> MeasureSnapshot | None:
    """Dernier instantané (None s'il n'existe pas)."""
    raise NotImplementedError


def apply_refresh(new: MeasureSnapshot, data_dir: Path, cache_dir: Path) -> list[Path]:
    """Écrit `monsters.json`, le manifeste et l'instantané ; rend les chemins écrits."""
    raise NotImplementedError
