"""Sorts : rang appris, coefficient de puissance des sorts, dégâts d'un rang au niveau du personnage."""

from __future__ import annotations

import math
from typing import NamedTuple

from forever.engine.model import GameData, Points, Rank


class RankValues(NamedTuple):
    damage_min: float
    damage_max: float
    dot_total: float


def _half_up(x: float) -> float:
    """Arrondi au demi supérieur, comme le décodeur (0,5 -> 1)."""
    return math.floor(round(x, 9) + 0.5)


def _normalize(x: float) -> float:
    rounded = round(x, 9)
    return int(rounded) if rounded.is_integer() else rounded


def rank_values_at_level(gd: GameData, key: str, rank: int, level: int) -> RankValues:
    """Dégâts d'un rang (position à partir de 1) pour un personnage de niveau `level` : chaque effet est évalué à
    son niveau borné par son niveau de base et son niveau maximal (`spell_scaling.json`), puis arrondi au demi
    supérieur ; au plafond de niveau, reproduit les rangs de `spells.json` décodés du client.

    Registre : G7"""
    scaling = gd.scaling[key][rank - 1]
    low = high = dot = 0.0
    for c in scaling.components:
        at = max(c.base_level, min(level, c.max_level))
        points = c.base_points + c.points_per_level * (at - c.base_level)
        a, b = _half_up(points * (1 - c.variance / 2)), _half_up(points * (1 + c.variance / 2))
        if c.kind == "direct":
            low, high = low + a, high + b
        elif c.kind == "channel":
            low, high = low + a * c.ticks, high + b * c.ticks
        else:
            dot += a * c.ticks
    return RankValues(_normalize(low), _normalize(high), _normalize(dot))


def best_rank(gd: GameData, key: str, level: int, pts: Points) -> Rank | None:
    """Plus haut rang appris au niveau donné. Un sort de talent exige le talent ; son rang 1 vient du talent.

    Registre : G4"""
    s = gd.spells[key]
    if s.talent is not None and pts.get(s.talent, 0) <= 0:
        return None
    if s.talent is not None:
        ok = [s.ranks[0], *(r for r in s.ranks[1:] if r.level <= level)]
    else:
        ok = [r for r in s.ranks if r.level <= level]
    return ok[-1] if ok else None


def coefficient(gd: GameData, key: str, rank: Rank) -> float:
    """Part de la puissance des sorts ajoutée aux dégâts d'un rang (pénalité des sorts de bas niveau comprise).

    Registre : G4"""
    rules = gd.constants.coefficients
    spell = gd.spells[key]
    fixed = rules.fixed.get(key)
    if fixed is not None:
        if fixed.cast_s is not None:
            c = fixed.cast_s / rules.cast_divisor
        else:
            assert fixed.value is not None  # garanti par gamedata : value ou cast_s
            c = fixed.value * rules.slow_factor if fixed.slowed else fixed.value
    elif spell.channel:
        c = min(rank.cast_time_s, rules.channel_cap_s) / rules.cast_divisor
    else:
        c = min(rules.cast_max_s, max(rules.cast_min_s, rank.cast_time_s)) / rules.cast_divisor
        if spell.slow:
            c *= rules.slow_factor
    if rank.level < rules.low_level_threshold:
        c *= max(0.0, 1 - rules.low_level_penalty_per_level * (rules.low_level_threshold - rank.level))
    return c
