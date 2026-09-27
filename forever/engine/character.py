"""Modèle de personnage : stats estimées par niveau et race, remplacées par la fiche du personnage si fournie."""

from __future__ import annotations

from forever.engine.model import Character, CharacterOverrides, GameData


def int_per_crit(gd: GameData, level: int) -> float:
    """Intelligence pour 1 % de critique des sorts au niveau donné (niveau borné aux extrémités de la table).

    Registre : A5"""
    raise NotImplementedError


def character(gd: GameData, level: int, race: str = "Orc", overrides: CharacterOverrides | None = None) -> Character:
    """Stats du personnage. `overrides` (fiche du personnage) remplace toute estimation.

    Registre : A5, B9, G1, G2"""
    raise NotImplementedError
