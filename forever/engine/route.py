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

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from forever.engine.dungeon import SECONDS_PER_HOUR, SECONDS_PER_MINUTE
from forever.engine.model import GameData
from forever.engine.travel import CERTAINTY as TRAVEL_CERTAINTY
from forever.engine.travel import Point
from forever.engine.xp import (
    Party,
    QuestXpInput,
    Term,
    XpBonusState,
    XpResult,
    gray_level,
    mob_kill_xp,
    quest_xp,
)

STOP_KINDS = ("accept", "objective", "turnin", "dungeon", "dungeon_repeat", "train", "prof", "grind")
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
    class_quest: bool = False  # CJ1 : quête réservée à la classe (permise hors des zones de départ)


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
    zone_stay: float  # poids d'un arrêt hors de la zone courante dans la construction
    min_efficiency: float  # part du farm qu'une quête doit battre pour être prise
    train_time_s: float = 0.0  # visite au maître de classe (bloc F)
    train_max_delay: int = 0  # niveaux de retard permis pour l'entraînement


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
    required: frozenset[int] = frozenset()  # quêtes imposées par le joueur (--include)
    trainers: tuple[Point, ...] = ()  # maîtres de classe du camp (bloc F)
    train_levels: tuple[int, ...] = ()  # niveaux où la classe apprend des sorts, dans la route
    dropped: Mapping[int, str] = field(default_factory=dict)  # CJ1 : quêtes écartées du livre et pourquoi
    prof_visits: Mapping[str, tuple[int, tuple[Point, ...]]] = field(default_factory=dict)  # bloc H
    # CJ1 : zone de départ d'abord ; sous `early_level`, une quête hors de `early_zones` (ni de classe ni de donjon)
    # n'est pas prise ; None : aucune contrainte (rejeu d'un guide, race inconnue)
    early_zones: frozenset[int] | None = None
    early_level: int = 0
    refuse_red: bool = True  # CJ1 : notre route ne prend pas de quête rouge ; le rejeu d'un guide la permet


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
    trained: frozenset[int] = frozenset()  # niveaux d'entraînement faits
    prof_done: frozenset[str] = frozenset()  # visites aux maîtres de métier faites


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


_RANK = {"certain": 2, "probable": 1, "suppose": 0}
GRIND_REF = "farm"  # référence de l'arrêt de farm final


def weakest(*values: str) -> str:
    """Certitude la plus faible (`suppose` < `probable` < `certain`)."""
    return min(values, key=lambda c: _RANK.get(c, 0)) if values else "suppose"


def _ready(q: RouteQuest, state: RouteState) -> bool:
    """Objectif fait (ou rien à faire) : la quête peut être rendue."""
    if q.dungeon is not None or q.objective is not None:
        return q.id in state.progressed
    return True


def dungeon_kill_xp(gd: GameData, world: RouteWorld, d: RouteDungeon, level: int) -> XpResult:
    """XP d'un monstre du donjon : élite, bonus de donjon, part du groupe, bonus d'XP. Registre : I6, I10, I11, I13"""
    party = Party(tuple([level] * d.group))
    return mob_kill_xp(gd, level, d.mob_level, elite=True, dungeon=True, party=party, bonuses=world.bonuses)


def repeat_xp_h(gd: GameData, world: RouteWorld, d: RouteDungeon, level: int) -> float:
    """XP par heure d'un passage suivant (monstres seuls, sur la durée du passage). Registre : I14, I16"""
    seconds = d.minutes * SECONDS_PER_MINUTE
    return d.kills * dungeon_kill_xp(gd, world, d, level).xp / seconds * SECONDS_PER_HOUR if seconds > 0 else 0.0


def _check_accept(gd: GameData, world: RouteWorld, state: RouteState, quest_id: int) -> str | None:
    q = world.quests.get(quest_id)
    if q is None:
        return "quête hors de la route"
    if quest_id in state.log or quest_id in state.done:
        return "quête déjà prise"
    if q.min_level > state.level:
        return f"niveau minimal {q.min_level}"
    if world.refuse_red and q.dungeon is None and q.level >= state.level + gd.leveling.quest_band.red_min_diff:
        return "quête rouge, trop haute pour ce niveau (CJ1)"
    if (
        world.early_zones is not None
        and state.level < world.early_level
        and q.dungeon is None
        and not q.class_quest
        and q.zone not in world.early_zones
    ):
        return f"hors de la zone de départ avant le niveau {world.early_level} (CJ1)"
    if not set(q.prereq_all) <= state.done:
        return "prérequis non rendus"
    if q.prereq_any and not set(q.prereq_any) & state.done:
        return "aucun des prérequis rendu"
    if q.after and not set(q.after) & state.done:
        return "étape précédente de la chaîne non rendue"
    if set(q.exclusive) & (state.done | state.log):
        return "quête exclusive déjà prise"
    if len(state.log) >= world.params.log_size:
        return "journal de quêtes plein"
    return None


