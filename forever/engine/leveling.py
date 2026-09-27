"""Niveaux utiles au leveling : couleur d'une quête selon l'écart de niveau, bande des niveaux de quête utiles.

Chiffres dans `mechanics.json` (`leveling.quest_band`, règle de Classic, suppose) ; aucune constante ici."""

from __future__ import annotations

from typing import Literal

from forever.engine.model import GameData

QuestColor = Literal["gray", "green", "yellow", "orange", "red"]
USEFUL_COLORS: tuple[QuestColor, ...] = ("green", "yellow", "orange")


def gray_level(gd: GameData, player_level: int) -> int:
    """Niveau de quête le plus haut encore gris pour `player_level`.

    Registre : I7"""
    raise NotImplementedError


def quest_color(gd: GameData, player_level: int, quest_level: int) -> QuestColor:
    """Couleur d'une quête de niveau `quest_level` pour un personnage de niveau `player_level`.

    Registre : I7"""
    raise NotImplementedError


def level_band(gd: GameData, player_level: int) -> tuple[int, int]:
    """(plus bas, plus haut) niveaux de quête utiles (verts, jaunes, orange).

    Registre : I7"""
    raise NotImplementedError
