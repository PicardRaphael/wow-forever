"""Recherche d'une feuille de route (RX1, bloc C) : portage cité d'un sous-ensemble de Factoruide.

Code d'origine : MIT, brouznouf/factoruide@f7da6da, `crates/fg-route/src/plan/worth.rs` (valeur d'une quête et de sa
chaîne), `plan/regions.rs` et `plan/construct.rs` (construction gloutonne, région courante d'abord), `plan/moves.rs`
et `plan/search.rs` (amélioration locale : déplacer un arrêt, un bloc, retirer une quête, en insérer une ; budget
compté en essais, graine fixe). Les règles d'XP et de temps sont celles du moteur (`forever/engine/route.py`), jamais
celles de Factoruide.

Registre : I18."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from forever.engine.model import GameData
from forever.engine.route import RouteResult, RouteState, RouteWorld, Stop


@dataclass(frozen=True)
class PlanResult:
    stops: tuple[Stop, ...]
    result: RouteResult
    construct_seconds: float  # coût de la construction seule
    tries: int


def quest_worth(gd: GameData, world: RouteWorld, quest_id: int, level: int) -> float:
    """XP de la quête et des quêtes de sa chaîne qui la suivent, à `level`. Registre : I18"""
    raise NotImplementedError


def construct(gd: GameData, world: RouteWorld, start: RouteState, *, end_level: int, cap: int) -> list[Stop]:
    """Route gloutonne : donjon dû d'abord (ses quêtes prises avant), puis l'arrêt possible au meilleur rapport valeur
    sur temps (trajet compris). Registre : I18, I17"""
    raise NotImplementedError


def improve(
    gd: GameData,
    world: RouteWorld,
    stops: Sequence[Stop],
    start: RouteState,
    *,
    end_level: int,
    cap: int,
    tries: int,
    seed: int,
) -> list[Stop]:
    """Amélioration locale à graine fixe : un mouvement gardé seulement s'il rend une route possible et plus courte.
    Registre : I18"""
    raise NotImplementedError


def plan(
    gd: GameData,
    world: RouteWorld,
    start: RouteState,
    *,
    end_level: int,
    cap: int,
    tries: int | None = None,
    seed: int | None = None,
) -> PlanResult:
    """Construction puis amélioration (réglages de `world.params` par défaut). Registre : I18"""
    raise NotImplementedError
