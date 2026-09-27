"""Sorts : rang appris et coefficient de puissance des sorts."""

from __future__ import annotations

from forever.engine.model import GameData, Points, Rank


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
