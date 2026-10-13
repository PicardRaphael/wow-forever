"""Temps par monstre des classes sans moteur (T04d, bloc E) : mesuré dans les relevés du joueur, sinon estimé.

Ordre des sources (rendue avec le résultat) : moteur (Mage : simulateur de leveling, hors de ce module) ; sinon
**mesuré** pour la classe et la tranche de niveaux : durée des combats dans les journaux (première attaque du joueur
ou de son familier jusqu'à `UNIT_DIED` du monstre) et cadence de ForeverLogger (intervalle entre deux gains d'XP de
monstre d'une même séance, pauses longues écartées) ; sinon **estimé** : fourchette de `leveling.kill_time_estimate`
(`suppose`, « estimé »). Les relevés sont propres au joueur : gardés dans `<cache>/measures/kill_time.json`, jamais
dans `forever/data/`. Paramètres de mesure (taille d'échantillon, largeur des tranches, pause) : `measures.kill_time`
de `mechanics.json` ; aucun chiffre ici."""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable, Sequence
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.errors import DataSchemaError
from forever.pipeline.addon_sv import LoggerDB, XpGain, read_logger_db
from forever.pipeline.combatlog import Event, log_files, read_log

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


DAMAGE_SUFFIXES = ("_DAMAGE", "_DAMAGE_LANDED")
LOGGER_FILE = "ForeverLogger.lua"
QUARTILES = 4  # bornes basse et haute d'une tranche : premier et troisième quartiles (méthode)


