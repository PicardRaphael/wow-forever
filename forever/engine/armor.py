"""Armure portée par le Mage selon son niveau : Frost Armor, Ice Armor ou Mage Armor, rangs et niveaux
d'apprentissage lus dans le client (`spell_scaling.json.utility`)."""

from __future__ import annotations

from typing import NamedTuple

from forever.engine.model import GameData

ARMOR_CHOICES = ("auto", "frost", "mage")


class WornArmor(NamedTuple):
    """Armure portée : type, rang, niveau d'apprentissage du rang, ralenti des attaquants, part de la régénération
    gardée en incantation (fraction), source."""

    kind: str
    rank: int
    learned_level: int
    slows_attackers: bool
    regen_while_casting: float
    source: str


def worn_armor(gd: GameData, level: int, armor: str = "auto") -> WornArmor:
    """Armure portée au niveau `level`.

    Registre : B7, I6"""
    raise NotImplementedError
