"""Réinitialisation des talents (T05, bloc H ; décision 87) : coût selon le barème, or gagné par heure, bilan en or
d'une respec. Portage de seed/forever-mage/scripts/respec.py (formules pures ; les temps viennent des simulateurs).

Registre : I5"""

from __future__ import annotations

from forever.engine.model import GameData

MINUTES_PER_HOUR = 60.0  # conversion d'unité


def respec_cost(gd: GameData, n_previous: int) -> float:
    """Coût en or d'une réinitialisation après `n_previous` réinitialisations (`respec.json`, dernier palier répété).

    Registre : I5"""
    raise NotImplementedError


def respec_cost_certainty(gd: GameData, n_previous: int) -> str:
    """Certitude du coût : `probable` pour les paliers observés sur la bêta, `suppose` au-delà (règle Classic).

    Registre : I5"""
    raise NotImplementedError


def gold_per_hour(gd: GameData, level: int) -> float:
    """Or gagné par heure au niveau donné : palier le plus proche en dessous (le premier sous le premier palier).

    Registre : I5"""
    raise NotImplementedError


def respec_balance(gain_hours: float, cost_gold: float, gph: float, trip_minutes: float) -> float:
    """Bilan en or d'une respec : heures gagnées × or par heure − coût − trajet (en heures) × or par heure.

    Registre : I5"""
    raise NotImplementedError
