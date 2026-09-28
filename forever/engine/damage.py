"""Multiplicateurs de dégâts et puissance des sorts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Buffs, Character, GameData, Points, Rank
from forever.engine.spells import coefficient
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents de dégâts sont exprimés en %


def dmg_mult(gd: GameData, school: str, pts: Points, buffs: Buffs | None = None) -> float:
    """Multiplicateur de dégâts : talents globaux et d'école, puis buffs.

    Registre : A20"""
    buffs = buffs or {}
    m = 1 + talent_value(gd, pts, "arcaneInstability") / PERCENT
    if school in SCHOOL_FROST:
        m *= 1 + talent_value(gd, pts, "piercingIce") / PERCENT
    if school in SCHOOL_FIRE:
        m *= 1 + talent_value(gd, pts, "firePower") / PERCENT
    m *= 1 + buffs.get("dmg", 0.0)
    return m


def spell_power(ch: Character, buffs: Buffs | None = None) -> float:
    """Puissance des sorts du personnage, buffs en pourcentage puis fixes.

    Registre : G4"""
    buffs = buffs or {}
    return ch.sp * (1 + buffs.get("sp_pct", 0.0)) + buffs.get("sp_flat", 0.0)


def dot_tick_times(gd: GameData, duration_s: float) -> list[float]:
    """Instants des tics d'un DoT après l'impact : un tic par `leveling.dot_tick_s`, au moins un (seed).

    Registre : A17"""
    tick = gd.leveling.dot_tick_s
    return [tick * i for i in range(1, max(1, int(duration_s / tick)) + 1)]


def ignite_tick_times(gd: GameData) -> list[float]:
    """Instants des tics d'Ignite après le critique, sans cumul ni rafraîchissement (`rules="seed"` : un tic par
    période de `leveling.ignite` pendant sa durée, comme le seed).

    Registre : A18"""
    lv = gd.leveling
    return [lv.ignite_tick_s * i for i in range(1, lv.ignite_ticks + 1)]


def roll_base_damage(
    gd: GameData,
    key: str,
    rank: Rank,
    ch: Character,
    u: float,
    *,
    frozen: bool = False,
    rules: str = "forever",
    low_level_penalty: bool | None = None,
) -> float:
    """Dégâts de base d'un coup tiré : min + (max - min) × `u` (tirage uniforme dans [0, 1[ fourni par l'appelant)
    + coefficient (`coefficient`, selon `rules`) × puissance des sorts ; multiplicateur sur cible gelée du sort s'il
    en publie un (Ice Lance).

    Registre : G4"""
    c = coefficient(gd, key, rank, rules=rules, low_level_penalty=low_level_penalty)
    base = rank.damage_min + (rank.damage_max - rank.damage_min) * u + c * spell_power(ch)
    frozen_mult = gd.spells[key].frozen_mult
    if frozen and frozen_mult is not None:
        base *= frozen_mult
    return base


def dot_tick_damage(gd: GameData, dot_total: float, dmg_mult: float, ticks: int) -> float:
    """Dégâts d'un tic de DoT, hors critique : total du rang × multiplicateur de dégâts, réparti sur les tics.

    Registre : A17"""
    return dot_total * dmg_mult / ticks


def ignite_damage(gd: GameData, pts: Points, crit_damage: float) -> float:
    """Dégâts totaux d'Ignite posés par un coup critique de feu (part du talent).

    Registre : A18"""
    return crit_damage * talent_value(gd, pts, "ignite") / PERCENT


class IgniteState(NamedTuple):
    """Ignite en cours sur la cible : dégâts restant à infliger et instants des tics restants."""

    remaining: float
    ticks: tuple[float, ...]


def roll_ignite(gd: GameData, state: IgniteState | None, now: float, amount: float) -> IgniteState:
    """Nouvel Ignite posé à `now` par un critique de feu de part `amount` (règle roulante, `leveling.ignite_rule`,
    suppose) : le reste non infligé de l'Ignite en cours s'ajoute, l'aura (non cumulable, client) repart pour sa
    durée et le compteur de tics repart du critique (un tic par période de l'aura).

    Registre : A18"""
    lv = gd.leveling
    if lv.ignite_rule != "rolling":
        raise ValueError(f"règle d'Ignite inconnue « {lv.ignite_rule} » (rolling attendue)")
    remaining = amount + (state.remaining if state else 0.0)
    return IgniteState(remaining, tuple(now + lv.ignite_tick_s * i for i in range(1, lv.ignite_ticks + 1)))


def ignite_ticks_due(state: IgniteState | None, until: float) -> tuple[float, IgniteState | None]:
    """(dégâts des tics dus jusqu'à `until` inclus, Ignite restant ou None) : le reste se répartit à parts égales
    sur les tics restants.

    Registre : A18"""
    if state is None:
        return 0.0, None
    due = [t for t in state.ticks if t <= until]
    if not due:
        return 0.0, state
    per_tick = state.remaining / len(state.ticks)
    left = state.ticks[len(due) :]
    if not left:
        return state.remaining, None
    dealt = per_tick * len(due)
    return dealt, IgniteState(state.remaining - dealt, left)


def roll_ignite_keep_timer(gd: GameData, state: IgniteState | None, now: float, amount: float) -> IgniteState:
    """Variante de comparaison (T04c, décision 2, non retenue) : le reste s'ajoute aux tics restants, dont les
    instants ne bougent pas ; un Ignite sans tic restant repart du critique.

    Registre : A18"""
    if state is None or not state.ticks:
        return roll_ignite(gd, None, now, amount)
    return IgniteState(state.remaining + amount, state.ticks)


def predict_ignite_ticks(
    gd: GameData, crits: Sequence[tuple[float, float]], part: float, *, keep_timer: bool = False
) -> list[tuple[float, float]]:
    """Tics (instant, dégâts) prédits pour des critiques (instant, dégâts) et une part d'Ignite `part`, selon la
    règle des données (`roll_ignite`) ou la variante qui garde le compteur de tics (`keep_timer`). Un tic qui tombe
    à l'instant d'un critique passe avant lui.

    Registre : A18"""
    roll = roll_ignite_keep_timer if keep_timer else roll_ignite
    state: IgniteState | None = None
    out: list[tuple[float, float]] = []

    def flush(until: float) -> None:
        nonlocal state
        while state is not None and state.ticks and state.ticks[0] <= until:
            at = state.ticks[0]
            dealt, state = ignite_ticks_due(state, at)
            out.append((at, dealt))

    for at, damage in sorted(crits):
        flush(at)
        state = roll(gd, state, at, part * damage)
    flush(float("inf"))
    return out
