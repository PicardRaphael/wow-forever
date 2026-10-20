"""Auras temporaires du Mage : Arcane Blast (cumuls, expiration, consommation, bonus de dégâts des autres sorts).

Chiffres du talent `arcaneBlast` (`talents.json`, variables d'infobulle) : dégâts min et max, bonus de dégâts des
autres sorts par cumul (%), hausse du coût d'Arcane Blast par cumul (%), cumuls maximum, durée (s)."""

from __future__ import annotations

import math
from typing import Any, NamedTuple, cast

from forever.engine.model import Buffs, Character, GameData, Points
from forever.engine.talents import talent_model, talent_value

TALENT = "arcaneBlast"
SPELL = "arcane_blast"
PERCENT = 100.0  # conversion d'unité : les variables du talent sont exprimées en %
# Positions des variables du talent dans talents.json (lien talent -> effet, pas des chiffres de jeu).
DMG_PER_STACK, COST_PER_STACK, MAX_STACKS, DURATION = 2, 3, 4, 5
# Arcane Power (talents.json, « For the next {0} sec, your spells deal {1}% more damage while costing {2}% more mana »).
ARCANE_POWER = "arcanePower"
AP_DURATION, AP_DMG, AP_COST = 0, 1, 2
# Hot Streak (« grant Hot Streak for {0} sec. Hot Streak reduces the cast time of Pyroblast by {1}%, stacking up to {2}
# times ») : sorts dont un critique non périodique donne un cumul (description du talent).
HOT_STREAK = "hotStreak"
HS_DURATION, HS_CAST_PCT, HS_MAX_STACKS = 0, 1, 2
HOT_STREAK_SPELLS = frozenset({"fireball", "frostfire_bolt", "fire_blast", "scorch"})
PYROBLAST = "pyroblast"
# Missile Barrage (« Arcane Blast {0}% chance, Fireball, Frostbolt, Frostfire Bolt {1}% chance ... reduce the channeled
# duration of your next Arcane Missiles by {2}%, reduce the Mana cost by {3}% »).
MISSILE_BARRAGE = "missileBarrage"
MB_AB_CHANCE, MB_OTHER_CHANCE, MB_CHANNEL_PCT, MB_COST_PCT = 0, 1, 2, 3
MB_OTHER_SPELLS = frozenset({"fireball", "frostbolt", "frostfire_bolt"})
ARCANE_MISSILES = "arcane_missiles"
# 70450 (marqueur `missile_hits`) : « Arcane Blast {0}%, chaque projectile d'Arcane Missiles {1}%, Arcane Wrath,
# Fireball, Frostbolt, Frostfire Bolt {2}% ... canalisation raccourcie de {3}%, coût réduit de {4}% ».
MB_HITS_AB, MB_HITS_MISSILE, MB_HITS_OTHER, MB_HITS_CHANNEL, MB_HITS_COST = 0, 1, 2, 3, 4
MB_HITS_OTHER_SPELLS = frozenset({"arcane_wrath", "fireball", "frostbolt", "frostfire_bolt"})
INTELLECT_SP = "intellect_spell_power"  # 70450 : Arcane Blast donne une part de l'Intelligence en puissance des sorts
# Arcane Wrath (70450, « gains additional Spell Damage equal to {2}% of your maximum Mana »)
ARCANE_WRATH, ARCANE_WRATH_SPELL, AW_MANA_PCT = "arcaneWrath", "arcane_wrath", 2


class ArcaneBlastAura(NamedTuple):
    stacks: int
    expires: float


def arcane_blast_max_stacks(gd: GameData, pts: Points) -> int:
    """Cumuls maximum de l'aura d'Arcane Blast (0 sans le talent).

    Registre : B15"""
    return int(talent_value(gd, pts, TALENT, MAX_STACKS))


def arcane_blast_active(aura: ArcaneBlastAura | None, now: float) -> int:
    """Cumuls actifs à `now` (0 si l'aura est absente ou expirée).

    Registre : B15"""
    return aura.stacks if aura is not None and now < aura.expires else 0


def arcane_blast_after_cast(gd: GameData, pts: Points, aura: ArcaneBlastAura | None, now: float) -> ArcaneBlastAura:
    """Aura après un Arcane Blast lancé à `now` : un cumul de plus (borné au maximum du talent), durée relancée.
    Consommation : tout autre sort de dégâts retire l'aura (l'appelant la remet à None). 70450 (marqueur
    `intellect_spell_power`) : la durée court depuis la **première** application, jamais relancée.

    Registre : B15"""
    active = arcane_blast_active(aura, now)
    stacks = min(arcane_blast_max_stacks(gd, pts), active + 1)
    if talent_model(gd, TALENT) == INTELLECT_SP and active and aura is not None:
        return ArcaneBlastAura(stacks, aura.expires)
    return ArcaneBlastAura(stacks, now + talent_value(gd, pts, TALENT, DURATION))


