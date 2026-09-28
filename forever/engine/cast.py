"""Espérance d'un lancer : agrège toucher, critique, dégâts, temps et mana."""

from __future__ import annotations

from forever.engine.casting import cast_time
from forever.engine.crit import crit_chance, crit_mult
from forever.engine.damage import dmg_mult, spell_power
from forever.engine.hit import hit_chance
from forever.engine.mana import clearcast_cost_factor, mana_cost
from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Buffs, CastEstimate, Character, GameData, Points
from forever.engine.spells import best_rank, coefficient, dot_coefficient, dot_ticks, rank_damage
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents sont exprimés en %


def expected_cast(
    gd: GameData,
    key: str,
    level: int,
    pts: Points,
    ch: Character,
    level_diff: int = 0,
    *,
    frozen: bool = False,
    wc_stacks: float = 0,
    buffs: Buffs | None = None,
    frozen_mult: bool = True,
    spell_level: str = "rank",
    rules: str = "forever",
    low_level_penalty: bool | None = None,
) -> CastEstimate | None:
    """Espérance d'un sort : dégâts (toucher, critique, multiplicateurs, DoT qui critiquent, Ignite), mana
    (Frost Channeling, Master of Elements, Clearcasting), temps d'incantation, portée. None si le sort n'est pas appris.

    Portée : celle du sort, sinon la portée par défaut des données (sort de zone autour du lanceur).
    Cible gelée : multiplicateur de dégâts du sort s'il en publie un (Ice Lance), `frozen_mult=False` pour l'ignorer.

    `spell_level` : dégâts du rang (`rank`, défaut, parité avec le seed) ou au niveau du personnage (`character`) ;
    le rang rendu porte les dégâts retenus.

    `rules` : coefficients du client (`forever`, défaut) ou formule du seed (`seed`) ; `low_level_penalty` : pénalité
    des sorts de bas niveau (None : clé des données ; refusée à False avec `seed`), voir `coefficient`.

    Registre : A17, A18, A20, B12, B17, C2, G4, G7"""
    r = best_rank(gd, key, level, pts)
    if not r:
        return None
    if spell_level != "rank":
        low, high, dot_total = rank_damage(gd, key, r, level, spell_level)
        r = r._replace(damage_min=low, damage_max=high, dot_total=dot_total)
    s = gd.spells[key]
    school = s.school
    hit = hit_chance(gd, school, level_diff, pts, ch)
    crit = crit_chance(gd, key, school, pts, ch, frozen=frozen, wc_stacks=wc_stacks, buffs=buffs)
    cm = crit_mult(gd, school, pts)
    dm = dmg_mult(gd, school, pts, buffs, key=key, rules=rules)
    sp = spell_power(ch, buffs)
    c = coefficient(gd, key, r, rules=rules, low_level_penalty=low_level_penalty)
    base = (r.damage_min + r.damage_max) / 2.0 + c * sp
    if frozen and frozen_mult and s.frozen_mult is not None:
        base *= s.frozen_mult
    direct = base * dm * (1 + crit * (cm - 1))
    dot_sp = 0.0  # part de la puissance des sorts sur la durée du DoT (forever : coefficient par tic du client)
    if r.dot_total:
        per_tick = dot_coefficient(gd, key, r, rules=rules, low_level_penalty=low_level_penalty)
        dot_sp = dot_ticks(gd, key, r, rules=rules) * per_tick * sp
    dot = (r.dot_total + dot_sp) * dm * (1 + (crit * (cm - 1) if gd.rules.dot_can_crit else 0.0))
    ignite = 0.0
    if school in SCHOOL_FIRE:
        ignite = crit * base * dm * cm * talent_value(gd, pts, "ignite") / PERCENT
    dmg = hit * (direct + dot + ignite)
    mana = mana_cost(gd, key, r, pts, ch, buffs)
    base_mana_cost = r.mana if r.mana else mana
    if school in SCHOOL_FIRE or school in SCHOOL_FROST:
        mana -= hit * crit * talent_value(gd, pts, "masterOfElements") / PERCENT * base_mana_cost
    mana *= clearcast_cost_factor(gd, pts, hit)
    return {
        "key": key,
        "rank": r,
        "school": school,
        "hit": hit,
        "crit": crit,
        "crit_mult": cm,
        "dmg_mult": dm,
        "dmg": dmg,
        "direct_per_hit": direct,
        "dot": dot,
        "ignite": ignite,
        "mana": mana,
        "cast_s": cast_time(gd, key, r, pts, ch, buffs),
        "range_yd": s.range_yd if s.range_yd is not None else gd.constants.default_range_yd,
        "cooldown_s": r.cooldown_s,
    }