def kill_params(values: dict[str, Any]) -> KillParams:
    """Paramètres lus dans les valeurs de `mechanics.json` (`measures.kill_time`, `leveling.kill_time_estimate`)."""
    try:
        measure = values["measures.kill_time"]["value"]
        estimate = values["leveling.kill_time_estimate"]
        return KillParams(
            min_samples=int(measure["min_samples"]),
            band_levels=int(measure["band_levels"]),
            pause_s=float(measure["pause_s"]),
            estimate_low_s=float(estimate["value"]["low_s"]),
            estimate_high_s=float(estimate["value"]["high_s"]),
            estimate_source=str(estimate.get("source", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DataSchemaError(
            f"mechanics.json : measures.kill_time ou leveling.kill_time_estimate illisible ({exc}).",
            "installer une version de données de T04d ou plus récente",
        ) from exc


def _is_damage(name: str) -> bool:
    return name.endswith(DAMAGE_SUFFIXES)


def _mine(unit: Any, mine: str) -> tuple[bool, bool]:
    """(frappe du joueur ou de son familier, frappe du familier)."""
    if unit is None:
        return False, False
    if unit.guid == mine:
        return True, False
    if unit.is_mine and unit.kind in ("Pet", "Creature") and unit.is_player_controlled:
        return True, True
    return False, False


def fight_durations(events: Iterable[Event], mine: str) -> list[FightDuration]:
    """Combats du joueur `mine` (ou de son familier) terminés par la mort du monstre."""
    started: dict[str, tuple[datetime, bool, int | None]] = {}
    out: list[FightDuration] = []
    for e in events:
        dest = e.dest
        if dest is None or dest.kind != "Creature":
            continue
        if _is_damage(e.name):
            ours, pet = _mine(e.source, mine)
            if not ours:
                continue
            if dest.guid not in started:
                started[dest.guid] = (e.time, pet, dest.npc_id)
            elif pet and not started[dest.guid][1]:
                begin, _, npc = started[dest.guid]
                started[dest.guid] = (begin, True, npc)
        elif e.name == "UNIT_DIED" and dest.guid in started:
            begin, pet, npc = started.pop(dest.guid)
            out.append(FightDuration(dest.guid, npc, (e.time - begin).total_seconds(), pet, begin))
    return out


def kill_cadence(gains: Sequence[XpGain], *, pause_s: float) -> list[float]:
    """Intervalles entre deux gains d'XP de monstre successifs d'une même séance (pauses de plus de `pause_s`
    écartées)."""
    times = sorted(g.time for g in gains if g.kind == "monster" and g.time is not None)
    return [float(b - a) for a, b in pairwise(times) if 0 < b - a <= pause_s]


def _band(level: int, width: int) -> tuple[int, int]:
    low = (level - 1) // width * width + 1
    return low, low + width - 1


def _summary(cls: str, band: tuple[int, int], method: str, values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    quartiles = statistics.quantiles(ordered, n=QUARTILES) if len(ordered) >= 2 else [ordered[0]] * 3
    return {
        "class": cls,
        "level_min": band[0],
        "level_max": band[1],
        "method": method,
        "samples": len(ordered),
        "median_s": statistics.median(ordered),
        "low_s": min(quartiles[0], statistics.median(ordered)),
        "high_s": max(quartiles[-1], statistics.median(ordered)),
    }


def measure_kill_times(params: KillParams, *, logs: Sequence[Path], loggers: Sequence[LoggerDB]) -> dict[str, Any]:
    """Mesures par classe et tranche de niveaux : `{"bands": [{class, level_min, level_max, method, samples,
    median_s, low_s, high_s}], "unattributed": n}` (classe et niveau lus dans ForeverLogger par le GUID)."""
    groups: dict[tuple[str, tuple[int, int], str], list[float]] = {}
    unattributed = 0
    characters = {guid: (db, c) for db in loggers for guid, c in db.characters.items()}
    for path in logs:
        _, stream = read_log(path)
        events = list(stream)
        for guid in {
            e.source.guid for e in events if e.source is not None and e.source.is_mine and e.source.kind == "Player"
        }:
            found = characters.get(guid)
            for fight in fight_durations(events, guid):
                level = found[0].level_at(guid, fight.start) if found else None
                cls = (found[1].class_ or "").lower() if found else ""
                if not cls or level is None:
                    unattributed += 1
                    continue
                groups.setdefault((cls, _band(level, params.band_levels), "journaux"), []).append(fight.seconds)
    for db in loggers:
        for character in db.characters.values():
            cls = (character.class_ or "").lower()
            by_level: dict[int, list[XpGain]] = {}
            for gain in character.xp:
                if gain.level is not None:
                    by_level.setdefault(gain.level, []).append(gain)
            for level, gains in by_level.items():
                intervals = kill_cadence(gains, pause_s=params.pause_s)
                if cls and intervals:
                    groups.setdefault((cls, _band(level, params.band_levels), "cadence"), []).extend(intervals)
    bands = [_summary(cls, band, method, values) for (cls, band, method), values in sorted(groups.items())]
    return {"bands": bands, "unattributed": unattributed}


def kill_time(params: KillParams, *, class_name: str, level: int, measures: dict[str, Any] | None) -> KillTime:
    """Temps par monstre d'une classe sans moteur : mesuré si la tranche a assez de relevés, sinon estimé."""
    cls = class_name.lower()
    candidates = [
        b
        for b in (measures or {}).get("bands", [])
        if b["class"] == cls and b["level_min"] <= level <= b["level_max"] and b["samples"] >= params.min_samples
    ]
    if candidates:
        best = min(candidates, key=lambda b: (b["method"] != "journaux", -b["samples"]))
        method = "durée des combats (journaux)" if best["method"] == "journaux" else "cadence des gains (ForeverLogger)"
        return KillTime(
            cls, level, "measured", best["median_s"], best["low_s"], best["high_s"], best["samples"], "probable", method
        )
    low, high = params.estimate_low_s, params.estimate_high_s
    return KillTime(cls, level, "estimated", (low + high) / 2, low, high, 0, "suppose", "estimé")


def refresh_kill_times(deps: Deps, *, logs_dir: Path | None = None, sv_dir: Path | None = None) -> dict[str, Any]:
    """Relit journaux et ForeverLogger, écrit `<cache>/measures/kill_time.json` et rend les mesures."""
    from forever.gamedata import MECHANICS_FILE
    from forever.store import load_version

    data = load_version(deps)
    params = kill_params(data.read_json(MECHANICS_FILE)["values"])
    wow = deps.wow_dir
    logs_dir = logs_dir or (wow / "Logs" if wow else None)
    logs = log_files(logs_dir) if logs_dir is not None and logs_dir.is_dir() else []
    if sv_dir is not None:
        paths = [sv_dir / LOGGER_FILE]
    elif wow is not None:
        paths = sorted(wow.glob(f"WTF/Account/*/SavedVariables/{LOGGER_FILE}"))
    else:
        paths = []
    loggers = [read_logger_db(p) for p in paths if p.is_file()]
    out = {**measure_kill_times(params, logs=logs, loggers=loggers), "logs": len(logs), "loggers": len(loggers)}
    target = deps.cache_dir / "measures" / MEASURES_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(json.dumps(out, ensure_ascii=False, indent=1).encode("utf-8"))
    return out


def load_kill_times(deps: Deps) -> dict[str, Any] | None:
    """Mesures gardées dans le cache (None si aucune)."""
    path = deps.cache_dir / "measures" / MEASURES_FILE
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None
