"""Scénarios provisoires de donjon et de raid (T05, décision 82) : boss de donjon, paquet de monstres, boss de raid
(`mechanics.json`, `build.scenarios`, suppose ; affinés en DJ1 et T09).

Tank présent : aucun coup reçu, aucun recul, aucune course ; le Mage lance depuis sa portée. Mana bornée : réserve
plus régénération en combat, sans Évocation ni potion ; une fois la mana épuisée, plus aucun dégât. Métrique : dégâts
par seconde sur la durée du scénario (paquet : jusqu'à la mort du paquet ou la fin de la durée). Arcane Power à 0 s
puis à chaque recharge. Aucune formule de combat ici : les règles viennent de `forever/engine/`.

Registre : H3, H5, I1"""

from __future__ import annotations

import random
from typing import Any, NamedTuple, TypedDict

from forever.engine.model import CharacterOverrides, GameData, Points
from forever.sim.leveling_mc import McStats

ENCOUNTER_ROTATIONS = ("frost", "fire", "arcane", "aoe")  # aoe : paquet (sorts de zone)
AOE_FILLERS = ("arcane_explosion", "blizzard", "flamestrike")  # sort de zone de remplissage de la rotation aoe


class EncounterLog(NamedTuple):
    """Lancer relevé par `encounter_fight(log=…)` : début et fin de l'incantation, sort, mana payée, dégâts infligés
    par ce lancer (toutes cibles, coups directs)."""

    start: float
    end: float
    key: str
    cost: float
    dmg: float


class EncounterResult(TypedDict):
    dps: float
    dmg: float
    duration_s: float
    oom_s: float | None  # instant où la mana manque pour le lancer suivant (None : jamais)
    taken: float
    rotation: str


def encounter_analytic(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    over: CharacterOverrides | None = None,
    **options: Any,
) -> EncounterResult:
    """Espérance d'un scénario : cycle de la rotation (dégâts et mana par seconde), fenêtres d'Arcane Power, fin de
    mana, par segments.

    Registre : H3, H5, I1"""
    raise NotImplementedError


def encounter_fight(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    rng: random.Random | None = None,
    log: list[EncounterLog] | None = None,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> EncounterResult:
    """Un combat du scénario simulé lancer par lancer (tirages de toucher, de dégâts et de critique).

    Registre : H3, H5, I1, J2"""
    raise NotImplementedError


def encounter_mc(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    n: int = 400,
    seed: int = 12345,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> McStats:
    """Statistiques des dégâts par seconde sur `n` combats du scénario, générateur à graine fixe.

    Registre : H3, H5, J2"""
    raise NotImplementedError
