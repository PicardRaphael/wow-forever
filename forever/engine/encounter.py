"""Règles des scénarios de donjon et de raid (T05, décision 82) : PV des cibles, durée retenue pour les dégâts par
seconde, lancer qui tient dans la durée. Scénarios provisoires lus dans `mechanics.json` (`build.scenarios`)."""

from __future__ import annotations

import math

from forever.engine.model import GameData, Scenario
from forever.engine.monsters import mob_hp

EPSILON_S = 1e-9  # marge de méthode : un lancer qui finit exactement à la fin de la durée est gardé


def scenario_hp(gd: GameData, sc: Scenario, level: int, mob_source: str) -> list[float]:
    """PV de chaque cible du scénario : sans limite pour un boss (durée fixe), PV du monstre normal du niveau
    `level + level_offset` pour un paquet.

    Registre : H3"""
    if sc.hp == "boss":
        return [math.inf] * sc.targets
    return [mob_hp(gd, level + sc.level_offset, mob_source).value] * sc.targets  # type: ignore[arg-type]


def cast_fits(end_s: float, duration_s: float) -> bool:
    """Un lancer n'est commencé que s'il finit dans la durée du scénario.

    Registre : H5"""
    return end_s <= duration_s + EPSILON_S


def encounter_length(duration_s: float, last_end_s: float, oom_s: float | None, dead_s: float | None) -> float:
    """Durée qui divise les dégâts : mort du paquet, sinon toute la durée après une fin de mana (le reste compte sans
    dégâts), sinon la fin du dernier lancer qui tient dans la durée (la fraction de lancer qui ne tient pas est un
    artefact de découpage).

    Registre : H5"""
    if dead_s is not None:
        return dead_s
    if oom_s is not None:
        return duration_s
    return last_end_s
