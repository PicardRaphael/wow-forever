"""Décision entre builds au Monte Carlo (T05, décision 85) : différence appariée des temps (ou des dégâts) combat par
combat, intervalle de confiance, gagnant ou égalité statistique départagée par l'analytique, stabilité sur plusieurs
graines. Fonctions pures : l'évaluation est passée en paramètre."""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from typing import NamedTuple

from forever.sim.leveling_mc import McStats


class Gap(NamedTuple):
    """Différence moyenne a - b, bornes de l'intervalle de confiance, significative si l'intervalle exclut 0."""

    mean: float
    low: float
    high: float
    confidence: float
    significant: bool


class Decision[C](NamedTuple):
    """Gagnant, second, écart apparié (gagnant - second, dans le sens de la métrique) et mode de décision
    (`monte_carlo` si l'écart est significatif, sinon `analytique`)."""

    winner: C
    runner_up: C
    gap: Gap
    decided_by: str


class Stability[C](NamedTuple):
    """Gagnant de chaque graine et stabilité (même gagnant partout)."""

    seeds: tuple[int, ...]
    winners: tuple[C, ...]
    stable: bool


def paired_gap(a: McStats, b: McStats, confidence: float) -> Gap:
    """Différence appariée a - b (combat i contre combat i, même graine) et son intervalle à `confidence` (loi
    normale : moyenne ± z × erreur standard des différences) ; ValueError si les nombres de combats diffèrent.

    Registre : I5, J2"""
    if a.n != b.n or len(a.totals) != len(b.totals):
        raise ValueError(f"écart apparié impossible : {a.n} et {b.n} combats (même nombre attendu)")
    diffs = [x - y for x, y in zip(a.totals, b.totals, strict=True)]
    mean = statistics.mean(diffs)
    half = statistics.NormalDist().inv_cdf((1 + confidence) / 2) * statistics.stdev(diffs) / math.sqrt(len(diffs))
    low, high = mean - half, mean + half
    return Gap(mean, low, high, confidence, low > 0 or high < 0)


def _key(stats: McStats, lower_is_better: bool) -> float:
    return stats.mean if lower_is_better else -stats.mean


def decide[C](
    finalists: Sequence[C],
    evaluate: Callable[[C, int], McStats],
    analytic: Callable[[C], float],
    *,
    seed: int,
    confidence: float,
    lower_is_better: bool,
) -> Decision[C]:
    """Meilleur des finalistes au Monte Carlo (moyenne), écart apparié avec le second ; si l'intervalle contient 0,
    égalité statistique départagée par l'analytique (valeur de `analytic`, même sens que la métrique).

    Registre : I5"""
    if len(finalists) < 2:
        raise ValueError(f"{len(finalists)} finaliste(s) : au moins deux finalistes pour décider")
    stats = [(c, evaluate(c, seed)) for c in finalists]
    ranked = sorted(stats, key=lambda cs: _key(cs[1], lower_is_better))
    (first, s1), (second, s2) = ranked[0], ranked[1]
    gap = paired_gap(s1, s2, confidence)
    if gap.significant:
        return Decision(first, second, gap, "monte_carlo")
    a1, a2 = analytic(first), analytic(second)
    better_second = a2 < a1 if lower_is_better else a2 > a1
    if better_second:
        return Decision(second, first, paired_gap(s2, s1, confidence), "analytique")
    return Decision(first, second, gap, "analytique")


def stability[C](
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
    winners = tuple(
        decide(finalists, evaluate, analytic, seed=s, confidence=confidence, lower_is_better=lower_is_better).winner
        for s in seeds
    )
    return Stability(tuple(seeds), winners, len(set(map(repr, winners))) == 1)
