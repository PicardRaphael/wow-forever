"""Conseil de respec en leveling (T05, bloc H ; décision 87) : portage du conseil du seed (`advise_leveling`, parité en
mode seed) et conseil forever (gain d'heures par niveau de respec, niveau conseillé).

Méthode forever : deux chemins de l'optimiseur de leveling, à l'analytique (préréglage donné, sans Monte Carlo) :
le chemin gardé (build actuel, points suivants optimisés) et le chemin libre (meilleur ordre depuis le niveau de
départ des talents). Respec au niveau L : gain = heures du chemin gardé − heures du chemin libre, de L au niveau visé ;
bilan = gain × or par heure au niveau L − coût − trajet ; niveau conseillé = bilan le plus grand, s'il est positif.

Registre : I5"""

from __future__ import annotations

from typing import Any, NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points, Preset
from forever.optimize.leveling import LevelingPath


class RespecAdvice(NamedTuple):
    """Conseil : verdict (`réinitialiser` ou `garder`), niveau conseillé (None : garder), heures gagnées, coût, bilan
    et or par heure au niveau conseillé (ou actuel), certitude du coût, (niveau, heures gagnées, bilan) par niveau,
    chemins gardé et libre."""

    verdict: str
    level: int | None
    gain_hours: float
    cost_gold: float
    balance_gold: float
    gold_per_hour: float
    cost_certainty: str
    by_level: tuple[tuple[int, float, float], ...]
    keep: LevelingPath
    free: LevelingPath


def advise_leveling(
    gd: GameData,
    level: int,
    current: Points,
    target: Points,
    hours: float,
    race: str = "Orc",
    n_previous: int = 0,
    gph: float | None = None,
    *,
    rules: str = "forever",
    **options: Any,
) -> dict[str, Any]:
    """Conseil du seed (`respec.advise_leveling`) : XP par heure du build actuel et du build cible (meilleure rotation
    à l'analytique), heures gagnées sur `hours` heures, bilan en or, verdict ; mêmes arrondis que le seed.

    Registre : I5"""
    raise NotImplementedError


def advise_respec(
    gd: GameData,
    level: int,
    current: Points,
    target_level: int,
    race: str = "Orc",
    *,
    preset: Preset,
    n_previous: int = 0,
    over: CharacterOverrides | None = None,
    talented_bonus: int = 0,
    **options: Any,
) -> RespecAdvice:
    """Conseil forever : faut-il réinitialiser le build `current` (niveau `level`) d'ici au niveau `target_level`, et
    à quel niveau ; ValueError si le build actuel est illégal.

    Registre : I5"""
    raise NotImplementedError
