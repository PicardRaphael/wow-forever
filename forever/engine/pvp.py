"""Profil PvP d'un build (T05, bloc G) : dégâts d'ouverture (burst), contrôle, survie, dégâts soutenus en kite.
Portage de seed/forever-mage/scripts/pvp.py (statut EST du seed : `suppose`) : modèle de scénarios qui compare des
builds entre eux, sans simulation de duel. Barème du seed dans `mechanics.json` (`pvp.profile`), poids par contexte
(`pvp.weights`) ; recharges du client (`spell_scaling.json.talent_cooldowns`) et sorts utilitaires (`spells.json`).

Registre : I5"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points


class PvpProfile(NamedTuple):
    """Composantes brutes du profil, score pondéré et séquence d'ouverture retenue."""

    score: float
    burst_seq: str
    burst: float
    control: float
    survival: float
    sustain: float


def pvp_score(
    gd: GameData,
    pts: Points,
    level: int = 60,
    race: str = "Orc",
    weights: Mapping[str, float] | None = None,
    over: CharacterOverrides | None = None,
    *,
    rules: str = "forever",
) -> PvpProfile:
    """Profil PvP : chaque composante normalisée par sa référence, plafonnée, pondérée (poids du contexte `bg` par
    défaut), mise à l'échelle.

    Registre : I5"""
    raise NotImplementedError


def seed_rounded(p: PvpProfile) -> dict[str, object]:
    """Profil arrondi comme le seed (`pvp.score`) : score et composantes à 0,1 près, statut EST.

    Registre : I5"""
    raise NotImplementedError
