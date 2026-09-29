"""Ordre des talents pour le leveling (T05, décision 84) : faisceau sur les ordres légaux, présélection à l'analytique
avec anticipation gloutonne, décision au Monte Carlo ; score = somme des temps par monstre pondérés par l'XP de chaque
niveau (heures équivalentes).

Portage de seed/forever-mage/scripts/optimize.py (`leveling`, `rollout_value`, `score_plan`, `level_weight`) : en mode
seed (`rules="seed"`), les méthodes du seed à l'identique (rotations frost et fire, deux Monte Carlo par candidat).
En mode forever, les choix du build (rotation, armure, `ab_stacks`, `ab_dump`, `hs_stacks`) sont cherchés avec les
talents : évaluation rapide (rotations aux défauts) pour la présélection et l'anticipation, complète (toutes les
combinaisons légales) pour les finalistes, un seul Monte Carlo sur la meilleure combinaison.

Registre : I5, I6"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points

# Paramètres de méthode du seed (optimize.py), pas des chiffres de jeu : poids du temps immédiat et de l'anticipation
# dans la présélection, poids de l'anticipation dans le tri du faisceau.
NOW_WEIGHT, LOOK_WEIGHT, BEAM_LOOK_WEIGHT = 0.5, 0.5, 0.25
SECONDS_PER_HOUR = 3600.0
SEED_ROTATIONS = ("frost", "fire")


class BuildChoice(NamedTuple):
    """Choix du build hors talents : rotation et paramètres des simulateurs (None : défaut du simulateur)."""

    rotation: str
    armor: str = "auto"
    ab_stacks: int | None = None
    ab_dump: str | None = None
    hs_stacks: int | None = None

    def options(self) -> dict[str, Any]:
        """Options des simulateurs correspondant au choix (clés non nulles, armure seulement si elle est forcée)."""
        out: dict[str, Any] = {}
        if self.armor != "auto":
            out["armor"] = self.armor
        for key in ("ab_stacks", "ab_dump", "hs_stacks"):
            if getattr(self, key) is not None:
                out[key] = getattr(self, key)
        return out


class Step(NamedTuple):
    """Étape du chemin : niveau, talent pris (None si aucun point), temps par monstre arrondi comme le seed, rotation,
    choix complet du build."""

    level: int
    talent: str | None
    time_s: float
    rotation: str
    choice: BuildChoice


class LevelingPath(NamedTuple):
    hours_equiv: float
    points: dict[str, int]
    steps: tuple[Step, ...]


class PlanScore(NamedTuple):
    hours_equiv: float
    steps: tuple[tuple[int, float, str], ...]
    points: dict[str, int]


def level_weight(gd: GameData, level: int) -> float:
    """Poids d'un niveau : XP pour passer au niveau suivant / XP d'un monstre du niveau (monstres par niveau) ; 0 au
    plafond (aucune XP à gagner), comme le seed.

    Registre : I5, I6"""
    raise NotImplementedError


def build_choices(
    gd: GameData, level: int, pts: Points, *, rules: str = "forever", full: bool = False
) -> list[BuildChoice]:
    """Choix du build possibles à un niveau : rotations apprises (seed : frost, fire), et en évaluation complète les
    armures apprises, `ab_stacks` × `ab_dump` appris, `hs_stacks`.

    Registre : I1, I5"""
    raise NotImplementedError


def best_choice(
    gd: GameData,
    level: int,
    pts: Points,
    race: str = "Orc",
    over: CharacterOverrides | None = None,
    *,
    rules: str = "forever",
    full: bool = False,
    **options: Any,
) -> tuple[float, BuildChoice]:
    """(temps par monstre à l'analytique, choix) le plus court ; égalités départagées comme le seed (nom de rotation).

    Registre : I5"""
    raise NotImplementedError


def optimize_leveling(
    gd: GameData,
    race: str,
    lfrom: int,
    lto: int,
    *,
    beam: int = 3,
    depth: int = 4,
    shortlist: int = 4,
    mc_n: int = 200,
    seed: int = 12345,
    rules: str = "forever",
    start: Points | None = None,
    over: CharacterOverrides | None = None,
    talented_bonus: int = 0,
    **options: Any,
) -> LevelingPath:
    """Meilleur ordre des talents de `lfrom` à `lto` (faisceau, anticipation, Monte Carlo sur la présélection).

    Registre : I5, I6"""
    raise NotImplementedError


def score_plan(
    gd: GameData,
    plan: Sequence[tuple[int, str | None]],
    race: str = "Orc",
    over: CharacterOverrides | None = None,
    *,
    rules: str = "forever",
    talented_bonus: int = 0,
    **options: Any,
) -> PlanScore:
    """Heures équivalentes d'un plan (niveau, talent) : même métrique que `optimize_leveling`, analytique seulement ;
    ValueError si le plan est illégal à un niveau.

    Registre : I5"""
    raise NotImplementedError