def arcane_blast_bonus(gd: GameData, pts: Points, stacks: int, *, for_spell: str, ch: Character | None = None) -> Buffs:
    """Bonus de dégâts de l'aura pour `for_spell` (buff `dmg`, fraction) : +x % par cumul sur les autres sorts,
    aucun sur Arcane Blast lui-même (son aura augmente son coût, pas ses dégâts). 70450 (marqueur
    `intellect_spell_power`) : x % de l'Intelligence de `ch` en puissance des sorts par cumul (`sp_flat`), sur tous
    les sorts, Arcane Blast compris.

    Registre : B15"""
    if talent_model(gd, TALENT) == INTELLECT_SP:
        if stacks <= 0 or ch is None:
            return {}
        return {"sp_flat": stacks * talent_value(gd, pts, TALENT, DMG_PER_STACK) / PERCENT * ch.intellect}
    if for_spell == SPELL or stacks <= 0:
        return {}
    return {"dmg": stacks * talent_value(gd, pts, TALENT, DMG_PER_STACK) / PERCENT}


def arcane_blast_after_spell(
    gd: GameData, pts: Points, aura: ArcaneBlastAura | None, now: float, key: str
) -> ArcaneBlastAura | None:
    """Aura après un sort de dégâts `key` lancé à `now` : Arcane Blast cumule, tout autre sort de dégâts la consomme ;
    70450 (marqueur `intellect_spell_power`) : les autres sorts la laissent jusqu'à son expiration.

    Registre : B15"""
    if key == SPELL:
        return arcane_blast_after_cast(gd, pts, aura, now)
    return aura if talent_model(gd, TALENT) == INTELLECT_SP else None


def arcane_power_buffs(gd: GameData, pts: Points) -> Buffs:
    """Buffs de l'aura d'Arcane Power (talent pris) : bonus de dégâts en source distincte (`dmg_sources`, multiplié
    aux autres bonus en mode forever) et hausse du coût (`cost`) ; {} sans le talent. L'aura (durée du talent,
    recharge du client) n'est pas gérée ici : l'appelant décide quand elle est active.

    Registre : A20, B15"""
    if talent_value(gd, pts, ARCANE_POWER, AP_DMG) <= 0:
        return {}
    return {
        "dmg_sources": (talent_value(gd, pts, ARCANE_POWER, AP_DMG) / PERCENT,),
        "cost": talent_value(gd, pts, ARCANE_POWER, AP_COST) / PERCENT,
    }


def fire_vulnerability_buffs(gd: GameData, stacks: int) -> Buffs:
    """Cumuls de Fire Vulnerability sur la cible (buff `fire_vulnerability`), bornés au maximum du client ; {} sans
    cumul. Effet sur les dégâts : `dmg_mult`.

    Registre : A20"""
    n = min(stacks, gd.fire_vulnerability.max_stacks)
    return {"fire_vulnerability": n} if n > 0 else {}


def merge_buffs(*buffs: Buffs | None) -> Buffs:
    """Réunion de plusieurs buffs : somme des bonus scalaires, sources de dégâts distinctes mises bout à bout,
    cumuls de Fire Vulnerability au plus grand (une seule aura sur la cible).

    Registre : A20"""
    out: dict[str, Any] = {}
    for b in buffs:
        raw: dict[str, Any] = dict(b or {})
        for k, v in raw.items():
            if k == "dmg_sources":
                out[k] = (*out.get(k, ()), *v)
            elif k == "fire_vulnerability":
                out[k] = max(out.get(k, 0), v)
            else:
                out[k] = out.get(k, 0.0) + v
    return cast(Buffs, out)


# --- T05 : Arcane Power dans les rotations, Hot Streak, Missile Barrage ------------------------------------------


def arcane_power_window(gd: GameData, pts: Points) -> tuple[float, float] | None:
    """(durée de l'aura en s, recharge en s) d'Arcane Power si le talent est pris : durée du talent (`talents.json`),
    recharge du client (`spell_scaling.json.talent_cooldowns`) ; None sans le talent.

    Registre : B15"""
    duration = talent_value(gd, pts, ARCANE_POWER, AP_DURATION)
    if duration <= 0:
        return None
    return duration, gd.talent_cooldowns_s[ARCANE_POWER]


def arcane_power_pull(clock_s: float, ready_at_s: float, window: tuple[float, float] | None) -> tuple[bool, float]:
    """Politique « au pull dès que prête » (décision 79) : (aura posée au début du combat qui commence à `clock_s`,
    instant où la recharge suivante sera écoulée).

    Registre : B15"""
    if window is None or clock_s < ready_at_s:
        return False, ready_at_s
    return True, clock_s + window[1]


def arcane_power_share(cycle_s: float, cooldown_s: float) -> float:
    """Part des combats qui commencent avec Arcane Power prête (analytique) : min(1, cycle / recharge).

    Registre : B15"""
    return min(1.0, cycle_s / cooldown_s)


