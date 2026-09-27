"""Coût en mana."""

from __future__ import annotations

from forever.engine.model import SCHOOL_FROST, Buffs, Character, GameData, Points, Rank, Restore
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


def in_combat_regen_fraction(gd: GameData, pts: Points, level: int) -> float:
    """Part de la régénération d'Esprit gardée en combat (règle d'incantation) : Arcane Meditation, ou Mage Armor
    dès le niveau de son premier rang (`spells.json.utility`), bornée à 1.

    Registre : B7"""
    f = talent_value(gd, pts, "arcaneMeditation") / PERCENT
    if level >= gd.utility.mage_armor_level:
        f = max(f, gd.utility.mage_armor_regen)
    return min(1.0, f)


def _restore_rate(r: Restore, level: int) -> float:
    idx = max([i for i, lv in enumerate(r.spell_levels) if lv <= level] or [0])
    amount, duration = r.restore[idx]
    return amount / duration


def consumables(gd: GameData, level: int) -> tuple[float, float]:
    """(mana, vie) rendues par seconde par la boisson et la nourriture conjurées du plus haut rang appris.

    Registre : I6"""
    return _restore_rate(gd.utility.water, level), _restore_rate(gd.utility.food, level)


def downtime(gd: GameData, ch: Character, level: int, mana_used: float, taken: float) -> float:
    """Repos après un combat : le plus long de la boisson (mana, avec l'Esprit) et du repas (vie, avec la
    régénération de repos `leveling.rest_hp_regen_fraction`).

    Registre : I6"""
    water, food = consumables(gd, level)
    return max(mana_used / (water + ch.spirit_regen), taken / (food + gd.leveling.rest_hp_regen_fraction * ch.hp))


def master_of_elements_refund(gd: GameData, pts: Points, rank: Rank, estimated_mana: float) -> float:
    """Registre : B17"""
    raise NotImplementedError
