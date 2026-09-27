"""Modèle analytique du leveling : espérance fermée du temps par monstre, environ mille fois plus rapide que le Monte
Carlo (utilisée par l'optimiseur en T05).

Portage de seed/forever-mage/scripts/sim_leveling.py (`kill_analytic`) : approche du monstre (incantations pendant
sa course, ralentie par Frostbolt), puis cycle en mêlée (sort principal allongé par le recul d'incantation, Ice Lance
pendant le gel de Frostbite et sur Fingers of Frost, Fire Blast à chaque recharge), dégâts subis hors gel, repos.
Deux termes morts du seed sont omis sans changer un seul résultat : `cyc_time` multiplie un plafond par 0, et `k`
(part de temps sur Fire Blast) n'est jamais lu. Comme le seed, le cycle compte la recharge de Fire Blast du rang,
sans Wake of Fire.

Les règles viennent de `forever/engine/` ; ce module assemble l'espérance. Registre : I1, I6."""

from __future__ import annotations

from typing import Any

from forever.engine.cast import expected_cast
from forever.engine.casting import pushback_resist_chance, pushback_s
from forever.engine.character import character
from forever.engine.mana import downtime, in_combat_regen_fraction
from forever.engine.model import CharacterOverrides, GameData, Points
from forever.engine.monsters import mob_hp, mob_swing_damage, mob_xp
from forever.engine.movement import (
    attacker_swing_s,
    frostbite_chance,
    frostbite_freeze_s,
    frostbolt_slow,
    mob_speed,
    spell_range,
    travel_time,
)
from forever.engine.spells import best_rank
from forever.engine.talents import talent_value
from forever.sim.leveling_mc import PERCENT, ROTATIONS, SECONDS_PER_HOUR, KillResult, options_with_defaults


def kill_analytic(
    gd: GameData,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    over: CharacterOverrides | None = None,
    **options: Any,
) -> KillResult:
    """Espérance d'un combat contre un monstre normal de niveau `level + level_diff`, puis du repos."""
    o = options_with_defaults(gd, rotation, options)
    lv, mm, gcd = gd.leveling, gd.mob_model, gd.rules.gcd_s
    level_diff = o["level_diff"]
    spell_level = o["spell_level"]
    ch = character(gd, level, race, over)
    mlevel = level + level_diff
    hp = mob_hp(gd, mlevel, o["mob_source"]).value
    main = ROTATIONS[rotation]
    frostbolt = main == "frostbolt"
    # empilements moyens de Winter's Chill (estimation du seed)
    wc = talent_value(gd, pts, "wintersChill", 1, 0) * min(
        1.0, talent_value(gd, pts, "wintersChill", 0) / PERCENT * lv.analytic_winters_chill_casts
    )
    e = expected_cast(gd, main, level, pts, ch, level_diff, wc_stacks=wc, spell_level=spell_level)
    if e is None:
        raise ValueError(f"{main} n'est pas appris au niveau {level}")
    c, d_cast, m_cast = e["cast_s"], e["dmg"], e["mana"]
    frng = spell_range(gd, main, pts)
    flight = travel_time(gd, main, frng, analytic=True)
    slow = frostbolt_slow(gd, pts) if frostbolt else 0.0
    run = mob_speed(gd, slow * e["hit"])
    t0 = c + flight + (frng - mm.melee_range) / run
    swing = attacker_swing_s(gd, frost_armor=True)
    p_land = 1 - mm.avoid_vs_mage
    burning = pushback_resist_chance(gd, pts, fire_school=main == "fireball")
    push_per_s = p_land / swing * pushback_s(gd) * (1 - burning)
    c_melee = c / max(lv.analytic_min_cast_fraction, 1 - push_per_s)
    # gel : Frostbite et Fingers of Frost -> Ice Lance
    fbite = frostbite_chance(gd, pts) if frostbolt else 0.0
    frz_per_cast = fbite * e["hit"] * frostbite_freeze_s(gd)
    has_il = best_rank(gd, "ice_lance", level, pts) is not None and rotation == "frost"
    il = (
        expected_cast(gd, "ice_lance", level, pts, ch, level_diff, frozen=True, wc_stacks=wc, spell_level=spell_level)
        if has_il
        else None
    )
    fof_p = talent_value(gd, pts, "fingersOfFrost", 0) / PERCENT if has_il else 0.0
    il_casts = (frz_per_cast / gcd + fof_p * e["hit"]) if has_il else 0.0
    # cycle en mêlée : un sort principal, puis Ice Lance pendant le gel
    cyc_time = c_melee + il_casts * gcd
    cyc_dmg = d_cast + (il_casts * il["dmg"] if il else 0.0)
    cyc_mana = m_cast + (il_casts * il["mana"] if il else 0.0)
    if main == "fireball":
        fbl = expected_cast(gd, "fire_blast", level, pts, ch, level_diff, spell_level=spell_level)
        if fbl:
            cyc_dmg += fbl["dmg"] * c_melee / fbl["cooldown_s"]
            cyc_mana += fbl["mana"] * c_melee / fbl["cooldown_s"]
            cyc_time += gcd * c_melee / fbl["cooldown_s"]
    n_pre = t0 / c
    if hp <= n_pre * d_cast:
        combat = hp / d_cast * c + flight
        t_melee = 0.0
        mana = hp / d_cast * m_cast
    else:
        t_melee = (hp - n_pre * d_cast) / (cyc_dmg / cyc_time)
        combat = t0 + t_melee
        mana = n_pre * m_cast + t_melee / cyc_time * cyc_mana
    frozen_frac = min(lv.analytic_freeze_cap, frz_per_cast / cyc_time) if t_melee else 0.0
    hit_raw = mob_swing_damage(gd, mlevel, ch.armor)
    taken = t_melee * (1 - frozen_frac) / swing * p_land * hit_raw * (1 + mm.crit * (mm.crit_mult - 1))
    mana = max(0.0, mana - in_combat_regen_fraction(gd, pts, level) * ch.spirit_regen * combat)
    down = downtime(gd, ch, level, mana, taken)
    total = combat + down + o["run_between_s"]
    return {
        "combat": combat,
        "mana": mana,
        "taken": taken,
        "downtime": down,
        "total": total,
        "xp_h": mob_xp(gd, level) * SECONDS_PER_HOUR / total,
    }
