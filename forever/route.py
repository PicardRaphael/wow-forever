"""Étapes de route neutres (T04f, préparées pour RX1) : une étape à placer dans une route de leveling (aller, prendre,
rendre, cliquer, utiliser un objet, note). T04f fournit deux producteurs : la chaîne du sac de couchage
(`sleeping_bag_steps`) et les rappels de bonus d'XP (`bonus_reminders`) ; RX1 les place dans la route et les encode
au format RestedXP. Aucun chiffre de jeu ici."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forever.engine.model import GameData
from forever.engine.xp import XpBonusState

KINDS = ("goto", "accept", "turnin", "click", "use_item", "note")


@dataclass(frozen=True)
class RouteStep:
    kind: str  # KINDS
    text: str
    quest_id: int | None = None
    item_id: int | None = None
    map: int | None = None  # uiMapID
    zone: str | None = None  # nom anglais de la carte
    x: float | None = None  # position en pourcentage de la carte
    y: float | None = None
    level: int | None = None
    at_s: float | None = None  # rappel : instant de la séance (secondes depuis son début)
    source: str = ""
    certainty: str = "suppose"


def sleeping_bag_steps(chain: Any) -> list[RouteStep]:
    raise NotImplementedError


def bonus_reminders(gd: GameData, state: XpBonusState, *, hours: float, level: int) -> list[RouteStep]:
    raise NotImplementedError
