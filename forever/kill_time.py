"""Temps par monstre des classes sans moteur (T04d, bloc E) : mesuré dans les relevés du joueur, sinon estimé.

Ordre des sources (rendue avec le résultat) : moteur (Mage : simulateur de leveling, hors de ce module) ; sinon
**mesuré** pour la classe et la tranche de niveaux : durée des combats dans les journaux (première attaque du joueur
ou de son familier jusqu'à `UNIT_DIED` du monstre) et cadence de ForeverLogger (intervalle entre deux gains d'XP de
monstre d'une même séance, pauses longues écartées) ; sinon **estimé** : fourchette de `leveling.kill_time_estimate`
(`suppose`, « estimé »). Les relevés sont propres au joueur : gardés dans `<cache>/measures/kill_time.json`, jamais
dans `forever/data/`. Paramètres de mesure (taille d'échantillon, largeur des tranches, pause) : `measures.kill_time`
de `mechanics.json` ; aucun chiffre ici."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.pipeline.addon_sv import LoggerDB, XpGain
from forever.pipeline.combatlog import Event

SOURCES = ("engine", "measured", "estimated")
MEASURES_FILE = "kill_time.json"


class FightDuration(NamedTuple):
    mob: str  # GUID du monstre
    npc_id: int | None
    seconds: float
    pet: bool  # le familier a frappé pendant le combat
    start: Any  # heure locale du début (datetime)


class KillTime(NamedTuple):
    class_name: str
    level: int
    source: str  # « engine », « measured » ou « estimated »
    seconds: float
    low: float
    high: float
    samples: int
    certainty: str
    method: str  # journaux, cadence de ForeverLogger, estimation


class KillParams(NamedTuple):
    min_samples: int
    band_levels: int
    pause_s: float
    estimate_low_s: float
    estimate_high_s: float
    estimate_source: str


def kill_params(values: dict[str, Any]) -> KillParams:
    """Paramètres lus dans les valeurs de `mechanics.json` (`measures.kill_time`, `leveling.kill_time_estimate`)."""
    raise NotImplementedError


def fight_durations(events: Iterable[Event], mine: str) -> list[FightDuration]:
    """Combats du joueur `mine` (ou de son familier) terminés par la mort du monstre."""
    raise NotImplementedError


def kill_cadence(gains: Sequence[XpGain], *, pause_s: float) -> list[float]:
    """Intervalles entre deux gains d'XP de monstre successifs d'une même séance (pauses de plus de `pause_s`
    écartées)."""
    raise NotImplementedError


def measure_kill_times(params: KillParams, *, logs: Sequence[Path], loggers: Sequence[LoggerDB]) -> dict[str, Any]:
    """Mesures par classe et tranche de niveaux : `{"bands": [{class, level_min, level_max, method, samples,
    median_s, low_s, high_s}], "unattributed": n}` (classe et niveau lus dans ForeverLogger par le GUID)."""
    raise NotImplementedError


def kill_time(params: KillParams, *, class_name: str, level: int, measures: dict[str, Any] | None) -> KillTime:
    """Temps par monstre d'une classe sans moteur : mesuré si la tranche a assez de relevés, sinon estimé."""
    raise NotImplementedError


def refresh_kill_times(deps: Deps, *, logs_dir: Path | None = None, sv_dir: Path | None = None) -> dict[str, Any]:
    """Relit journaux et ForeverLogger, écrit `<cache>/measures/kill_time.json` et rend les mesures."""
    raise NotImplementedError


def load_kill_times(deps: Deps) -> dict[str, Any] | None:
    """Mesures gardées dans le cache (None si aucune)."""
    raise NotImplementedError
