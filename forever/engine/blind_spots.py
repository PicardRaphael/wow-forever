"""Angles morts d'un build (T05, décision 88) : mécaniques absentes ou partielles du modèle qui influencent le résultat
(champ `angle_mort` du registre : talents concernés, contextes, fonction d'estimation). Chaque estimation est une
borne haute de l'effet, en fraction de la métrique, calculée avec les données de la version ; None : non chiffré.

Registre : I5"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points

CONTEXTS = ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")  # contextes des builds (forever build)


class BlindSpotRule(NamedTuple):
    """Angle mort déclaré au registre : entrée, description, statut, talents concernés (vide : tout build du contexte),
    contextes, fonction d'estimation (None : non chiffré)."""

    id: str
    description: str
    status: str
    talents: tuple[str, ...]
    contexts: tuple[str, ...]
    estimate: str | None


class BlindSpot(NamedTuple):
    """Angle mort d'un build : règle, talents du build ou de l'alternative concernés, borne haute de l'effet (fraction
    de la métrique) ou None (non chiffré)."""

    id: str
    description: str
    status: str
    talents: tuple[str, ...]
    effect: float | None


Estimator = Callable[[GameData, int, Points, str, "CharacterOverrides | None"], "float | None"]


def estimate_cooldown_talents(
    gd: GameData, level: int, pts: Points, race: str, over: CharacterOverrides | None = None
) -> float | None:
    """Presence of Mind (une incantation rendue instantanée par recharge : la plus longue des sorts principaux appris)
    et Combustion (au plus ses critiques garantis par recharge, chacun du bonus de critique) ; Cold Snap : non chiffré.
    Borne haute, fraction du temps ou des dégâts.

    Registre : B18"""
    raise NotImplementedError


def estimate_wake_of_fire_crit(
    gd: GameData, level: int, pts: Points, race: str, over: CharacterOverrides | None = None
) -> float | None:
    """Bonus de critique de Wake of Fire sur le Fire Blast qui suit une mise à mort : au plus un critique de plus par
    combat, rapporté aux PV du monstre du niveau. Borne haute, fraction des dégâts d'un combat.

    Registre : B19"""
    raise NotImplementedError


def estimate_evocation(
    gd: GameData, level: int, pts: Points, race: str, over: CharacterOverrides | None = None
) -> float | None:
    """Évocation : mana rendue par une Évocation (régénération d'Esprit multipliée pendant sa durée) rapportée à la
    réserve : au plus autant d'incantation en plus quand la mana borne le combat. Borne haute.

    Registre : B10"""
    raise NotImplementedError


ESTIMATORS: Mapping[str, Estimator] = {
    "cooldown_talents": estimate_cooldown_talents,
    "wake_of_fire_crit": estimate_wake_of_fire_crit,
    "evocation": estimate_evocation,
}


def select_blind_spots(
    gd: GameData,
    rules: Sequence[BlindSpotRule],
    context: str,
    level: int,
    pts: Points,
    near: Points | None = None,
    race: str = "Orc",
    over: CharacterOverrides | None = None,
) -> list[BlindSpot]:
    """Angles morts d'un build dans un contexte : règles du contexte dont un talent est pris par le build ou par
    l'alternative proche `near` (toutes les règles sans talent), avec l'estimation du moteur.

    Registre : I5"""
    raise NotImplementedError
