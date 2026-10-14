"""Comparaison avec une route de Factoruide (RX1, bloc G, question RTE1).

Le joueur exporte une route de Factoruide (bouton « Share », fichier `.fgguide` : JSON `factoruide-guide`, lu en
local, jamais recopié dans le dépôt). Ses arrêts de quête sont rejoués par notre simulation (`forever/engine/route.py`,
nos règles d'XP et de temps) ; un arrêt impossible chez nous (quête inconnue, prérequis, niveau) est sauté et dit ;
les visites au maître de classe sont placées comme dans nos routes. Le résultat se compare à notre route pour la même
demande : temps, XP par heure, quêtes communes et propres à chacune."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.engine.model import GameData
from forever.engine.route import RouteResult, RouteState, RouteWorld, Stop

FORMATS = ("factoruide-guide", "brouzquest-result")
KINDS = {"accept": "accept", "objective": "objective", "turnin": "turnin"}


class FgGuide(NamedTuple):
    class_name: str
    faction: str  # horde | alliance
    from_level: int
    to_level: int
    total_time: float  # secondes, d'après Factoruide
    stops: list[tuple[str, int]]  # (sorte de Factoruide, quête) dans l'ordre


class Replay(NamedTuple):
    stops: list[Stop]
    skipped: list[dict[str, Any]]  # {"kind", "quest", "reason"}
    result: RouteResult


def read_fgguide(path: Path) -> FgGuide:
    """Route d'un fichier `.fgguide` ; InvalidArgumentError si ce n'est pas un guide de Factoruide."""
    raise NotImplementedError


def replay_guide(
    gd: GameData, world: RouteWorld, steps: Sequence[tuple[str, int]], start: RouteState, *, end_level: int, cap: int
) -> Replay:
    """Arrêts de Factoruide rejoués par notre simulation. Registre : I18"""
    raise NotImplementedError


def compare_route(deps: Any, path: Path, *, wow_dir: Path | None = None) -> dict[str, Any]:
    """Notre route et la route de Factoruide rejouée, pour la même demande, avec la provenance (`forever route
    compare`). Registre : I18"""
    raise NotImplementedError