def hot_streak_rules(gd: GameData, pts: Points) -> tuple[float, float, int] | None:
    """(durée de l'aura en s, réduction de l'incantation de Pyroblast par cumul en fraction, cumuls maximum) de Hot
    Streak si le talent est pris ; None sinon. Durée : variable de l'infobulle du client (rang de talents.json depuis la
    révision 2, T06b) ; `duration_s` du talent seulement dans la copie du seed (`_seed_talents.json`, mode seed).

    Registre : B15"""
    if pts.get(HOT_STREAK, 0) <= 0:
        return None
    talent = gd.talents[HOT_STREAK]
    duration = talent.duration_s if talent.duration_s is not None else talent_value(gd, pts, HOT_STREAK, HS_DURATION)
    return (
        duration,
        talent_value(gd, pts, HOT_STREAK, HS_CAST_PCT) / PERCENT,
        int(talent_value(gd, pts, HOT_STREAK, HS_MAX_STACKS)),
    )


def hot_streak_buffs(gd: GameData, pts: Points, stacks: int) -> Buffs:
    """Buff de Pyroblast lancé avec `stacks` cumuls de Hot Streak : réduction de l'incantation (`cast_reduction`).

    Registre : B15"""
    rules = hot_streak_rules(gd, pts)
    if rules is None or stacks <= 0:
        return {}
    return {"cast_reduction": min(stacks, rules[2]) * rules[1]}


def missile_barrage_chance(gd: GameData, pts: Points, key: str, *, missiles: float = 1.0) -> float:
    """Chance qu'un sort `key` qui touche déclenche Missile Barrage (0 sans le talent ou pour un autre sort).
    70450 (marqueur `missile_hits`) : aussi chaque projectile d'Arcane Missiles (`missiles` projectiles :
    1 - (1 - p)^missiles) et Arcane Wrath.

    Registre : B14"""
    if talent_model(gd, MISSILE_BARRAGE) == "missile_hits":
        if key == SPELL:
            return talent_value(gd, pts, MISSILE_BARRAGE, MB_HITS_AB) / PERCENT
        if key == ARCANE_MISSILES:
            per = talent_value(gd, pts, MISSILE_BARRAGE, MB_HITS_MISSILE) / PERCENT
            return 1 - (1 - per) ** missiles if per > 0 else 0.0
        if key in MB_HITS_OTHER_SPELLS:
            return talent_value(gd, pts, MISSILE_BARRAGE, MB_HITS_OTHER) / PERCENT
        return 0.0
    if key == SPELL:
        return talent_value(gd, pts, MISSILE_BARRAGE, MB_AB_CHANCE) / PERCENT
    if key in MB_OTHER_SPELLS:
        return talent_value(gd, pts, MISSILE_BARRAGE, MB_OTHER_CHANCE) / PERCENT
    return 0.0


def missile_barrage_buffs(gd: GameData, pts: Points) -> Buffs:
    """Buff de l'Arcane Missiles suivant sous Missile Barrage : canalisation raccourcie (`cast_reduction`) et coût
    réduit (`cost`) ; {} sans le talent.

    Registre : B14"""
    if pts.get(MISSILE_BARRAGE, 0) <= 0:
        return {}
    hits = talent_model(gd, MISSILE_BARRAGE) == "missile_hits"  # 70450 : variables décalées d'un rang
    return {
        "cast_reduction": talent_value(gd, pts, MISSILE_BARRAGE, MB_HITS_CHANNEL if hits else MB_CHANNEL_PCT) / PERCENT,
        "cost": -talent_value(gd, pts, MISSILE_BARRAGE, MB_HITS_COST if hits else MB_COST_PCT) / PERCENT,
    }


def arcane_missiles_count(gd: GameData, position: int) -> float:
    """Projectiles d'un rang d'Arcane Missiles (tics de canalisation de `spell_scaling.json`) ; 1 sans donnée.

    Registre : B14"""
    ranks = gd.scaling.get(ARCANE_MISSILES, ())
    if not 1 <= position <= len(ranks):
        return 1.0
    ticks = sum(c.ticks for c in ranks[position - 1].components if c.kind == "channel")
    return ticks if ticks > 0 else 1.0


def arcane_wrath_bonus(gd: GameData, pts: Points, ch: Character) -> Buffs:
    """Arcane Wrath (70450, talent en or) : puissance des sorts en plus égale à x % du mana maximum, sur lui seul
    (`sp_flat`) ; {} sans le talent.

    Registre : B15"""
    if pts.get(ARCANE_WRATH, 0) <= 0:
        return {}
    return {"sp_flat": talent_value(gd, pts, ARCANE_WRATH, AW_MANA_PCT) / PERCENT * ch.mana}


def arcane_power_windows(gd: GameData, pts: Points, duration_s: float) -> list[tuple[float, float]]:
    """Fenêtres d'Arcane Power d'une rencontre de durée fixe : aura à 0 s puis à chaque recharge (décision 79) ;
    aucune sans le talent.

    Registre : B15"""
    window = arcane_power_window(gd, pts)
    if window is None:
        return []
    length, cooldown = window
    return [(k * cooldown, min(duration_s, k * cooldown + length)) for k in range(math.ceil(duration_s / cooldown))]
