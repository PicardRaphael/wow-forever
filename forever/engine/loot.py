"""Passages d'un donjon pour obtenir ses objets (CJ1, bloc 4b, décision 277), fonctions pures : chaque objet tombe
indépendamment à chaque passage avec son taux (fraction) ; espérance du nombre de passages pour les obtenir tous
(inclusion-exclusion sur les objets voulus du donjon) et plus petit nombre de passages qui les donne tous avec la chance
demandée. Taux lus dans les sources (DJ1), jamais écrits ici.

Registre : I20."""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence

MAX_RUNS = 10_000  # borne de la recherche du nombre de passages (garde-fou de calcul, pas une valeur du jeu)


def expected_runs(rates: Sequence[float]) -> float:
    """Espérance du nombre de passages pour obtenir chacun des objets de taux `rates` (au moins une fois) : somme sur
    les sous-ensembles non vides S de (-1)^(|S|+1) / (1 - prod(1 - p_i, i dans S)) ; infini si un taux est nul.

    Registre : I20"""
    if not rates:
        return 0.0
    if any(p <= 0 for p in rates):
        return math.inf
    total = 0.0
    for size in range(1, len(rates) + 1):
        for subset in itertools.combinations(rates, size):
            none = math.prod(1 - p for p in subset)
            total += (-1) ** (size + 1) / (1 - none)
    return total


def runs_for_chance(rates: Sequence[float], chance: float) -> int | None:
    """Plus petit nombre de passages n tel que la probabilité d'avoir obtenu tous les objets, prod(1 - (1 - p_i)^n),
    atteigne `chance` ; None si un taux est nul (jamais atteint).

    Registre : I20"""
    if not rates:
        return 0
    if any(p <= 0 for p in rates):
        return None
    for n in range(1, MAX_RUNS + 1):
        if math.prod(1 - (1 - p) ** n for p in rates) >= chance:
            return n
    return None
