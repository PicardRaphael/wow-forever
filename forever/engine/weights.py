"""Poids des statistiques (CJ1, bloc 4, décision 276), fonctions pures : effet d'une unité de chaque statistique sur
une mesure où plus grand vaut mieux (XP par heure du leveling), par différences finies avant sur la fiche du
personnage ; normalisation sur une statistique de référence. Les pas des différences sont des réglages de méthode,
donnés par l'appelant.

Registre : I3."""

from __future__ import annotations

from collections.abc import Callable, Mapping


def stat_weights(
    metric: Callable[[Mapping[str, float]], float], base: Mapping[str, float], deltas: Mapping[str, float]
) -> dict[str, float]:
    """Gain de `metric` par unité de chaque statistique de `deltas` (différence finie avant depuis `base`).

    Registre : I3"""
    reference = metric(dict(base))
    out: dict[str, float] = {}
    for key, step in deltas.items():
        moved = {**base, key: base.get(key, 0.0) + step}
        out[key] = (metric(moved) - reference) / step
    return out


def normalize_weights(raw: Mapping[str, float], *, reference: str) -> dict[str, float]:
    """Poids relatifs à `reference` (= 1), poids négatifs ramenés à 0 ; ValueError si la référence n'a aucun effet.

    Registre : I3"""
    base = raw.get(reference)
    if base is None or base <= 0:
        raise ValueError(f"statistique de référence sans effet : {reference}")
    return {key: max(0.0, value / base) for key, value in raw.items()}
