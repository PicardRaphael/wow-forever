"""Écart d'un build de la communauté avec notre build de référence, dans son contexte et à son niveau (T05, bloc J) :
métrique analytique du contexte (meilleur choix de rotation pour chaque build), écart relatif orienté (positif : le
build de la communauté fait mieux). Contexte `pvp` des sources : profil des champs de bataille (`pvp-bg`).

Registre : I5"""

from __future__ import annotations

from collections.abc import Mapping

from forever.engine.model import GameData

SOURCE_CONTEXTS = {"leveling": "leveling", "dungeon": "dungeon", "raid": "raid", "pvp": "pvp-bg"}


def community_gap(
    gd: GameData, context: str, level: int, theirs: Mapping[str, int], ours: Mapping[str, int], race: str = "Orc"
) -> float:
    """Écart relatif orienté (leur valeur - la nôtre) / |la nôtre| de la métrique analytique du contexte.

    Registre : I5"""
    raise NotImplementedError
