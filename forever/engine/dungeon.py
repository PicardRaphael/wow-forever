"""Passage d'un donjon et niveau de placement (DJ1, bloc E), fonctions pures.

Durée et monstres d'un passage, par ordre : passages relevés (ForeverLogger, InstanceTracker de Naowh Forever ;
médiane, `certain`), compte de monstres d'un addon (durée de la formule, `suppose`), formule par défaut de Factoruide
(MIT, `crates/fg-route/src/model/dungeons.rs`, lue le 2026-10-13 : minutes bornées de la forme base + pente × niveau
des monstres, monstres de même forme ; paramètres dans `mechanics.json`, `dungeon.run_defaults`, `suppose`).
Niveau de placement : niveau de la plage où le premier passage rapporte la plus grande part de niveau par heure.

Registre : I16 (durée et monstres d'un passage), I17 (niveau de placement d'un donjon dans une route)."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta
from typing import Any, NamedTuple

RUN_DEFAULTS_KEY = "dungeon.run_defaults"
SECONDS_PER_HOUR = timedelta(
    hours=True
).total_seconds()  # conversions d'unité (True : une heure, une minute ; aucun chiffre dans le moteur)
SECONDS_PER_MINUTE = timedelta(minutes=True).total_seconds()
PARAMS = ("base_minutes", "minutes_per_mob_level", "min_minutes", "max_minutes", "base_kills", "kills_per_mob_level")


class RunModel(NamedTuple):
    minutes: float
    kills: float
    source: str  # measured | addon | formula
    certainty: str
    samples: int


class Pass(NamedTuple):
    xp: float
    seconds: float

    @property
    def xp_h(self) -> float:
        return self.xp / (self.seconds / SECONDS_PER_HOUR) if self.seconds > 0 else 0.0


class Placement(NamedTuple):
    level: int
    share_h: float  # part de l'XP du niveau gagnée par heure au premier passage
    window: list[int]  # niveaux où le premier passage bat la meilleure zone


def run_defaults(values: Mapping[str, Any]) -> dict[str, float]:
    """Paramètres de la formule par défaut (`mechanics.json`, `dungeon.run_defaults`). Registre : I16"""
    raw = values[RUN_DEFAULTS_KEY]["value"]
    return {k: float(raw[k]) for k in PARAMS}


def formula_run(params: Mapping[str, float], mob_level: float) -> tuple[float, float]:
    """(minutes, monstres) de la formule de Factoruide pour un niveau de monstres. Registre : I16"""
    minutes = params["base_minutes"] + params["minutes_per_mob_level"] * mob_level
    minutes = min(max(minutes, params["min_minutes"]), params["max_minutes"])
    return minutes, params["base_kills"] + params["kills_per_mob_level"] * mob_level


def run_model(
    params: Mapping[str, float],
    mob_level: float,
    *,
    measured: Sequence[float] = (),
    measured_kills: Sequence[float] = (),
    addon_kills: float | None = None,
) -> RunModel:
    """Durée (minutes) et monstres d'un passage : relevés (`measured`, secondes ; médiane) > compte d'un addon >
    formule. Registre : I16"""
    minutes, kills = formula_run(params, mob_level)
    if measured_kills:
        kills = float(statistics.median(measured_kills))
    elif addon_kills is not None:
        kills = float(addon_kills)
    if measured:
        return RunModel(
            float(statistics.median(measured)) / SECONDS_PER_MINUTE, kills, "measured", "certain", len(measured)
        )
    if addon_kills is not None or measured_kills:
        return RunModel(minutes, kills, "addon", "suppose", 0)
    return RunModel(minutes, kills, "formula", "suppose", 0)


def first_pass(
    *, run: RunModel, kill_xp: float, quests_xp: float, quests: int, travel_s: float, quest_overhead_s: float
) -> Pass:
    """Premier passage avec quêtes : monstres et quêtes, sur prise des quêtes, aller, passage et retour.
    Registre : I14, I16"""
    seconds = run.minutes * SECONDS_PER_MINUTE + travel_s + travel_s + quest_overhead_s * quests
    return Pass(run.kills * kill_xp + quests_xp, seconds)


def repeat_pass(*, run: RunModel, kill_xp: float) -> Pass:
    """Passage suivant : monstres seuls, sur la durée du passage. Registre : I14, I16"""
    return Pass(run.kills * kill_xp, run.minutes * SECONDS_PER_MINUTE)


def placement_level(
    levels: Sequence[int],
    first_pass_xp_h: Callable[[int], float | None],
    level_xp: Callable[[int], float],
    best_zone_xp_h: Callable[[int], float | None],
) -> Placement | None:
    """Niveau qui maximise l'XP par heure du premier passage divisée par l'XP du niveau (à égalité le plus bas) ;
    `first_pass_xp_h` rend None à un niveau où le donjon ne vaut rien (quêtes grises, hors plage). Registre : I17"""
    best: tuple[float, int] | None = None  # (part, niveau)
    window: list[int] = []
    for level in levels:
        xp_h = first_pass_xp_h(level)
        if xp_h is None:
            continue
        share = xp_h / level_xp(level)
        if best is None or share > best[0]:
            best = (share, level)
        zone = best_zone_xp_h(level)
        if zone is None or xp_h > zone:
            window.append(level)
    if best is None:
        return None
    share, level = best
    return Placement(level, share, window)
