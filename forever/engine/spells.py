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
    ranks = gd.scaling[key]
    if not 1 <= rank <= len(ranks):
        raise ValueError(f"rang {rank} hors de 1-{len(ranks)} pour {key}")
    scaling = ranks[rank - 1]
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


SPELL_LEVELS = ("rank", "character")


def rank_damage(gd: GameData, key: str, rank: Rank, level: int, spell_level: str = "rank") -> RankValues:
    """Dégâts d'un rang : ceux de `spells.json` (`rank`, plafond de niveau du rang) ou au niveau du personnage
    (`character`, `rank_values_at_level`).

    Registre : G7"""
    if spell_level == "rank":
        return RankValues(rank.damage_min, rank.damage_max, rank.dot_total)
    if spell_level == "character":
        return rank_values_at_level(gd, key, rank.position, level)
    raise ValueError(f"spell_level inconnu « {spell_level} » ({' ou '.join(SPELL_LEVELS)} attendu)")


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


RULES = ("forever", "seed")


def _check_rules(rules: str, low_level_penalty: bool | None) -> None:
    if rules not in RULES:
        raise ValueError(f"rules inconnu « {rules} » ({' ou '.join(RULES)} attendu)")
    if rules == "seed" and low_level_penalty is False:
        raise ValueError("low_level_penalty False sans effet avec rules seed (le seed applique toujours la pénalité)")


def low_level_factor(gd: GameData, rank: Rank, low_level_penalty: bool | None = None) -> float:
    """Pénalité des sorts de bas niveau : × max(0, 1 - part par niveau × (seuil - niveau du rang)) sous le seuil
    (`coefficient.low_level`, règle Classic supposée) ; 1 si elle n'est pas appliquée (`low_level_penalty` False ;
    None : `coefficient.low_level_default` des données).

    Registre : G4"""
    rules = gd.constants.coefficients
    apply = rules.low_level_default if low_level_penalty is None else low_level_penalty
    if not apply or rank.level >= rules.low_level_threshold:
        return 1.0
    return max(0.0, 1 - rules.low_level_penalty_per_level * (rules.low_level_threshold - rank.level))


def _seed_coefficient(gd: GameData, key: str, rank: Rank) -> float:
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
    return c * low_level_factor(gd, rank, True)


def coefficient(
    gd: GameData, key: str, rank: Rank, *, rules: str = "forever", low_level_penalty: bool | None = None
) -> float:
    """Part de la puissance des sorts ajoutée aux dégâts directs d'un rang (coup direct, ou somme des éclairs d'un
    sort canalisé).

    `rules="forever"` (défaut) : coefficients du client (`spell_scaling.json`, EffectBonusCoefficient) : somme des
    composants `direct` et des composants `channel` × leurs tics, × pénalité des sorts de bas niveau
    (`low_level_factor`). `rules="seed"` : formule du seed (incantation / 3,5, bornes, canalisé, ralenti,
    coefficients fixes), pénalité toujours appliquée.

    Registre : G4"""
    _check_rules(rules, low_level_penalty)
    if rules == "seed":
        return _seed_coefficient(gd, key, rank)
    c = 0.0
    for comp in gd.scaling[key][rank.position - 1].components:
        if comp.kind == "direct":
            c += comp.bonus_coefficient
        elif comp.kind == "channel":
            c += comp.bonus_coefficient * comp.ticks
    return c * low_level_factor(gd, rank, low_level_penalty)


def dot_coefficient(
    gd: GameData, key: str, rank: Rank, *, rules: str = "forever", low_level_penalty: bool | None = None
) -> float:
    """Part de la puissance des sorts ajoutée à chaque tic de DoT d'un rang.

    Registre : A17, G4"""
    raise NotImplementedError


def dot_ticks(gd: GameData, key: str, rank: Rank, *, rules: str = "forever") -> int:
    """Nombre de tics du DoT d'un rang.

    Registre : A17"""
    raise NotImplementedError
