"""Simulation d'une feuille de route de leveling (RX1, bloc C), fonctions pures.

Une route est une suite d'arrêts (`Stop` : prendre, objectif, rendre, donjon, passage suivant d'un donjon) déroulée
sur un état (`RouteState` : niveau, XP, position, journal, quêtes faites). Chaque arrêt coûte le trajet depuis la
position courante (fonction `travel` injectée, `forever/engine/travel.py`) et son action ; l'XP vient du modèle de
T04d (`quest_xp`, `mob_kill_xp`, bonus de T04f par `XpBonusState`), le temps par monstre de `kill_seconds` (mesure du
joueur d'abord, décision 249). Faute de quêtes pour finir, la route se termine par du farm au niveau du joueur.
Contraintes dures vérifiées par `check_stop` : prérequis, chaîne, exclusives, niveau minimal, journal plein, donjon
dans sa fenêtre de placement (DJ1), passage suivant seulement s'il bat la meilleure zone (I14).

Registre : I18 (feuille de route), I17 (placement d'un donjon), I14, I6, I12, D10."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from forever.engine.model import GameData
from forever.engine.travel import Point
from forever.engine.xp import Term, XpBonusState

STOP_KINDS = ("accept", "objective", "turnin", "dungeon", "dungeon_repeat", "grind")
SEARCH_KEY = "route.search"


@dataclass(frozen=True)
class RouteQuest:
    """Quête prête pour la route : positions monde, XP de base et sa provenance, contraintes."""

    id: int
    name: str
    level: int
    min_level: int
    base_xp: float
    xp_source: str
    xp_certainty: str
    giver: Point
    turn_in: Point
    objective: Point | None  # None : rien à faire entre la prise et le rendu
    kills: float  # monstres tués pour l'objectif
    mob_level: int
    zone: int | None = None  # uiMapID du donneur
    prereq_all: tuple[int, ...] = ()
    prereq_any: tuple[int, ...] = ()
    after: tuple[int, ...] = ()  # chaîne : une de ces quêtes faite avant
    exclusive: tuple[int, ...] = ()
    dungeon: str | None = None
    certainty: str = "suppose"  # positions et objectif


@dataclass(frozen=True)
class RouteDungeon:
    """Donjon placé : fenêtre de niveaux permise (placement de DJ1), passage, quêtes."""

    key: str
    name: str
    entrance: Point
    levels: tuple[int, int]  # premier et dernier niveau permis pour le premier passage
    quests: tuple[int, ...]
    minutes: float
    kills: float
    mob_level: int
    group: int
    certainty: str


@dataclass(frozen=True)
class Stop:
    kind: str  # STOP_KINDS
    ref: int | str  # quête (identifiant) ou donjon (clé du livre)


@dataclass(frozen=True)
class RouteParams:
    """Réglages de la route (`mechanics.json`, `route.search`)."""

    log_size: int
    stop_overhead_s: float
    tries: int
    seed: int


@dataclass(frozen=True)
class RouteWorld:
    """Entrées de la simulation ; `travel(a, b, niveau)` et `kill_seconds(niveau)` en secondes ;
    `best_zone_xp_h(niveau)` : XP par heure de la meilleure zone (None : aucune zone chiffrée)."""

    quests: Mapping[int, RouteQuest]
    dungeons: Mapping[str, RouteDungeon]
    params: RouteParams
    travel: Callable[[Point, Point, int], float]
    kill_seconds: Callable[[int], float]
    best_zone_xp_h: Callable[[int], float | None]
    bonuses: XpBonusState | None = None


@dataclass(frozen=True)
class RouteState:
    level: int
    xp: float  # XP dans le niveau
    position: Point
    seconds: float = 0.0
    log: frozenset[int] = frozenset()
    progressed: frozenset[int] = frozenset()  # objectifs faits
    done: frozenset[int] = frozenset()
    dungeons_done: frozenset[str] = frozenset()
    rested: float = 0.0


@dataclass(frozen=True)
class StopResult:
    kind: str
    ref: int | str
    level: int  # niveau au début de l'arrêt
    xp: float
    seconds: float  # trajet compris
    travel_s: float
    terms: tuple[Term, ...]
    certainty: str


@dataclass(frozen=True)
class RouteResult:
    start_level: int
    end_level: int
    reached: bool
    feasible: bool
    seconds: float
    xp: float
    xp_h: float
    stops: tuple[StopResult, ...]
    warnings: tuple[str, ...]
    certainty: str


def check_stop(gd: GameData, world: RouteWorld, state: RouteState, stop: Stop) -> str | None:
    """Raison pour laquelle `stop` est impossible dans `state` (None : possible). Registre : I18, I17, I14"""
    raise NotImplementedError


def apply_stop(
    gd: GameData, world: RouteWorld, state: RouteState, stop: Stop, *, cap: int
) -> tuple[RouteState, StopResult]:
    """État après `stop` (supposé possible) et son résultat. Registre : I18, I6, I12, D10"""
    raise NotImplementedError


def simulate(
    gd: GameData,
    world: RouteWorld,
    stops: Sequence[Stop],
    start: RouteState,
    *,
    end_level: int,
    cap: int,
    finish: bool = True,
) -> RouteResult:
    """Route déroulée jusqu'à `end_level` (arrêts suivants ignorés), farm final au besoin (`finish`) ; un arrêt
    impossible rend une route `feasible=False`. Registre : I18"""
    raise NotImplementedError


def best_zone_xp_h(
    gd: GameData,
    quests: Sequence[RouteQuest],
    level: int,
    *,
    kill_seconds: float,
    overhead_s: float,
) -> float | None:
    """XP par heure de la meilleure zone à `level` : quêtes accessibles et non grises de chaque zone, XP des quêtes et
    de leurs monstres sur le temps des monstres et des arrêts (même forme que les objectifs de T04d). Registre : I14"""
    raise NotImplementedError
