"""Armure portée par le Mage selon son niveau : Frost Armor, Ice Armor ou Mage Armor, rangs et niveaux
d'apprentissage lus dans le client (`spell_scaling.json.utility`)."""

from __future__ import annotations

from typing import NamedTuple

from forever.engine.model import ArmorRank, GameData

ARMOR_CHOICES = ("auto", "frost", "mage")
ARMOR_NAMES = {"frost_armor": "Frost Armor", "ice_armor": "Ice Armor", "mage_armor": "Mage Armor"}
# Effets retenus par decode_rules.json.utility_spells (noms des clés de spell_scaling.json.utility).
REGEN_EFFECT = "regen_while_casting_pct"
CHILL_EFFECT = "chill_on_hit_spell"
PERCENT = 100.0  # conversion d'unité : la part de régénération est exprimée en %


class WornArmor(NamedTuple):
    """Armure portée : type, rang, niveau d'apprentissage du rang, ralenti des attaquants, part de la régénération
    gardée en incantation (fraction), source."""

    kind: str
    rank: int
    learned_level: int
    slows_attackers: bool
    regen_while_casting: float
    source: str


def _best(gd: GameData, kind: str, level: int) -> ArmorRank | None:
    learned = [a for a in gd.armors.get(kind, ()) if a.learned_level <= level]
    return learned[-1] if learned else None


def worn_armor(gd: GameData, level: int, armor: str = "auto") -> WornArmor:
    """Armure portée au niveau `level`, au plus haut rang appris (niveaux d'apprentissage du client) :
    `frost` : Ice Armor dès son premier rang, sinon Frost Armor ; `mage` : Mage Armor (ValueError sous son niveau
    d'apprentissage : un choix impossible n'est jamais remplacé) ; `auto` : Mage Armor dès qu'elle est apprise, sinon
    comme `frost` (T04c, décision 3). Ralenti des attaquants : armure qui déclenche un ralenti sur un coup reçu.

    Registre : B7, I6"""
    if armor not in ARMOR_CHOICES:
        raise ValueError(f"armor inconnue « {armor} » ({', '.join(ARMOR_CHOICES)} attendue)")
    worn = _best(gd, "mage_armor", level) if armor in ("auto", "mage") else None
    if worn is None and armor == "mage":
        first = gd.armors["mage_armor"][0]
        raise ValueError(
            f"{ARMOR_NAMES['mage_armor']} n'est pas apprise au niveau {level} (rang 1 au niveau {first.learned_level})"
        )
    worn = worn or _best(gd, "ice_armor", level) or _best(gd, "frost_armor", level)
    if worn is None:
        raise ValueError(f"aucune armure apprise au niveau {level}")
    return WornArmor(
        kind=worn.kind,
        rank=worn.rank,
        learned_level=worn.learned_level,
        slows_attackers=CHILL_EFFECT in worn.effects,
        regen_while_casting=worn.effects.get(REGEN_EFFECT, 0.0) / PERCENT,
        source=(
            f"client {gd.game_version} : {ARMOR_NAMES.get(worn.kind, worn.kind)} rang {worn.rank} (sort "
            f"{worn.spell_id}), appris au niveau {worn.learned_level} (spell_scaling.json.utility)"
        ),
    )
