"""Coût en mana."""

from __future__ import annotations

from forever.engine.model import SCHOOL_FROST, Buffs, Character, GameData, Points, Rank
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents de coût sont exprimés en %


def mana_cost(gd: GameData, key: str, rank: Rank, pts: Points, ch: Character, buffs: Buffs | None = None) -> float:
    """Coût d'un lancer : coût du rang (ou part du mana de base), réductions de talents, buffs de coût.

    Rang de talent sans coût publié : estimation (part du premier coût publié, sinon coût par défaut).

    Registre : B11, B17"""
    buffs = buffs or {}
    s = gd.spells[key]
    c = gd.constants
    if s.mana_pct_base:
        m = s.mana_pct_base * ch.base_mana
    elif rank.mana is None:
        published = [cost for r in s.ranks if (cost := r.mana)]
        m = published[0] * c.talent_rank_mana_ratio if published else c.talent_rank_mana_default
    else:
        m = rank.mana
    if s.school in SCHOOL_FROST:
        m *= 1 - talent_value(gd, pts, "frostChanneling") / PERCENT
    m *= 1 + buffs.get("cost", 0.0)
    return m
