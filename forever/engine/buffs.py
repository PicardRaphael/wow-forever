"""Auras temporaires du Mage : Arcane Blast (cumuls, expiration, consommation, bonus de dégâts des autres sorts).

Chiffres du talent `arcaneBlast` (`talents.json`, variables d'infobulle) : dégâts min et max, bonus de dégâts des
autres sorts par cumul (%), hausse du coût d'Arcane Blast par cumul (%), cumuls maximum, durée (s)."""

from __future__ import annotations

from typing import Any, NamedTuple, cast

from forever.engine.model import Buffs, GameData, Points
from forever.engine.talents import talent_value

TALENT = "arcaneBlast"
SPELL = "arcane_blast"
PERCENT = 100.0  # conversion d'unité : les variables du talent sont exprimées en %
# Positions des variables du talent dans talents.json (lien talent -> effet, pas des chiffres de jeu).
DMG_PER_STACK, COST_PER_STACK, MAX_STACKS, DURATION = 2, 3, 4, 5
# Arcane Power (talents.json, « For the next {0} sec, your spells deal {1}% more damage while costing {2}% more mana »).
ARCANE_POWER = "arcanePower"
AP_DURATION, AP_DMG, AP_COST = 0, 1, 2


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
    Consommation : tout autre sort de dégâts retire l'aura (l'appelant la remet à None).

    Registre : B15"""
    stacks = min(arcane_blast_max_stacks(gd, pts), arcane_blast_active(aura, now) + 1)
    return ArcaneBlastAura(stacks, now + talent_value(gd, pts, TALENT, DURATION))


def arcane_blast_bonus(gd: GameData, pts: Points, stacks: int, *, for_spell: str) -> Buffs:
    """Bonus de dégâts de l'aura pour `for_spell` (buff `dmg`, fraction) : +x % par cumul sur les autres sorts,
    aucun sur Arcane Blast lui-même (son aura augmente son coût, pas ses dégâts).

    Registre : B15"""
    if for_spell == SPELL or stacks <= 0:
        return {}
    return {"dmg": stacks * talent_value(gd, pts, TALENT, DMG_PER_STACK) / PERCENT}


def arcane_blast_after_spell(
    gd: GameData, pts: Points, aura: ArcaneBlastAura | None, now: float, key: str
) -> ArcaneBlastAura | None:
    """Aura après un sort de dégâts `key` lancé à `now` : Arcane Blast cumule, tout autre sort de dégâts la consomme.

    Registre : B15"""
    return arcane_blast_after_cast(gd, pts, aura, now) if key == SPELL else None


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
    raise NotImplementedError


def arcane_power_pull(clock_s: float, ready_at_s: float, window: tuple[float, float] | None) -> tuple[bool, float]:
    """Politique « au pull dès que prête » (décision 79) : (aura posée au début du combat qui commence à `clock_s`,
    instant où la recharge suivante sera écoulée).

    Registre : B15"""
    raise NotImplementedError


def arcane_power_share(cycle_s: float, cooldown_s: float) -> float:
    """Part des combats qui commencent avec Arcane Power prête (analytique) : min(1, cycle / recharge).

    Registre : B15"""
    raise NotImplementedError


def hot_streak_rules(gd: GameData, pts: Points) -> tuple[float, float, int] | None:
    """(durée de l'aura en s, réduction de l'incantation de Pyroblast par cumul en fraction, cumuls maximum) de Hot
    Streak si le talent est pris ; None sinon.

    Registre : B15"""
    raise NotImplementedError


def hot_streak_buffs(gd: GameData, pts: Points, stacks: int) -> Buffs:
    """Buff de Pyroblast lancé avec `stacks` cumuls de Hot Streak : réduction de l'incantation (`cast_reduction`).

    Registre : B15"""
    raise NotImplementedError


def missile_barrage_chance(gd: GameData, pts: Points, key: str) -> float:
    """Chance qu'un sort `key` qui touche déclenche Missile Barrage (0 sans le talent ou pour un autre sort).

    Registre : B14"""
    raise NotImplementedError


def missile_barrage_buffs(gd: GameData, pts: Points) -> Buffs:
    """Buff de l'Arcane Missiles suivant sous Missile Barrage : canalisation raccourcie (`cast_reduction`) et coût
    réduit (`cost`) ; {} sans le talent.

    Registre : B14"""
    raise NotImplementedError
