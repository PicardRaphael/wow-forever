"""Angles morts d'un build (T05, décision 88) : mécaniques absentes ou partielles du modèle qui influencent le résultat
(champ `angle_mort` du registre : talents concernés, contextes, fonction d'estimation). Chaque estimation est une
borne haute de l'effet, en fraction de la métrique, calculée avec les données de la version ; None : non chiffré.

Registre : I5"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import NamedTuple

from forever.engine.cast import expected_cast
from forever.engine.casting import cast_time
from forever.engine.character import character
from forever.engine.crit import crit_mult
from forever.engine.model import CharacterOverrides, GameData, Points
from forever.engine.monsters import mob_hp
from forever.engine.spells import best_rank
from forever.engine.talents import talent_value

CONTEXTS = ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")  # contextes des builds (forever build)
# Liens talent -> effet (noms et positions des variables de talents.json, pas des chiffres de jeu).
PRESENCE_OF_MIND, COMBUSTION, WAKE_OF_FIRE = "presenceOfMind", "combustion", "wakeOfFire"
COMBUSTION_CHARGES, WOF_CRIT = 1, 2
MAIN_SPELLS = ("frostbolt", "fireball", "pyroblast", "arcane_blast", "frostfire_bolt")
PERCENT = 100.0  # conversion d'unité


class BlindSpotRule(NamedTuple):
    """Angle mort déclaré au registre : entrée, description, statut, talents concernés (vide : tout build du contexte),
    contextes, fonction d'estimation (None : non chiffré)."""

    id: str
    description: str
    status: str
    talents: tuple[str, ...]
    contexts: tuple[str, ...]
    estimate: str | None


class BlindSpot(NamedTuple):
    """Angle mort d'un build : règle, talents du build ou de l'alternative concernés, borne haute de l'effet (fraction
    de la métrique) ou None (non chiffré)."""

    id: str
    description: str
    status: str
    talents: tuple[str, ...]
    effect: float | None


Estimator = Callable[[GameData, int, Points, str, "CharacterOverrides | None"], "float | None"]


def estimate_cooldown_talents(
    gd: GameData, level: int, pts: Points, race: str, over: CharacterOverrides | None = None
) -> float | None:
    """Presence of Mind (une incantation rendue instantanée par recharge : la plus longue des sorts principaux appris)
    et Combustion (au plus ses critiques garantis par recharge, chacun du bonus de critique) ; Cold Snap : non chiffré.
    Borne haute, fraction du temps ou des dégâts.

    Registre : I5 (estimation de l'angle mort B18)"""
    ch = character(gd, level, race, over)
    bound = 0.0
    rated = False
    cds = gd.talent_cooldowns_s
    if pts.get(PRESENCE_OF_MIND, 0) > 0:
        casts = [cast_time(gd, k, r, pts, ch) for k in MAIN_SPELLS if (r := best_rank(gd, k, level, pts)) is not None]
        if casts:
            bound += max(casts) / cds[PRESENCE_OF_MIND]
            rated = True
    if pts.get(COMBUSTION, 0) > 0 and (r := best_rank(gd, "fireball", level, pts)) is not None:
        charges = talent_value(gd, pts, COMBUSTION, COMBUSTION_CHARGES)
        extra = crit_mult(gd, "fire", pts) - 1
        bound += charges * extra * cast_time(gd, "fireball", r, pts, ch) / cds[COMBUSTION]
        rated = True
    return bound if rated else None


def estimate_wake_of_fire_crit(
    gd: GameData, level: int, pts: Points, race: str, over: CharacterOverrides | None = None
) -> float | None:
    """Bonus de critique de Wake of Fire sur le Fire Blast qui suit une mise à mort : au plus un critique de plus par
    combat, rapporté aux PV du monstre du niveau. Borne haute, fraction des dégâts d'un combat.

    Registre : I5 (estimation de l'angle mort B19)"""
    if pts.get(WAKE_OF_FIRE, 0) <= 0:
        return None
    ch = character(gd, level, race, over)
    e = expected_cast(gd, "fire_blast", level, pts, ch, 0, spell_level="character")
    if e is None:
        return None
    hit_dmg = e["direct_per_hit"] / (1 + e["crit"] * (e["crit_mult"] - 1))  # coup sans critique
    bonus = min(1.0, talent_value(gd, pts, WAKE_OF_FIRE, WOF_CRIT) / PERCENT)
    return bonus * (e["crit_mult"] - 1) * hit_dmg / mob_hp(gd, level, gd.leveling.mob_source).value  # type: ignore[arg-type]


def estimate_evocation(
    gd: GameData, level: int, pts: Points, race: str, over: CharacterOverrides | None = None
) -> float | None:
    """Évocation : mana rendue par une Évocation (régénération d'Esprit multipliée pendant sa durée) rapportée à la
    réserve : au plus autant d'incantation en plus quand la mana borne le combat. Borne haute.

    Registre : I5 (estimation de l'angle mort B10)"""
    ch = character(gd, level, race, over)
    u = gd.utility
    if level < u.evocation_level or not u.evocation_regen_mult:
        return None
    return u.evocation_regen_mult * ch.spirit_regen * u.evocation_duration_s / ch.mana


ESTIMATORS: Mapping[str, Estimator] = {
    "cooldown_talents": estimate_cooldown_talents,
    "wake_of_fire_crit": estimate_wake_of_fire_crit,
    "evocation": estimate_evocation,
}


def select_blind_spots(
    gd: GameData,
    rules: Sequence[BlindSpotRule],
    context: str,
    level: int,
    pts: Points,
    near: Points | None = None,
    race: str = "Orc",
    over: CharacterOverrides | None = None,
) -> list[BlindSpot]:
    """Angles morts d'un build dans un contexte : règles du contexte dont un talent est pris par le build ou par
    l'alternative proche `near` (toutes les règles sans talent), avec l'estimation du moteur.

    Registre : I5"""
    taken = {k for k, v in pts.items() if v > 0} | {k for k, v in (near or {}).items() if v > 0}
    out: list[BlindSpot] = []
    for rule in rules:
        if context not in rule.contexts:
            continue
        concerned = tuple(k for k in rule.talents if k in taken)
        if rule.talents and not concerned:
            continue
        estimator = ESTIMATORS.get(rule.estimate) if rule.estimate else None
        effect = estimator(gd, level, {**(near or {}), **pts}, race, over) if estimator else None
        out.append(BlindSpot(rule.id, rule.description, rule.status, concerned, effect))
    return out


def modeled_talents(gd: GameData, rules: Sequence[BlindSpotRule]) -> frozenset[str]:
    """Talents modélisés : ceux qui ne figurent dans aucun angle mort d'une entrée `absent` du registre (T06b,
    décision D7 ; départage des recommandations à égalité).

    Registre : I5"""
    unmodeled = {t for r in rules if r.status == "absent" for t in r.talents}
    return frozenset(k for k in gd.talents if k not in unmodeled)
