"""Bonus d'XP de Forever pour toutes les classes (T04f) : catalogue lu dans `xp_bonuses.json`, état des bonus d'un
personnage, « quel bonus prendre maintenant » (écart d'XP par heure calculé par le moteur, jamais par un modèle de
langage), consultation (`forever lookup xp_bonuses`, `forever_lookup(kind="xp_bonuses")`).

Aucun chiffre de jeu ici : les valeurs viennent des données de la version, les écarts de `forever/engine/xp.py`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from forever.config import Deps
from forever.engine.model import GameData
from forever.engine.xp import ActiveAura, XpBonusState

DEFAULT_SESSION_H = 2.0  # durée de séance par défaut (paramètre des outils, pas une valeur du jeu)
BONUS_NAMES = ("sleeping_bag", "food")  # bonus nommés des outils (forever sim leveling --bonus)


@dataclass(frozen=True)
class BonusAdvice:
    """Bonus absent mais accessible, et ce qu'il rapporte sur la séance (XP par heure en plus)."""

    key: str  # sleeping_bag, food, tent
    name: str
    xp_h_gain: float
    how: str
    certainty: str


def bonus_state(
    gd: GameData,
    names: Sequence[str] = (),
    *,
    auras: Sequence[ActiveAura] = (),
    legacy_ranks: Mapping[int, int] | None = None,
) -> XpBonusState:
    raise NotImplementedError


def active_bonuses(gd: GameData, state: XpBonusState) -> list[dict[str, Any]]:
    raise NotImplementedError


def best_bonus(
    gd: GameData,
    state: XpBonusState,
    *,
    level: int,
    base_xp_h: float,
    kill_share: float,
    hours: float = DEFAULT_SESSION_H,
    rested_pool: float = 0.0,
) -> list[BonusAdvice]:
    raise NotImplementedError


def catalog(gd: GameData) -> list[dict[str, Any]]:
    raise NotImplementedError


def lookup_xp_bonuses(deps: Deps, *, access: str | None = None) -> dict[str, Any]:
    raise NotImplementedError
