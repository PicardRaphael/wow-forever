"""Toucher des sorts."""

from __future__ import annotations

from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Character, GameData, Points
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents de toucher sont exprimés en %


def hit_chance(gd: GameData, school: str, level_diff: int, pts: Points, ch: Character) -> float:
    """Chance de toucher selon l'écart de niveau avec la cible, les talents et le toucher d'équipement.

    Cible plus basse (écart négatif) : raté à écart 0 diminué de `miss_per_level_below` par niveau (règle Classic,
    décision 4 du plan T04b ; la ligne « - » de la table n'est plus lue) ; au-delà de la table : sa dernière ligne ;
    plancher `min_miss` dans tous les cas.

    Registre : A3, A4, H1"""
    rules = gd.rules
    t = rules.spell_miss_by_level_diff
    last = str(max(int(k) for k in t if k != "-"))
    if level_diff < 0:
        miss = t["0"] + level_diff * gd.constants.miss_per_level_below
    else:
        miss = t.get(str(level_diff), t[last])
    if school in SCHOOL_FROST or school in SCHOOL_FIRE:
        miss -= talent_value(gd, pts, "elementalPrecision") / PERCENT
    if school == "arcane":
        miss -= talent_value(gd, pts, "arcaneFocus") / PERCENT
    miss -= ch.hit_gear
    return 1.0 - max(rules.min_miss, miss)
