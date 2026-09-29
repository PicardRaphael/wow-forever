"""Écart d'un build de la communauté avec notre build de référence, dans son contexte et à son niveau (T05, bloc J) :
métrique analytique du contexte (meilleur choix de rotation pour chaque build), écart relatif orienté (positif : le
build de la communauté fait mieux). Contexte `pvp` des sources : profil des champs de bataille (`pvp-bg`).

Registre : I5"""

from __future__ import annotations

from collections.abc import Mapping

from forever.engine.model import GameData
from forever.engine.pvp import pvp_score
from forever.optimize.endgame import PVP_CONTEXTS, context_analytic
from forever.optimize.leveling import best_choice

SOURCE_CONTEXTS = {"leveling": "leveling", "dungeon": "dungeon", "raid": "raid", "pvp": "pvp-bg"}


def community_gap(
    gd: GameData, context: str, level: int, theirs: Mapping[str, int], ours: Mapping[str, int], race: str = "Orc"
) -> float:
    """Écart relatif orienté (leur valeur - la nôtre) / |la nôtre| de la métrique analytique du contexte.

    Registre : I5"""
    ctx = SOURCE_CONTEXTS[context]

    def oriented(pts: Mapping[str, int]) -> float:
        if ctx == "leveling":
            return -best_choice(gd, level, pts, race, full=True)[0]
        if ctx in PVP_CONTEXTS:
            return pvp_score(gd, pts, level, race, gd.pvp.weights[PVP_CONTEXTS[ctx]]).score
        return context_analytic(gd, ctx, level, pts, race)[0]

    ref = oriented(ours)
    return (oriented(theirs) - ref) / abs(ref)
