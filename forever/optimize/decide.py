"""Décision entre builds au Monte Carlo (T05, décision 85) : différence appariée des temps (ou des dégâts) combat par
combat, intervalle de confiance, gagnant ou égalité statistique départagée par l'analytique, stabilité sur plusieurs
graines. Fonctions pures : l'évaluation est passée en paramètre."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, NamedTuple, TypeVar

from forever.sim.leveling_mc import McStats

C = TypeVar("C")


class Gap(NamedTuple):
    """Différence moyenne a - b, bornes de l'intervalle de confiance, significative si l'intervalle exclut 0."""

    mean: float
    low: float
    high: float
    confidence: float
    significant: bool


class Decision(NamedTuple, Generic[C]):
    """Gagnant, second, écart apparié (gagnant - second, dans le sens de la métrique) et mode de décision
    (`monte_carlo` si l'écart est significatif, sinon `analytique`)."""

    winner: C
    runner_up: C
    gap: Gap
    decided_by: str


class Stability(NamedTuple, Generic[C]):
    """Gagnant de chaque graine et stabilité (même gagnant partout)."""

    seeds: tuple[int, ...]
    winners: tuple[C, ...]
    stable: bool


def paired_gap(a: McStats, b: McStats, confidence: float) -> Gap:
    """Différence appariée a - b (combat i contre combat i, même graine) et son intervalle à `confidence`.

    Registre : I5, J2"""
    raise NotImplementedError


def decide(
    finalists: Sequence[C],
    evaluate: Callable[[C, int], McStats],
    analytic: Callable[[C], float],
    *,
    seed: int,
    confidence: float,
    lower_is_better: bool,
) -> Decision[C]:
    """Meilleur des finalistes au Monte Carlo (moyenne), écart apparié avec le second ; si l'intervalle contient 0,
    égalité statistique départagée par l'analytique.

    Registre : I5"""
    raise NotImplementedError


def stability(
    finalists: Sequence[C],
    evaluate: Callable[[C, int], McStats],
    analytic: Callable[[C], float],
    seeds: Sequence[int],
    *,
    confidence: float,
    lower_is_better: bool,
) -> Stability[C]:
    """Décision rejouée sur chaque graine ; stable si le même gagnant sort partout.

    Registre : I5"""
    raise NotImplementedError
