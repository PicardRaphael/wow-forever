"""Build du Mage par contexte pour la CLI (`forever build`) et le serveur MCP (`forever_build`) : talents et ordre
d'apprentissage, choix du build (rotation, armure, cumuls), raison de chaque choix, alternative la plus proche avec
écart apparié et intervalle, stabilité, sensibilité aux hypothèses incertaines, respec, angles morts, certitude et
provenance (T05, décisions 79 à 89).

Aucun calcul ici : l'optimiseur (`forever/optimize/`) cherche et décide, les simulateurs (`forever/sim/`) évaluent,
le moteur (`forever/engine/`) porte les règles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from forever.config import Deps
from forever.provenance import Provenance

CONTEXTS = ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")


class BuildReport(TypedDict):
    context: str
    level: int
    race: str
    scenario: dict[str, Any]
    talents: dict[str, int]
    talents_by_tree: dict[str, dict[str, int]]
    order: list[dict[str, Any]]
    choices: dict[str, dict[str, Any]]
    metric: dict[str, Any]
    reasons: list[dict[str, Any]]
    alternative: dict[str, Any]
    stability: dict[str, Any]
    sensitivity: list[dict[str, Any]]
    respec: dict[str, Any]
    blind_spots: list[dict[str, Any]]
    certainty: str
    certainty_sources: dict[str, str]
    verifiable_in_game: bool
    assumptions: list[str]
    provenance: Provenance


def build_report(
    deps: Deps,
    context: str,
    level: int,
    *,
    race: str = "Orc",
    current: Mapping[str, int] | None = None,
    respecs: int = 0,
    sp: float | None = None,
    crit: float | None = None,
    preset: str = "rapide",
    seed: int = 12345,
    rules: str = "forever",
    sensitivity: bool = True,
    talented_bonus: int = 0,
) -> BuildReport:
    """Rapport de build complet pour un contexte et un niveau (InvalidArgumentError, message en français).

    `current` : build actuel (conseil de respec) ; `respecs` : réinitialisations déjà faites ; `sp`, `crit` : fiche
    remplacée ; `preset` : préréglage de l'optimiseur (`build.presets`) ; `talented_bonus` : points de talent du bonus
    Legacy « Talented » (hypothèse affichée)."""
    raise NotImplementedError
