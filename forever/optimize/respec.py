"""Conseil de respec en leveling (T05, bloc H ; décision 87) : portage du conseil du seed (`advise_leveling`, parité en
mode seed) et conseil forever (gain d'heures par niveau de respec, niveau conseillé).

Méthode forever : deux chemins de l'optimiseur de leveling, à l'analytique (préréglage donné, sans Monte Carlo) :
le chemin gardé (build actuel, points suivants optimisés) et le chemin libre (meilleur ordre depuis le niveau de
départ des talents). Respec au niveau L : gain = heures du chemin gardé − heures du chemin libre, de L au niveau visé ;
bilan = gain × or par heure au niveau L − coût − trajet ; niveau conseillé = bilan le plus grand, s'il est positif.

Registre : I5"""

from __future__ import annotations

from typing import Any, NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points, Preset
from forever.engine.respec import gold_per_hour, respec_balance, respec_cost, respec_cost_certainty
from forever.engine.talents import check_build
from forever.optimize.leveling import (
    SECONDS_PER_HOUR,
    LevelingPath,
    best_choice,
    build_choices,
    level_weight,
    optimize_leveling,
)
from forever.sim.leveling_analytic import kill_analytic

RESET, KEEP = "réinitialiser", "garder"


class RespecAdvice(NamedTuple):
    """Conseil : verdict (`réinitialiser` ou `garder`), niveau conseillé (None : garder), heures gagnées, coût, bilan
    et or par heure au niveau conseillé (ou actuel), certitude du coût, (niveau, heures gagnées, bilan) par niveau,
    chemins gardé et libre."""

    verdict: str
    level: int | None
    gain_hours: float
    cost_gold: float
    balance_gold: float
    gold_per_hour: float
    cost_certainty: str
    by_level: tuple[tuple[int, float, float], ...]
    keep: LevelingPath
    free: LevelingPath


def advise_leveling(
    gd: GameData,
    level: int,
    current: Points,
    target: Points,
    hours: float,
    race: str = "Orc",
    n_previous: int = 0,
    gph: float | None = None,
    *,
    rules: str = "forever",
    **options: Any,
) -> dict[str, Any]:
    """Conseil du seed (`respec.advise_leveling`) : XP par heure du build actuel et du build cible (meilleure rotation
    à l'analytique), heures gagnées sur `hours` heures, bilan en or, verdict ; mêmes arrondis que le seed.

    Registre : I5"""
    sim = {"rules": rules, **options}

    def xp_h(pts: Points) -> float:
        return max(
            kill_analytic(gd, level, pts, race, c.rotation, **sim)["xp_h"]
            for c in build_choices(gd, level, pts, rules=rules)
        )

    cur, tgt = xp_h(current), xp_h(target)
    gain_h = hours * (1 - cur / tgt) if tgt > cur else -hours * (1 - tgt / cur)
    cost = respec_cost(gd, n_previous)
    rate = gph or gold_per_hour(gd, level)
    trip = gd.respec.trip_minutes
    value = respec_balance(gain_h, cost, rate, trip)
    return {
        "xp_h_actuel": round(cur),
        "xp_h_cible": round(tgt),
        "heures_gagnees": round(gain_h, 2),
        "cout_po": cost,
        "bilan_po_equiv": round(value, 1),
        "verdict": RESET if value > 0 else KEEP,
        "hypotheses": f"{rate} po/h (suppose), trajet {trip} min, barème {list(gd.respec.schedule_gold)}",
    }


def _hours_by_level(gd: GameData, path: LevelingPath) -> dict[int, float]:
    """Heures équivalentes de chaque niveau d'un chemin (temps de la dernière étape du niveau × poids du niveau)."""
    out: dict[int, float] = {}
    for s in path.steps:
        out[s.level] = s.time_s * level_weight(gd, s.level) / SECONDS_PER_HOUR
    return out


def advise_respec(
    gd: GameData,
    level: int,
    current: Points,
    target_level: int,
    race: str = "Orc",
    *,
    preset: Preset,
    n_previous: int = 0,
    over: CharacterOverrides | None = None,
    talented_bonus: int = 0,
    **options: Any,
) -> RespecAdvice:
    """Conseil forever : faut-il réinitialiser le build `current` (niveau `level`) d'ici au niveau `target_level`, et
    à quel niveau ; ValueError si le build actuel est illégal.

    Registre : I5"""
    errors = check_build(gd, current, level, talented_bonus)
    if errors:
        raise ValueError(f"build actuel illégal au niveau {level} : {' ; '.join(errors)}")
    search = {"beam": preset.beam, "depth": preset.depth, "shortlist": preset.shortlist, "mc_n": 0}
    common = {"over": over, "talented_bonus": talented_bonus, **search, **options}
    keep = (
        optimize_leveling(gd, race, level + 1, target_level, start=current, **common)
        if target_level > level
        else LevelingPath(0.0, dict(current), ())
    )
    free = optimize_leveling(gd, race, gd.constants.talents.first_level, target_level, **common)
    keep_h = _hours_by_level(gd, keep)
    now = best_choice(gd, level, current, race, over, full=True, **options)[0]
    keep_h[level] = round(now, 2) * level_weight(gd, level) / SECONDS_PER_HOUR
    free_h = _hours_by_level(gd, free)
    cost = respec_cost(gd, n_previous)
    trip = gd.respec.trip_minutes
    rows = []
    for lv in range(level, target_level + 1):
        gain = sum(keep_h[x] - free_h[x] for x in range(lv, target_level + 1))
        rows.append((lv, gain, respec_balance(gain, cost, gold_per_hour(gd, lv), trip)))
    best = max(rows, key=lambda r: (r[2], -r[0]))
    reset = best[2] > 0
    return RespecAdvice(
        RESET if reset else KEEP,
        best[0] if reset else None,
        best[1],
        cost,
        best[2],
        gold_per_hour(gd, best[0]),
        respec_cost_certainty(gd, n_previous),
        tuple(rows),
        keep,
        free,
    )
