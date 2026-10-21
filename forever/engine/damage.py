"""Multiplicateurs de dégâts et puissance des sorts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Buffs, Character, GameData, Points, Rank
from forever.engine.spells import check_rules, coefficient, dot_coefficient
from forever.engine.talents import talent_model, talent_value

PERCENT = 100.0  # conversion d'unité : les talents de dégâts sont exprimés en %
MS_PER_S = 1000.0  # conversion d'unité : périodes du client en millisecondes


# Liens sort -> talent propre à un sort et école des auras -> écoles touchées (noms, pas des chiffres de jeu).
CONE_OF_COLD, IMPROVED_CONE_OF_COLD = "cone_of_cold", "improvedConeOfCold"
AURA_SCHOOLS = {"fire": SCHOOL_FIRE, "frost": SCHOOL_FROST}


def fire_vulnerability_part(gd: GameData, school: str, stacks: int) -> float:
    """Hausse des dégâts subis par la cible pour un sort de l'école `school` : cumuls × part par cumul, pour les
    écoles de l'aura (client) ; Givre-feu compte comme feu (suppose, voir OPEN_QUESTIONS).

    Registre : A20"""
    fv = gd.fire_vulnerability
    if stacks <= 0 or not any(school in AURA_SCHOOLS.get(s, frozenset({s})) for s in fv.schools):
        return 0.0
    return min(stacks, fv.max_stacks) * fv.pct_per_stack / PERCENT


def dmg_mult(
    gd: GameData,
    school: str,
    pts: Points,
    buffs: Buffs | None = None,
    *,
    key: str | None = None,
    rules: str = "forever",
) -> float:
    """Multiplicateur de dégâts : talents globaux et d'école, talent propre au sort `key` (Improved Cone of Cold),
    puis buffs (`dmg`, `dmg_sources`) et cumuls de Fire Vulnerability sur la cible.

    `rules="forever"` : chaque source multiplie (`damage.bonus_stacking` `multiplicative`, probable, test en jeu E6 ;
    variante `additive` : bonus des buffs et de Fire Vulnerability additionnés comme le seed) ; Improved Cone of Cold aux rangs de
    `talents.json` (courbe Trait du client, décision 77). `rules="seed"` : bonus des buffs et de Fire Vulnerability additionnés dans
    un seul facteur, Improved Cone of Cold ignoré (le seed ne le connaît pas).

    Registre : A20"""
    check_rules(rules, None)
    buffs = buffs or {}
    m = 1 + talent_value(gd, pts, "arcaneInstability") / PERCENT
    if school in SCHOOL_FROST:
        m *= 1 + talent_value(gd, pts, "piercingIce") / PERCENT
        m *= frigid_power_mult(gd, pts, buffs.get("ice_barrier_shield", 0.0))
    if school in SCHOOL_FIRE:
        m *= 1 + fire_power_bonus(gd, pts, buffs.get("fire_effects", 0.0))
    sources = buffs.get("dmg_sources", ())
    fire = fire_vulnerability_part(gd, school, buffs.get("fire_vulnerability", 0))
    if rules == "seed":
        return m * (1 + buffs.get("dmg", 0.0) + sum(sources) + fire)
    if key == CONE_OF_COLD:
        m *= 1 + talent_value(gd, pts, IMPROVED_CONE_OF_COLD) / PERCENT
    if gd.constants.bonus_stacking == "additive":
        return m * (1 + buffs.get("dmg", 0.0) + sum(sources) + fire)
    m *= 1 + buffs.get("dmg", 0.0)
    for s in sources:
        m *= 1 + s
    return m * (1 + fire)


ICE_BARRIER = "iceBarrier"
FRIGID_POWER, FRIGID_SHIELDED = 1, 3  # variables du rang d'Ice Barrier : Frigid Power, bonus sous le bouclier


def frigid_power_mult(gd: GameData, pts: Points, shielded: float = 0.0) -> float:
    """Frigid Power d'Ice Barrier (correctif du serveur 112753, 70450 r6, HF2) : bonus de dégâts de Givre du talent pris
    (Ice Barrier lancé avant le combat et relancé à l'expiration, suppose), multiplié par le bonus sous le bouclier
    pondéré par `shielded` (part du temps sous le bouclier, bornée à [0, 1]) ; 1 sans le talent ou avant le
    correctif (rang sans ces variables).

    Registre : A22"""
    if pts.get(ICE_BARRIER, 0) <= 0 or ICE_BARRIER not in gd.talents:
        return 1.0
    rank = gd.talents[ICE_BARRIER].ranks[0]
    if len(rank) <= FRIGID_SHIELDED:
        return 1.0
    share = max(0.0, min(1.0, shielded))
    base = talent_value(gd, pts, ICE_BARRIER, FRIGID_POWER) / PERCENT
    return (1 + base) * (1 + share * talent_value(gd, pts, ICE_BARRIER, FRIGID_SHIELDED) / PERCENT)


FRIGID_MINUTES = 2  # variable du rang d'Ice Barrier : durée de Frigid Power, en minutes
SECONDS_PER_MINUTE = 60.0  # conversion d'unité


def frigid_power_duration_s(gd: GameData, pts: Points) -> float | None:
    """Durée de Frigid Power (s), lue dans la variable du rang d'Ice Barrier ; None sans le talent ou avant le correctif.

    Registre : A22"""
    if frigid_power_mult(gd, pts) == 1.0:
        return None
    return talent_value(gd, pts, ICE_BARRIER, FRIGID_MINUTES) * SECONDS_PER_MINUTE


def winters_chill_cone_sp(gd: GameData, key: str, wc_stacks: float) -> float:
    """Part de la puissance des sorts ajoutée au coefficient de Cone of Cold par les cumuls de Winter's Chill
    (correctif du serveur 112753 : « gains an additional x% of your spell damage », 70450 r7) ; 0 pour un autre sort.

    Registre : D4"""
    if key != CONE_OF_COLD or not wc_stacks:
        return 0.0
    return gd.constants.cone_of_cold_sp_per_winters_chill_stack * wc_stacks


def fire_power_bonus(gd: GameData, pts: Points, effects: float) -> float:
    """Bonus de Fire Power (fraction) : bonus plat du talent ; 70450 (marqueur `per_fire_effect`) : x % par effet de
    Feu du Mage sur la cible, au plus le plafond du talent (deuxième variable).

    Registre : A20"""
    if talent_model(gd, "firePower") == "per_fire_effect":
        per, cap = talent_value(gd, pts, "firePower", 0), talent_value(gd, pts, "firePower", 1)
        return min(per * effects, cap) / PERCENT
    return talent_value(gd, pts, "firePower") / PERCENT


def fire_effects_steady(gd: GameData, pts: Points, *, crit: float) -> float:
    """Effets de Feu du Mage sur la cible en régime établi d'une rotation de Feu (calcul analytique, `suppose`) : le
    DoT de Fireball, toujours renouvelé, et Ignite avec la chance qu'un des lancers de sa durée critique ; le
    simulateur Monte Carlo compte, lui, les effets réellement posés.

    Registre : A20"""
    count = 1.0
    if talent_value(gd, pts, "ignite") > 0 and "fireball" in gd.spells:
        cast = max(gd.rules.gcd_s, gd.spells["fireball"].ranks[-1].cast_time_s)
        casts = max(1.0, gd.leveling.ignite_duration_s / cast)
        count += 1 - (1 - crit) ** casts
    return count


def spell_power(ch: Character, buffs: Buffs | None = None) -> float:
    """Puissance des sorts du personnage, buffs en pourcentage puis fixes.

    Registre : G4"""
    buffs = buffs or {}
    return ch.sp * (1 + buffs.get("sp_pct", 0.0)) + buffs.get("sp_flat", 0.0)


def dot_tick_times(gd: GameData, duration_s: float, period_s: float | None = None) -> list[float]:
    """Instants des tics d'un DoT après l'impact : un tic par période, au moins un ; période `period_s`
    (`dot_tick_period_s`), `leveling.dot_tick_s` si elle n'est pas donnée (seed).

    Registre : A17"""
    tick = gd.leveling.dot_tick_s if period_s is None else period_s
    return [tick * i for i in range(1, max(1, int(duration_s / tick)) + 1)]


def dot_tick_period_s(gd: GameData, key: str, rank: Rank, *, rules: str = "forever") -> float:
    """Période des tics du DoT d'un rang (s) : période de l'aura du client (`period_ms` du composant `dot`) en
    `forever` ; `leveling.dot_tick_s` pour tout DoT en `seed`. ValueError si le rang n'a pas de DoT (`forever`).

    Registre : A17"""
    check_rules(rules, None)
    if rules == "seed":
        return gd.leveling.dot_tick_s
    periods = {c.period_ms for c in gd.scaling[key][rank.position - 1].components if c.kind == "dot"}
    if len(periods) != 1:
        raise ValueError(f"{key} rang {rank.position} : {len(periods)} période(s) de DoT, une attendue")
    return periods.pop() / MS_PER_S


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
    buffs: Buffs | None = None,
    wc_stacks: float = 0,
) -> float:
    """Dégâts de base d'un coup tiré : min + (max - min) × `u` (tirage uniforme dans [0, 1[ fourni par l'appelant)
    + coefficient (`coefficient`, selon `rules`) × puissance des sorts (buffs de puissance compris : `sp_flat`,
    `sp_pct`, 70450) ; multiplicateur sur cible gelée du sort s'il en publie un (Ice Lance) ; Cone of Cold : part de la
    puissance des sorts des cumuls de Winter's Chill (`wc_stacks`, 70450 r7).

    Registre : G4, D4"""
    c = coefficient(gd, key, rank, rules=rules, low_level_penalty=low_level_penalty)
    c += winters_chill_cone_sp(gd, key, wc_stacks)
    base = rank.damage_min + (rank.damage_max - rank.damage_min) * u + c * spell_power(ch, buffs)
    frozen_mult = gd.spells[key].frozen_mult
    if frozen and frozen_mult is not None:
        base *= frozen_mult
    return base


def dot_sp_per_tick(
    gd: GameData,
    key: str,
    rank: Rank,
    ch: Character,
    buffs: Buffs | None = None,
    *,
    rules: str = "forever",
    low_level_penalty: bool | None = None,
) -> float:
    """Part de la puissance des sorts ajoutée à chaque tic du DoT d'un rang : `dot_coefficient` × puissance des sorts
    (0 en `seed` ou sans coefficient par tic).

    Registre : A17, G4"""
    c = dot_coefficient(gd, key, rank, rules=rules, low_level_penalty=low_level_penalty)
    return c * spell_power(ch, buffs) if c else 0.0


def dot_tick_damage(gd: GameData, dot_total: float, dmg_mult: float, ticks: int, *, sp_per_tick: float = 0.0) -> float:
    """Dégâts d'un tic de DoT, hors critique : (total du rang réparti sur les tics + part de la puissance des sorts
    par tic, `dot_coefficient` × puissance des sorts) × multiplicateur de dégâts.

    Registre : A17"""
    return (dot_total + sp_per_tick * ticks) * dmg_mult / ticks


def ignite_damage(gd: GameData, pts: Points, crit_damage: float) -> float:
    """Dégâts totaux d'Ignite posés par un coup critique de feu : part du talent × dégâts du critique final (bonus en
    pourcentage déjà compris) ; les tics ne sont pas remultipliés (« Ignite no longer double dips on % damage
    increase modifiers », notes de Blizzard du 24/09/2026, build 1.60.1.70009, probable).

    Registre : A18"""
    return crit_damage * talent_value(gd, pts, "ignite") / PERCENT


class IgniteState(NamedTuple):
    """Ignite en cours sur la cible : dégâts restant à infliger et instants des tics restants."""

    remaining: float
    ticks: tuple[float, ...]


def roll_ignite(gd: GameData, state: IgniteState | None, now: float, amount: float) -> IgniteState:
    """Nouvel Ignite posé à `now` par un critique de feu de part `amount` (règle roulante, `leveling.ignite_rule`,
    suppose) : le reste non infligé de l'Ignite en cours s'ajoute, l'aura (non cumulable, client) repart pour sa
    durée et le compteur de tics repart du critique (un tic par période de l'aura). La règle `independent`
    (variante, règle du seed) ne passe pas par ici : un Ignite par critique, tics fixes (`ignite_tick_times`).

    Registre : A18"""
    lv = gd.leveling
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