def check_stop(gd: GameData, world: RouteWorld, state: RouteState, stop: Stop) -> str | None:
    """Raison pour laquelle `stop` est impossible dans `state` (None : possible). Registre : I18, I17, I14"""
    if stop.kind == "accept" and isinstance(stop.ref, int):
        return _check_accept(gd, world, state, stop.ref)
    if stop.kind in ("objective", "turnin") and isinstance(stop.ref, int):
        q = world.quests.get(stop.ref)
        if q is None or stop.ref not in state.log:
            return "quête absente du journal"
        if stop.kind == "objective":
            if q.objective is None or q.dungeon is not None:
                return "aucun objectif hors donjon"
            return "objectif déjà fait" if stop.ref in state.progressed else None
        return None if _ready(q, state) else "objectif non fait"
    if stop.kind == "train" and isinstance(stop.ref, int):
        if not world.trainers or stop.ref not in world.train_levels:
            return "aucun entraînement à ce niveau"
        if stop.ref > state.level:
            return f"niveau {stop.ref} pas encore atteint"
        return "entraînement déjà fait" if stop.ref in state.trained else None
    if stop.kind == "prof" and isinstance(stop.ref, str):
        visit = world.prof_visits.get(stop.ref)
        if visit is None:
            return "aucun rang de métier à apprendre"
        if visit[0] > state.level:
            return f"niveau {visit[0]} pas encore atteint"
        return "rang déjà appris" if stop.ref in state.prof_done else None
    if stop.kind in ("dungeon", "dungeon_repeat") and isinstance(stop.ref, str):
        d = world.dungeons.get(stop.ref)
        if d is None:
            return "donjon hors de la route"
        if stop.kind == "dungeon":
            if stop.ref in state.dungeons_done:
                return "premier passage déjà fait"
            low, high = d.levels
            return None if low <= state.level <= high else f"hors de la fenêtre de placement ({low}-{high})"
        if stop.ref not in state.dungeons_done:
            return "passage suivant avant le premier"
        zone = world.best_zone_xp_h(state.level)
        if zone is not None and repeat_xp_h(gd, world, d, state.level) <= zone:
            return "passage suivant moins bon que la meilleure zone"
        return None
    return f"arrêt inconnu : {stop.kind}"


def gain(gd: GameData, level: int, xp: float, gained: float, cap: int) -> tuple[int, float]:
    """Niveau et XP dans le niveau après un gain (courbe d'XP de la version, plafond `cap`). Registre : I18"""
    xp += gained
    while level < cap and xp >= gd.xp_to_next[min(level, len(gd.xp_to_next)) - 1]:
        xp -= gd.xp_to_next[min(level, len(gd.xp_to_next)) - 1]
        level += 1
    return level, xp


def nearest_trainer(world: RouteWorld, position: Point, level: int) -> tuple[Point, float]:
    """Maître de classe le plus proche en temps et le trajet jusqu'à lui. Registre : I18"""
    best = min(((t, world.travel(position, t, level)) for t in world.trainers), key=lambda x: x[1])
    return best


def nearest_place(world: RouteWorld, places: Sequence[Point], position: Point, level: int) -> tuple[Point, float]:
    """Lieu le plus proche en temps parmi `places`, et le trajet jusqu'à lui. Registre : I18"""
    return min(((p, world.travel(position, p, level)) for p in places), key=lambda x: x[1])


def missed_visit(world: RouteWorld, before: RouteState, after: RouteState) -> str | None:
    """Visite due (maître de classe ou de métier) dépassée de plus de `train_max_delay` niveaux sans être faite."""
    level = missed_training(world, before, after)
    if level is not None:
        return f"entraînement du niveau {level} manqué"
    for name, (at, _) in sorted(world.prof_visits.items()):
        if name not in after.prof_done and at <= before.level and after.level > at + world.params.train_max_delay:
            return f"visite au maître de {name} manquée"
    return None


def missed_training(world: RouteWorld, before: RouteState, after: RouteState) -> int | None:
    """Niveau d'entraînement atteint avant l'arrêt et dépassé de plus de `train_max_delay` niveaux sans visite au
    maître (None sinon). Un arrêt qui saute d'un coup un niveau d'entraînement n'est pas fautif : la visite devient
    due et c'est l'arrêt suivant, s'il n'est pas la visite, qui la manque. Registre : I18"""
    if not world.trainers:
        return None
    for level in world.train_levels:
        if level not in after.trained and level <= before.level and after.level > level + world.params.train_max_delay:
            return level
    return None


