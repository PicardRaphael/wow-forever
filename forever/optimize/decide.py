"""Décision entre builds au Monte Carlo (T05, décision 85) : différence appariée des temps (ou des dégâts) combat par
combat, intervalle de confiance, gagnant ou égalité statistique départagée par l'analytique, stabilité sur plusieurs
graines. Fonctions pures : l'évaluation est passée en paramètre."""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from typing import Any, NamedTuple

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


# Origine d'une décision de l'optimiseur (T06b, décision D7) : écart significatif au Monte Carlo ; talent modélisé
# préféré à égalité ; choix non départagé par le calcul ; point de passage vers un palier ; candidat gardé par
# l'anticipation du faisceau ; passe sans Monte Carlo ; un seul candidat.
DECIDED_BY = (
    "monte_carlo",
    "modelise",
    "non_departage",
    "passage_palier",
    "anticipation",
    "analytique",
    "seul_candidat",
)


def gap_dict(g: Gap) -> dict[str, Any]:
    """Écart brut (a − b) et `advantage` : sa valeur absolue, avantage du meilleur des deux (T06b)."""
    return {
        "mean": g.mean,
        "advantage": abs(g.mean),
        "low": g.low,
        "high": g.high,
        "confidence": g.confidence,
        "significant": g.significant,
    }


def tie_break(
    cands: Sequence[tuple[str, McStats]],
    modeled: frozenset[str] | None,
    confidence: float,
    *,
    lower_is_better: bool = True,
) -> dict[str, Any]:
    """Choix entre candidats mesurés sur les mêmes combats : le meilleur au Monte Carlo si son avance est
    significative ; sinon, parmi les candidats à égalité (écart apparié non significatif avec le meilleur), un talent
    modélisé passe devant un non modélisé (`modelise`) ; sinon le meilleur, « non départagé par le calcul »
    (`non_departage`). Rend le choix, sa décision, le second et l'écart apparié choix − second, et pour chaque candidat
    sa moyenne, son écart au meilleur et s'il est modélisé (`modeled` None : aucun talent n'est dit modélisé).

    Registre : I5"""
    sign = 1.0 if lower_is_better else -1.0
    order = sorted(range(len(cands)), key=lambda i: (sign * cands[i][1].mean, i))
    best = cands[order[0]][1]
    rows: list[dict[str, Any]] = []
    for key, st in cands:
        g = paired_gap(st, best, confidence)
        rows.append(
            {
                "talent": key,
                "mean": st.mean,
                "n": st.n,
                "gap": gap_dict(g),
                "significant": g.significant,
                "modeled": modeled is not None and key in modeled,
            }
        )
    if len(cands) == 1:
        return {"choice": cands[0][0], "decided_by": "seul_candidat", "runner_up": None, "gap": None, "rows": rows}
    tied = [i for i in order if not rows[i]["significant"]]
    pool = [i for i in tied if rows[i]["modeled"]]
    if len(tied) == 1:
        choice, by = tied[0], "monte_carlo"
    elif pool and len(pool) < len(tied):
        choice, by = pool[0], "modelise" if len(pool) == 1 else "non_departage"
    else:
        choice, by = tied[0], "non_departage"
    runner = next(i for i in order if i != choice)
    g = paired_gap(cands[choice][1], cands[runner][1], confidence)
    return {
        "choice": cands[choice][0],
        "decided_by": by,
        "runner_up": cands[runner][0],
        "gap": gap_dict(g),
        "rows": rows,
    }


def departage[C](
    candidates: Sequence[C], compare: Callable[[C, C], tuple[Gap, str, bool]]
) -> tuple[C, list[dict[str, Any]]]:
    """Départage final d'une recommandation (décision 219) : le premier candidat est champion ; un candidat qui le bat
    significativement (`compare(candidat, champion)` : écart, mode, candidat meilleur) prend sa place. Les comparaisons
    appariées ne sont pas transitives : les passes se répètent jusqu'à une passe sans changement (au plus une par
    candidat). Rend le champion et, pour chaque autre candidat, sa comparaison au champion final (dernière passe).

    Registre : I5"""
    unique: list[C] = []
    for c in candidates:
        if c not in unique:
            unique.append(c)
    champion = unique[0]
    rows: list[dict[str, Any]] = []
    for _ in range(len(unique)):
        rows = []
        switched = False
        for c in unique:
            if c == champion:
                continue
            gap, by, better = compare(c, champion)
            if gap.significant and better:
                champion, switched = c, True
                break
            rows.append({"candidate": c, **gap_dict(gap), "decided_by": by, "better": better})
        if not switched:
            break
    return champion, rows
