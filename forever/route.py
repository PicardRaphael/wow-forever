"""Étapes de route neutres (T04f, préparées pour RX1) : une étape à placer dans une route de leveling (aller, prendre,
rendre, cliquer, utiliser un objet, note). T04f fournit deux producteurs : la chaîne du sac de couchage
(`sleeping_bag_steps`) et les rappels de bonus d'XP (`bonus_reminders`) ; RX1 les place dans la route et les encode
au format RestedXP. Aucun chiffre de jeu ici."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from forever.engine.model import GameData
from forever.engine.xp import XpBonusState

KINDS = ("goto", "accept", "turnin", "click", "use_item", "note")
SECONDS_PER_HOUR = 3600.0  # conversion d'unité
FOOD_EXAMPLES = 3  # nourritures citées dans un rappel


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
    """Étapes de la chaîne du sac de couchage (`xp_bonuses.sleeping_bag_chain`), une par point, dans l'ordre du camp."""
    return list(chain.steps)


def bonus_reminders(gd: GameData, state: XpBonusState, *, hours: float, level: int) -> list[RouteStep]:
    """Rappels des bonus d'XP sur une séance de `hours` heures : sac de couchage reposé à chaque recharge de l'objet,
    nourriture nutritive de son niveau (sans nourriture active), tente avant la séance. Valeurs lues dans les données.

    Registre : D5, D9, E3"""
    from forever.engine.xp import xp_bonus_data

    data = xp_bonus_data(gd)
    out: list[RouteStep] = []
    bag = data.sleeping_bag
    if bag is not None and level >= bag.required_level and bag.cooldown_s > 0:
        aura = data.auras.get(bag.aura)
        count = math.ceil(hours * SECONDS_PER_HOUR / bag.cooldown_s)
        out += [
            RouteStep(
                "use_item",
                f"pose {bag.name} et reste assis dedans jusqu'à {bag.max_stacks} cumuls de "
                f"{aura.name if aura else bag.aura}",
                item_id=bag.item,
                level=level,
                at_s=i * bag.cooldown_s,
                source="xp_bonuses.json (sleeping_bag, client)",
                certainty="probable",
            )
            for i in range(count)
        ]
    foods = sorted((f for f in data.food if f.required_level <= level), key=lambda f: (-f.required_level, f.name))
    if not state.food and foods:
        names = ", ".join(f.name for f in foods[:FOOD_EXAMPLES])
        out.append(
            RouteStep(
                "note",
                f"mange une nourriture nutritive de ton niveau ({names})",
                level=level,
                at_s=0.0,
                source="xp_bonuses.json (food, client) ; xp.food_bonus",
                certainty="suppose",
            )
        )
    if data.tent_threshold_pct is not None:
        out.append(
            RouteStep(
                "note",
                "monte une tente près d'un feu de camp avant la séance (repos remonté)",
                level=level,
                at_s=0.0,
                source="xp_bonuses.json (camp, client) ; xp.camp_tent",
                certainty="probable",
            )
        )
    return sorted(out, key=lambda s: s.at_s or 0.0)
