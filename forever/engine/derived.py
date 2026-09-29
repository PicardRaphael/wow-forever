"""Valeurs dérivées des talents à cumuls (T06b, décision D4) : effet de chaque cumul, de 0 au maximum du rang, pour
que les outils rendent les tables que le modèle calculait (coût d'Arcane Blast, bonus aux autres sorts, critique de
Winter's Chill, incantation de Pyroblast sous Hot Streak). Chiffres : variables des talents (`talents.json`) et
constantes de `mechanics.json`, par les fonctions du moteur."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from forever.engine.buffs import DMG_PER_STACK, HOT_STREAK, HS_CAST_PCT, HS_MAX_STACKS, MAX_STACKS
from forever.engine.buffs import TALENT as ARCANE_BLAST
from forever.engine.character import character
from forever.engine.crit import winters_chill_crit
from forever.engine.mana import arcane_blast_cost
from forever.engine.model import GameData
from forever.engine.talents import talent_value

WINTERS_CHILL = "wintersChill"
WC_MAX_STACKS = 1  # 2e variable du rang de Winter's Chill : cumuls maximum
PERCENT = 100.0


class StackRow(TypedDict):
    stacks: int
    value: float
    mana: float | None


class StackTable(TypedDict):
    talent: str
    rank: int
    effect: str
    unit: str
    per_stack: float
    max_stacks: int
    at_max: float
    level: int | None
    rows: list[StackRow]


def _table(
    talent: str,
    rank: int,
    effect: str,
    unit: str,
    max_stacks: int,
    value: Callable[[int], float],
    level: int | None = None,
    mana: Callable[[int], float] | None = None,
) -> StackTable:
    rows: list[StackRow] = [
        {"stacks": n, "value": value(n), "mana": mana(n) if mana is not None else None} for n in range(max_stacks + 1)
    ]
    return {
        "talent": talent,
        "rank": rank,
        "effect": effect,
        "unit": unit,
        "per_stack": value(1) - value(0),
        "max_stacks": max_stacks,
        "at_max": rows[-1]["value"],
        "level": level,
        "rows": rows,
    }


def _arcane_blast(gd: GameData, rank: int, level: int | None) -> list[StackTable]:
    pts = {ARCANE_BLAST: rank}
    spell = gd.spells["arcane_blast"]
    first = spell.ranks[0]
    base = character(gd, level if level is not None else first.level)
    top = int(talent_value(gd, pts, ARCANE_BLAST, MAX_STACKS))

    def pct(n: int) -> float:
        return arcane_blast_cost(gd, first, pts, base, n) / base.base_mana * PERCENT

    def mana(n: int) -> float:
        return arcane_blast_cost(gd, first, pts, base, n)

    cost = _table(
        ARCANE_BLAST, rank, "arcane_blast_cost", "% du mana de base", top, pct, level, mana if level else None
    )
    bonus = talent_value(gd, pts, ARCANE_BLAST, DMG_PER_STACK)
    damage = _table(ARCANE_BLAST, rank, "other_spells_damage", "% de dégâts", top, lambda n: n * bonus)
    return [cost, damage]


def _winters_chill(gd: GameData, rank: int) -> list[StackTable]:
    top = int(talent_value(gd, {WINTERS_CHILL: rank}, WINTERS_CHILL, WC_MAX_STACKS))
    return [_table(WINTERS_CHILL, rank, "crit", "fraction de critique", top, lambda n: winters_chill_crit(gd, n))]


def _hot_streak(gd: GameData, rank: int) -> list[StackTable]:
    pts = {HOT_STREAK: rank}
    top = int(talent_value(gd, pts, HOT_STREAK, HS_MAX_STACKS))
    per = talent_value(gd, pts, HOT_STREAK, HS_CAST_PCT)
    return [_table(HOT_STREAK, rank, "pyroblast_cast_reduction", "% d'incantation", top, lambda n: n * per)]


def stack_tables(gd: GameData, talent: str, level: int | None = None) -> list[StackTable]:
    """Tables par cumul d'un talent à cumuls, pour chacun de ses rangs (liste vide pour un autre talent) ; `level` :
    coût d'Arcane Blast aussi en mana au niveau (mana de base du personnage).

    Registre : B11, B15, D4"""
    if talent not in gd.talents:
        return []
    ranks = range(1, gd.talents[talent].max_rank + 1)
    if talent == ARCANE_BLAST:
        return [t for r in ranks for t in _arcane_blast(gd, r, level)]
    if talent == WINTERS_CHILL:
        return [t for r in ranks for t in _winters_chill(gd, r)]
    if talent == HOT_STREAK:
        return [t for r in ranks for t in _hot_streak(gd, r)]
    return []
