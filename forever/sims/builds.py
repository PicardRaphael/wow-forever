"""Recherche de builds au niveau 60 par les simulateurs de la communauté (MS1, décision 301 ; revient sur la décision
299 au niveau 60 seulement) : aucun calcul de jeu ici, chaque build est mesuré par un simulateur (évaluation injectée).

Recherche locale : à chaque pas, un point est retiré parmi les moins utiles (`removals` premiers), puis remis là où il
rapporte le plus ; un build illégal sur les arbres du client n'est jamais mesuré ; arrêt dès qu'aucun échange ne gagne,
ou au plafond de pas. Tirages appariés (même graine) : le bruit d'un écart reste faible, mais il reste. D'où la
confirmation (`decide`) : un gain sous deux fois l'écart type de la différence des moyennes (erreur type de chaque
moyenne : écart type / racine du nombre de combats) est rendu « non départagé »."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

Evaluate = Callable[[Mapping[str, int]], tuple[float, float]]


def climb(
    start: Mapping[str, int],
    evaluate: Evaluate,
    legal: Callable[[Mapping[str, int]], bool],
    candidates: Sequence[str],
    *,
    max_steps: int = 30,
    removals: int = 4,
) -> dict[str, Any]:
    """Échange d'un point tant que les dégâts montent ; rend les talents trouvés, les pas et la raison de l'arrêt."""
    cache: dict[tuple[tuple[str, int], ...], float] = {}

    def dps(talents: Mapping[str, int]) -> float:
        tag = tuple(sorted((k, v) for k, v in talents.items() if v))
        if tag not in cache:
            cache[tag] = evaluate({k: v for k, v in talents.items() if v})[0]
        return cache[tag]

    keys = dict(start)
    steps: list[dict[str, Any]] = []
    stopped = "plafond d'échanges atteint"
    for _ in range(max_steps):
        base = dps(keys)
        costs = []
        for k in [k for k, v in keys.items() if v]:
            fewer = {**keys, k: keys[k] - 1}
            if legal(fewer):
                costs.append((base - dps(fewer), k))
        costs.sort()
        best: tuple[float, str, str, dict[str, int]] | None = None
        for _, rk in costs[:removals]:
            fewer = {**keys, rk: keys[rk] - 1}
            for ak in candidates:
                if ak == rk:
                    continue
                more = {**fewer, ak: fewer.get(ak, 0) + 1}
                if not legal(more):
                    continue
                gain = dps(more) - base
                if best is None or gain > best[0]:
                    best = (gain, rk, ak, more)
        if best is None or best[0] <= 0:
            stopped = "aucun échange gagnant"
            break
        steps.append({"remove": best[1], "add": best[2], "before": base, "after": base + best[0]})
        keys = best[3]
    return {"talents": keys, "steps": steps, "stopped": stopped, "evaluations": len(cache)}


def decide(start: Mapping[str, Any], final: Mapping[str, Any]) -> dict[str, Any]:
    """Verdict de la confirmation : gain du build trouvé sur le départ, seuil de bruit, « meilleur » ou « non
    départagé » (gain sous le seuil, ou nul)."""

    def se(r: Mapping[str, Any]) -> float:
        n = max(int(r.get("iterations") or 0), 1)
        return float(r.get("stdev") or 0.0) / math.sqrt(n)

    gain = float(final["dps"]) - float(start["dps"])
    threshold = 2 * math.sqrt(se(start) ** 2 + se(final) ** 2)
    verdict = "meilleur" if gain > threshold and gain > 0 else "non départagé"
    return {"gain": gain, "threshold": threshold, "verdict": verdict}
