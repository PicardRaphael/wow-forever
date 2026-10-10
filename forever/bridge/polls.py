"""Calendriers des relevés de la réserve après un envoi (P06b, bloc A, décision 235), miroir de `SCHEDULE` dans
`addon/ForeverBridge/ForeverBridge.lua` (un test compare les deux). L'attente après la réponse prête est le temps
jusqu'au relevé suivant ; les relevés consommés comptent les emplacements chargés jusqu'à celui qui porte la réponse."""

from __future__ import annotations

from collections.abc import Sequence

# P06a : 3, puis toutes les 4 s jusqu'à 27, 30, puis toutes les 10 s jusqu'à 190.
CURRENT: tuple[float, ...] = (3, 7, 11, 15, 19, 23, 27, 30, *range(40, 191, 10))
# P06b : 2, puis toutes les 4 s jusqu'à 60, puis toutes les 10 s jusqu'à 190.
PROPOSED: tuple[float, ...] = (2, *range(4, 61, 4), *range(70, 191, 10))


def poll_wait(schedule: Sequence[float], ready_s: float) -> float:
    """Secondes entre la réponse prête et le relevé qui la rapporte ; ValueError après le dernier relevé."""
    raise NotImplementedError


def polls_used(schedule: Sequence[float], ready_s: float) -> int:
    """Relevés faits jusqu'à celui qui rapporte la réponse, compris."""
    raise NotImplementedError