def _target(world: RouteWorld, state: RouteState, stop: Stop) -> tuple[Point, str]:
    if stop.kind in ("dungeon", "dungeon_repeat"):
        d = world.dungeons[str(stop.ref)]
        return d.entrance, d.certainty
    if stop.kind == "train":
        return nearest_trainer(world, state.position, state.level)[0], "suppose"
    if stop.kind == "prof":
        return nearest_place(world, world.prof_visits[str(stop.ref)][1], state.position, state.level)[0], "suppose"
    q = world.quests[int(stop.ref)]
    place = {"accept": q.giver, "turnin": q.turn_in, "objective": q.objective or q.giver}[stop.kind]
    return place, q.certainty


def apply_stop(
    gd: GameData, world: RouteWorld, state: RouteState, stop: Stop, *, cap: int
) -> tuple[RouteState, StopResult]:
    """État après `stop` (supposé possible) et son résultat. Registre : I18, I6, I12, D10"""
    target, place_certainty = _target(world, state, stop)
    travel_s = 0.0 if target == state.position else world.travel(state.position, target, state.level)
    level = state.level
    terms: tuple[Term, ...] = ()
    xp = 0.0
    log, progressed, done, dungeons_done = state.log, state.progressed, state.done, state.dungeons_done
    trained, prof_done = state.trained, state.prof_done
    if stop.kind == "prof":
        action = world.params.train_time_s
        prof_done = prof_done | {str(stop.ref)}
    elif stop.kind == "train":
        action = world.params.train_time_s
        trained = trained | {lv for lv in world.train_levels if lv <= level}
    elif stop.kind == "accept":
        action = world.params.stop_overhead_s
        log = log | {int(stop.ref)}
    elif stop.kind == "objective":
        q = world.quests[int(stop.ref)]
        per = mob_kill_xp(gd, level, q.mob_level, bonuses=world.bonuses)
        xp, terms = q.kills * per.xp, per.terms
        action = q.kills * world.kill_seconds(level) + world.params.stop_overhead_s
        progressed = progressed | {q.id}
    elif stop.kind == "turnin":
        q = world.quests[int(stop.ref)]
        res = quest_xp(gd, level, QuestXpInput(q.level, q.base_xp, q.xp_source, q.xp_certainty), bonuses=world.bonuses)
        xp, terms = res.xp, res.terms
        action = world.params.stop_overhead_s
        log, done = log - {q.id}, done | {q.id}
    else:  # dungeon, dungeon_repeat
        d = world.dungeons[str(stop.ref)]
        per = dungeon_kill_xp(gd, world, d, level)
        xp, terms = d.kills * per.xp, per.terms
        action = d.minutes * SECONDS_PER_MINUTE
        if stop.kind == "dungeon":
            dungeons_done = dungeons_done | {d.key}
            progressed = progressed | {i for i in log if world.quests[i].dungeon == d.key}
    new_level, new_xp = gain(gd, level, state.xp, xp, cap)
    certainty = weakest(place_certainty, *(t.certainty for t in terms), *([TRAVEL_CERTAINTY] if travel_s else []))
    seconds = travel_s + action
    result = StopResult(stop.kind, stop.ref, level, xp, seconds, travel_s, terms, certainty)
    after = RouteState(
        level=new_level,
        xp=new_xp,
        position=target,
        seconds=state.seconds + seconds,
        log=log,
        progressed=progressed,
        done=done,
        dungeons_done=dungeons_done,
        rested=state.rested,
        trained=trained,
        prof_done=prof_done,
    )
    return after, result


def _missed(world: RouteWorld, start: RouteState, state: RouteState) -> str | None:
    for d in world.dungeons.values():
        if d.key not in state.dungeons_done and start.level <= d.levels[1] < state.level:
            return f"donjon {d.name} manqué (fenêtre {d.levels[0]}-{d.levels[1]} dépassée)"
    return None


def _grind(
    gd: GameData, world: RouteWorld, start: RouteState, state: RouteState, *, end_level: int, cap: int
) -> tuple[RouteState, StopResult, str | None]:
    """Farm au niveau du joueur jusqu'à `end_level` (monstres de même niveau, temps par monstre du niveau) ;
    un monstre sans XP rend le farm impossible (durée infinie). Registre : I18, I6"""
    level, xp, seconds, total = state.level, state.xp, 0.0, 0.0
    for name, (at, places) in sorted(world.prof_visits.items()):  # visites de métier non faites
        if name not in state.prof_done and at < end_level:
            seconds += 2 * nearest_place(world, places, state.position, level)[1] + world.params.train_time_s
    if world.trainers:  # entraînements dus et non faits au début du farm
        due = [lv for lv in world.train_levels if lv <= level and lv not in state.trained]
        if due:
            seconds += 2 * nearest_trainer(world, state.position, level)[1] + world.params.train_time_s
    terms: tuple[Term, ...] = ()
    missed = None
    while level < min(end_level, cap):
        need = gd.xp_to_next[min(level, len(gd.xp_to_next)) - 1] - xp
        per = mob_kill_xp(gd, level, level, bonuses=world.bonuses)
        terms = terms or per.terms
        seconds += need / per.xp * world.kill_seconds(level) if per.xp > 0 else math.inf
        total += need
        level, xp = level + 1, 0.0
        missed = missed or _missed(world, start, replace(state, level=level))
        if world.trainers and level in world.train_levels and level not in state.trained:
            # visite au maître pendant le farm : aller et retour depuis la position, temps de la visite
            seconds += 2 * nearest_trainer(world, state.position, level)[1] + world.params.train_time_s
    certainty = weakest(*(t.certainty for t in terms))
    result = StopResult("grind", GRIND_REF, state.level, total, seconds, 0.0, terms, certainty)
    return replace(state, level=level, xp=xp, seconds=state.seconds + seconds), result, missed


