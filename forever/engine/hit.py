"""Toucher des sorts."""

from __future__ import annotations

from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Character, GameData, Points
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents de toucher sont exprimés en %


def hit_chance(gd: GameData, school: str, level_diff: int, pts: Points, ch: Character) -> float:
    """Chance de toucher selon l'écart de niveau avec la cible, les talents et le toucher d'équipement.

    Écart négatif : ligne « - » de la table ; au-delà de la table : sa dernière ligne.

    Registre : A3, A4, H1"""
    rules = gd.rules
    t = rules.spell_miss_by_level_diff
    last = str(max(int(k) for k in t if k != "-"))
    miss = t.get(str(level_diff), t["-"] if level_diff < 0 else t[last])
    if school in SCHOOL_FROST or school in SCHOOL_FIRE:
        miss -= talent_value(gd, pts, "elementalPrecision") / PERCENT
    if school == "arcane":
        miss -= talent_value(gd, pts, "arcaneFocus") / PERCENT
    miss -= ch.hit_gear
    return 1.0 - max(rules.min_miss, miss)
