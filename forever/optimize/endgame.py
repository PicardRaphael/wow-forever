"""Build d'un contexte de fin de partie à un niveau donné (donjon, raid ; T05, décision 84) : départs multiples (un par
arbre et par hybride), recherche locale (déplacer un point en gardant la légalité) jusqu'à un optimum local, tri à
l'analytique, décision au Monte Carlo apparié.

Métrique d'un contexte à plusieurs scénarios (`build.contexts`) : dégâts totaux / durée totale retenue, combat par
combat au Monte Carlo (le i-ème boss avec le i-ème paquet) ; rotation choisie par scénario, talents communs.

Registre : I5"""

from __future__ import annotations

from typing import Any, NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points
from forever.optimize.leveling import BuildChoice
from forever.sim.leveling_mc import McStats


class Candidate(NamedTuple):
    """Build candidat : talents, choix par scénario, valeur analytique du contexte, statistiques du Monte Carlo
    (None avant la décision)."""

    points: dict[str, int]
    choices: dict[str, BuildChoice]
    analytic: float
    stats: McStats | None


def context_scenarios(gd: GameData, context: str) -> tuple[str, ...]:
    """Scénarios d'un contexte (`build.contexts`) ; ValueError si le contexte est inconnu.

    Registre : I5"""
    raise NotImplementedError


def context_analytic(
    gd: GameData,
    context: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    over: CharacterOverrides | None = None,
    **options: Any,
) -> tuple[float, dict[str, BuildChoice]]:
    """(dégâts par seconde du contexte, meilleur choix par scénario) à l'analytique.

    Registre : H3, H5, I5"""
    raise NotImplementedError


def context_mc(
    gd: GameData,
    context: str,
    level: int,
    pts: Points,
    choices: dict[str, BuildChoice],
    race: str = "Orc",
    n: int = 200,
    seed: int = 12345,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> McStats:
    """Dégâts par seconde du contexte, combat par combat (un combat de chaque scénario par tirage), graine fixe.

    Registre : I5, J2"""
    raise NotImplementedError


def neighbors(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> list[dict[str, int]]:
    """Builds voisins : un point retiré d'un talent et placé sur un autre, builds légaux seulement, dans l'ordre de
    `talents.json` (déterministe).

    Registre : G3, I5"""
    raise NotImplementedError


def optimize_context(
    gd: GameData,
    context: str,
    level: int,
    race: str = "Orc",
    *,
    shortlist: int = 4,
    mc_n: int = 200,
    seed: int = 12345,
    depth: int = 2,
    over: CharacterOverrides | None = None,
    talented_bonus: int = 0,
    **options: Any,
) -> list[Candidate]:
    """Candidats classés du contexte au niveau donné (meilleur d'abord) : départs par arbre et hybrides, recherche
    locale, tri à l'analytique, Monte Carlo apparié sur les `shortlist` meilleurs.

    Registre : I5"""
    raise NotImplementedError
