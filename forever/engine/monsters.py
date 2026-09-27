"""Monstres : PV par niveau (mesure, Questie corrigé, ou modèle du seed).

Correction Questie -> Forever (décision 5 du plan T04b) : Questie charge sur Forever la base Classic Era, dont les PV
sont plus bas que ceux mesurés dès le niveau 10 ; le rapport PV Forever / PV Questie vient de `monsters.json`."""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Literal

from forever.engine.model import GameData, MonsterHp, QuestieCorrection

MobSource = Literal["measured", "seed"]
MOB_SOURCES = ("measured", "seed")


def correction_ratio(correction: QuestieCorrection | None, level: int) -> tuple[float, str]:
    """Rapport PV Forever / PV Questie au niveau donné et sa certitude : médiane mesurée au niveau s'il y en a une,
    sinon max(1, pente × niveau + ordonnée) ; `probable` entre le plus bas et le plus haut niveau mesuré, `suppose`
    au-delà (extrapolation) ; sans correction : 1, `suppose` (Questie tel quel).

    Registre : H11"""
    if correction is None:
        return 1.0, "suppose"
    certainty = "probable" if correction.level_min <= level <= correction.level_max else "suppose"
    if level in correction.levels:
        return correction.levels[level], certainty
    if correction.slope is None or correction.intercept is None:
        return 1.0, certainty
    return max(1.0, correction.slope * level + correction.intercept), certainty


def corrected_questie_value(questie_hp: float, ratio: float) -> int:
    """PV Questie × rapport, arrondis au plus proche (demi supérieur), comme les PV entiers du jeu.

    Registre : H11"""
    return math.floor(questie_hp * ratio + 0.5)


def questie_ratio(gd: GameData, level: int) -> tuple[float, str]:
    """Rapport de correction des données de la version (voir `correction_ratio`).

    Registre : H11"""
    return correction_ratio(gd.monsters.correction, level)


def corrected_questie_hp(gd: GameData, questie_hp: float, level: int) -> MonsterHp:
    """PV Questie d'un monstre normal corrigés vers Forever, avec la certitude du rapport.

    Registre : H11"""
    ratio, certainty = questie_ratio(gd, level)
    return MonsterHp(
        corrected_questie_value(questie_hp, ratio),
        certainty,
        f"Questie corrigé : {questie_hp:g} × {ratio:.4f} (monsters.json, questie_correction)",
    )


def _seed_hp(gd: GameData, level: int) -> float:
    anchors = gd.mob_model.hp_anchors
    ks = sorted(anchors)
    if level <= ks[0]:
        return anchors[ks[0]]
    for lo, hi in pairwise(ks):
        if lo <= level <= hi:
            return anchors[lo] + (anchors[hi] - anchors[lo]) * (level - lo) / (hi - lo)
    return anchors[ks[-1]]


def mob_hp(gd: GameData, level: int, mob_source: MobSource = "measured") -> MonsterHp:
    """PV d'un monstre normal du niveau donné. `measured` : agrégat de `monsters.json` (mesure des journaux, sinon
    Questie corrigé) ; `seed` : ancres de `leveling.json.mob_model` interpolées linéairement (parité avec le seed).

    Registre : H11"""
    if mob_source == "seed":
        return MonsterHp(_seed_hp(gd, level), gd.mob_model.certainty, "modèle du seed (leveling.json, hp_anchors)")
    if mob_source != "measured":
        raise ValueError(f"mob_source inconnu « {mob_source} » ({' ou '.join(MOB_SOURCES)} attendu)")
    hp = gd.monsters.hp_by_level.get(level)
    if hp is None:
        raise ValueError(f"PV des monstres inconnus au niveau {level} (monsters.json)")
    return hp


def mob_hit_damage(gd: GameData, level: int) -> float:
    """Dégâts bruts d'un coup de monstre normal, avant armure (`leveling.mob_hit_damage`).

    Registre : I6"""
    lv = gd.leveling
    return lv.mob_hit_per_level * level + lv.mob_hit_per_level_squared * level * level


def armor_reduction(gd: GameData, armor: float, attacker_level: int) -> float:
    """Réduction des dégâts physiques par l'armure du Mage (`leveling.armor_reduction`, attaquant < 60).

    Registre : I6"""
    lv = gd.leveling
    return armor / (armor + lv.armor_base + lv.armor_per_attacker_level * attacker_level)


def mob_xp(gd: GameData, level: int) -> float:
    """XP d'un monstre normal de même niveau (`leveling.mob_xp`, règle Classic ; XP de Forever en T04c).

    Registre : I6"""
    return gd.leveling.xp_base + gd.leveling.xp_per_level * level


def mob_swing_damage(gd: GameData, level: int, armor: float) -> float:
    """Dégâts d'un coup de monstre du niveau donné après l'armure du Mage.

    Registre : I6"""
    return mob_hit_damage(gd, level) * (1 - armor_reduction(gd, armor, level))


def mob_land_chance(gd: GameData) -> float:
    """Chance qu'un coup de monstre touche le Mage (`mob_model.avoid_vs_mage` du seed).

    Registre : I6"""
    return 1 - gd.mob_model.avoid_vs_mage


def mob_hit_taken(gd: GameData, hit: float, *, crit: bool) -> float:
    """Dégâts d'un coup de monstre qui touche, critique compris (`mob_model.crit_mult`).

    Registre : I6"""
    return hit * (gd.mob_model.crit_mult if crit else 1.0)


def mob_expected_hit(gd: GameData, hit: float) -> float:
    """Espérance des dégâts d'un coup de monstre qui touche (modèle analytique).

    Registre : I6"""
    mm = gd.mob_model
    return hit * (1 + mm.crit * (mm.crit_mult - 1))