def grind_to(
    gd: GameData, world: RouteWorld, start: RouteState, state: RouteState, *, level: int, cap: int
) -> tuple[RouteState, StopResult]:
    """Farm au niveau du joueur jusqu'à `level` au milieu d'une route (étape de farm d'un guide rejoué, RX1c) : mêmes
    règles que le farm final ; les entraînements et les visites de métier faits pendant le farm sont marqués faits.
    Registre : I18, I6"""
    after, result, _ = _grind(gd, world, start, state, end_level=level, cap=cap)
    trained = after.trained | {lv for lv in world.train_levels if lv <= after.level}
    prof_done = after.prof_done | {name for name, (at, _) in world.prof_visits.items() if at < after.level}
    return replace(after, trained=trained, prof_done=prof_done), replace(result, ref=level)


def pending_required(world: RouteWorld, state: RouteState) -> frozenset[int]:
    """Quêtes imposées de la route pas encore rendues (bloc 4d) : la route continue au-delà du niveau final tant
    qu'il en reste. Registre : I18"""
    return frozenset(q for q in world.required if q in world.quests and q not in state.done)


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
    state = start
    results: list[StopResult] = []
    warnings: list[str] = []
    feasible = True
    for stop in stops:
        if state.level >= end_level and not pending_required(world, state):
            break
        reason = check_stop(gd, world, state, stop)
        if reason is None:
            before = state
            state, result = apply_stop(gd, world, state, stop, cap=cap)
            if not math.isfinite(result.seconds):
                reason = "trajet impossible"
            else:
                results.append(result)
                reason = _missed(world, start, state)
                if reason is None:
                    reason = missed_visit(world, before, state)
        if reason is not None:
            feasible = False
            warnings.append(f"{stop.kind} {stop.ref} : {reason}")
            break
    if feasible and finish and state.level < end_level:
        state, result, missed = _grind(gd, world, start, state, end_level=end_level, cap=cap)
        results.append(result)
        if missed:  # farm final : le donjon n'est pas fait, c'est dit (l'optimiseur refuse une telle route)
            warnings.append(f"farm : {missed}")
    seconds = sum(r.seconds for r in results)
    xp = sum(r.xp for r in results)
    return RouteResult(
        start_level=start.level,
        end_level=state.level,
        reached=state.level >= end_level,
        feasible=feasible,
        seconds=seconds,
        xp=xp,
        xp_h=xp / (seconds / SECONDS_PER_HOUR) if seconds > 0 else 0.0,
        stops=tuple(results),
        warnings=tuple(warnings),
        certainty=weakest(*(r.certainty for r in results)),
    )


def best_zone_xp_h(
    gd: GameData,
    quests: Sequence[RouteQuest],
    level: int,
    *,
    kill_seconds: float,
    overhead_s: float,
    bonuses: XpBonusState | None = None,
) -> float | None:
    """XP par heure de la meilleure zone à `level` : quêtes accessibles et non grises de chaque zone, XP des quêtes et
    de leurs monstres sur le temps des monstres et des arrêts (même forme que les objectifs de T04d). Registre : I14"""
    gray = gray_level(gd, level)
    red = gd.leveling.quest_band.red_min_diff
    zones: dict[int | None, tuple[float, float]] = {}
    for q in quests:
        if q.dungeon is not None or q.min_level > level or q.level <= gray or q.level >= level + red:
            continue
        inp = QuestXpInput(q.level, q.base_xp, q.xp_source, q.xp_certainty)
        xp = quest_xp(gd, level, inp, bonuses=bonuses).xp
        xp += q.kills * mob_kill_xp(gd, level, q.mob_level, bonuses=bonuses).xp
        seconds = q.kills * kill_seconds + overhead_s
        total_xp, total_s = zones.get(q.zone, (0.0, 0.0))
        zones[q.zone] = (total_xp + xp, total_s + seconds)
    rates = [x / s * SECONDS_PER_HOUR for x, s in zones.values() if s > 0]
    return max(rates) if rates else None
