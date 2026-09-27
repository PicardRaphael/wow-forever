"""Talents : valeur d'un rang, points disponibles, légalité d'un build."""

from __future__ import annotations

from forever.engine.model import GameData, Points


def talent_value(gd: GameData, pts: Points, key: str, i: int = 0, default: float = 0.0) -> float:
    """Valeur `i` du rang pris (défaut si le talent n'est pas pris) ; rang borné au nombre de rangs connus.

    Registre : G3"""
    raise NotImplementedError


def points_available(gd: GameData, level: int, talented_bonus: int = 0) -> int:
    """Points de talent disponibles au niveau donné ; le bonus Legacy « Talented » avance le premier point.

    Registre : G3"""
    raise NotImplementedError


def check_build(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> list[str]:
    """Erreurs de légalité en français (liste vide : build légal).

    Registre : G3"""
    raise NotImplementedError


def legal_additions(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> list[str]:
    """Talents auxquels on peut ajouter un point maintenant, dans l'ordre de `talents.json`.

    Registre : G3"""
    raise NotImplementedError


def tree_split(gd: GameData, pts: Points) -> dict[str, int]:
    """Points dépensés par arbre.

    Registre : G3"""
    raise NotImplementedError
