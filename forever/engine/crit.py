"""Critique des sorts : chance et multiplicateur."""

from __future__ import annotations

from forever.engine.model import SCHOOL_FIRE, SCHOOL_FROST, Buffs, Character, GameData, Points
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents de critique sont exprimés en %
# Sorts concernés par les talents (lien talent -> effet : c'est la formule, pas un chiffre de jeu).
INCINERATION_SPELLS = frozenset({"fire_blast", "ice_lance", "arcane_blast", "scorch"})
WINTERS_CHILL_SPELLS = frozenset({"frostbolt", "ice_lance"})


def crit_chance(
    gd: GameData,
    key: str,
    school: str,
    pts: Points,
    ch: Character,
    *,
    frozen: bool = False,
    wc_stacks: float = 0,
    buffs: Buffs | None = None,
) -> float:
    """Chance de critique d'un sort (personnage, talents, cible gelée, Winter's Chill, buffs), bornée à [0, 1].

    Registre : A5, D4"""
    buffs = buffs or {}
    c = ch.crit
    c += talent_value(gd, pts, "arcaneInstability", 1) / PERCENT
    if school in SCHOOL_FIRE:
        c += talent_value(gd, pts, "criticalMass") / PERCENT
    if school == "arcane":
        c += talent_value(gd, pts, "arcaneImpact") / PERCENT
    if key in INCINERATION_SPELLS:
        c += talent_value(gd, pts, "incineration") / PERCENT
    if frozen:
        c += talent_value(gd, pts, "shatter") / PERCENT
    if key in WINTERS_CHILL_SPELLS:
        c += gd.constants.crit_per_winters_chill_stack * wc_stacks
    c += buffs.get("crit", 0.0)
    return max(0.0, min(1.0, c))


def crit_mult(gd: GameData, school: str, pts: Points) -> float:
    """Multiplicateur des dégâts d'un coup critique, talents d'école compris (Givre-feu : branche givre).

    Registre : A21"""
    base_bonus = gd.rules.crit_mult_spell - 1.0
    if school in SCHOOL_FROST:
        return 1 + base_bonus * (1 + talent_value(gd, pts, "iceShards") / PERCENT)
    if school == "arcane":
        return 1 + base_bonus * (1 + talent_value(gd, pts, "arcaneMind", 1) / PERCENT)
    return 1 + base_bonus


def winters_chill_crit(gd: GameData, stacks: float) -> float:
    raise NotImplementedError("T06b : Winter's Chill")
