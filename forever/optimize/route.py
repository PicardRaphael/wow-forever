"""Recherche d'une feuille de route (RX1, bloc C) : portage cité d'un sous-ensemble de Factoruide.

Code d'origine : MIT, brouznouf/factoruide@f7da6da, `crates/fg-route/src/plan/worth.rs` (valeur d'une quête et de sa
chaîne), `plan/regions.rs` et `plan/construct.rs` (construction gloutonne, région courante d'abord), `plan/moves.rs`
et `plan/search.rs` (amélioration locale : déplacer un arrêt, un bloc, retirer une quête, en insérer une ; budget
compté en essais, graine fixe). Les règles d'XP et de temps sont celles du moteur (`forever/engine/route.py`), jamais
celles de Factoruide.

Registre : I18."""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, replace

from forever.engine.model import GameData
from forever.engine.route import (
    RouteResult,
    RouteState,
    RouteWorld,
    Stop,
    apply_stop,
    check_stop,
    missed_visit,
    simulate,
)
from forever.engine.xp import QuestXpInput, gray_level, mob_kill_xp, quest_xp

CHAIN_DEPTH = 8  # étapes de chaîne comptées dans la valeur d'une quête (borne de parcours, pas une valeur du jeu)
BLOCK_MAX = 5  # arrêts déplacés d'un coup par le mouvement « bloc »
MISSED = "manqué"  # mot des avertissements de donjon manqué (forever/engine/route.py)
TURNIN_WEIGHT = 0.7  # poids de nearest_stop (Factoruide, construct.rs) : rendre d'abord, prendre en dernier
ACCEPT_WEIGHT = 1.3
REPEAT_WEIGHT = 0.8
DUNGEON_WEIGHT = 0.5  # premier passage d'un donjon placé (forcé chez Factoruide)
TRAIN_WEIGHT = 0.7  # visite au maître de classe : pesée comme un rendu (réglage de forever)
REQUIRED_WEIGHT = 0.1  # quête imposée par le joueur : prise en priorité (réglage de forever, pas de Factoruide)
DUNGEON_QUEST_WEIGHT = 0.25  # quête d'un donjon proche en niveau (détour accepté)
MOVES = 5  # déplacer un arrêt, un bloc, échanger deux arrêts, retirer une quête, en insérer une


@dataclass(frozen=True)
class PlanResult:
    stops: tuple[Stop, ...]
    result: RouteResult
    construct_seconds: float  # coût de la construction seule
    tries: int
    warnings: tuple[str, ...] = ()


def _quest_value(gd: GameData, world: RouteWorld, quest_id: int, level: int) -> float:
    """XP d'une quête à `level` : rendu et monstres de son objectif (portage de `quest_value`, worth.rs)."""
    q = world.quests[quest_id]
    inp = QuestXpInput(q.level, q.base_xp, q.xp_source, q.xp_certainty)
    kills = q.kills * mob_kill_xp(gd, level, q.mob_level, bonuses=world.bonuses).xp if q.kills else 0.0
    return quest_xp(gd, level, inp, bonuses=world.bonuses).xp + kills


def _followers(world: RouteWorld) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for q in world.quests.values():
        for before in sorted({*q.prereq_all, *q.prereq_any, *q.after}):
            out.setdefault(before, []).append(q.id)
    return out


def quest_worth(gd: GameData, world: RouteWorld, quest_id: int, level: int) -> float:
    """XP de la quête et des quêtes de sa chaîne qui la suivent, à `level` (portage de `quest_worth`, worth.rs : la
    quête vaut aussi ce qu'elle ouvre). Registre : I18"""
    followers = _followers(world)
    total, seen, frontier = 0.0, {quest_id}, [quest_id]
    for _ in range(CHAIN_DEPTH):
        if not frontier:
            break
        total += sum(_quest_value(gd, world, i, level) for i in frontier)
        frontier = sorted({n for i in frontier for n in followers.get(i, []) if n not in seen})
        seen.update(frontier)
    return total


def _quest_cost(world: RouteWorld, quest_id: int, level: int) -> float:
    """Secondes d'une quête seule : donneur, objectif, rendu, monstres et arrêts (portage de `quest_cost`)."""
    q = world.quests[quest_id]
    path = [q.giver, *([q.objective] if q.objective is not None else []), q.turn_in]
    travel = sum(world.travel(a, b, level) for a, b in itertools.pairwise(path) if a != b)
    stops = 2 + (1 if q.objective is not None else 0)
    return travel + q.kills * world.kill_seconds(level) + world.params.stop_overhead_s * stops


def _grind_rate(gd: GameData, world: RouteWorld, level: int) -> float:
    """XP par seconde du farm au niveau du joueur."""
    seconds = world.kill_seconds(level)
    return mob_kill_xp(gd, level, level, bonuses=world.bonuses).xp / seconds if seconds > 0 else 0.0


def _opens_dungeon(world: RouteWorld, quest_id: int, level: int) -> bool:
    """La quête ouvre (par sa chaîne) une quête d'un donjon placé encore à portée."""
    followers = _followers(world)
    seen, frontier = {quest_id}, [quest_id]
    for _ in range(CHAIN_DEPTH):
        frontier = sorted({n for i in frontier for n in followers.get(i, []) if n not in seen})
        if not frontier:
            return False
        seen.update(frontier)
        for n in frontier:
            d = world.dungeons.get(world.quests[n].dungeon or "")
            if d is not None and level <= d.levels[1]:
                return True
    return False


def _worth_it(gd: GameData, world: RouteWorld, state: RouteState, quest_id: int, trip: float) -> bool:
    """La quête vaut le détour : quête de donjon tant que le donjon est à portée, ou quête qui ouvre une quête de donjon
    (CJ1 : toutes les quêtes d'un donjon, aller-retour compris), sinon XP par seconde (chaîne comprise, trajet depuis
    la position compris) au moins `min_efficiency` fois le farm (portage de `worth_it`)."""
    q = world.quests[quest_id]
    if quest_id in world.required:
        return True
    if q.dungeon is not None:
        d = world.dungeons.get(q.dungeon)
        return d is not None and state.level <= d.levels[1]
    if _opens_dungeon(world, quest_id, state.level):
        return True
    cost = max(trip + _quest_cost(world, quest_id, state.level), 1.0)
    efficiency = quest_worth(gd, world, quest_id, state.level) / cost
    return efficiency >= world.params.min_efficiency * _grind_rate(gd, world, state.level)


def _dungeon_ready(gd: GameData, world: RouteWorld, state: RouteState) -> list[Stop]:
    """Premier passage possible d'un donjon dont aucune quête n'est plus à prendre (ses quêtes prises avant)."""
    out = []
    for key, d in sorted(world.dungeons.items()):
        stop = Stop("dungeon", key)
        if check_stop(gd, world, state, stop) is not None:
            continue
        pending = [q for q in d.quests if q in world.quests and check_stop(gd, world, state, Stop("accept", q)) is None]
        if not pending:
            out.append(stop)
    return out


def _candidates(gd: GameData, world: RouteWorld, state: RouteState) -> list[tuple[Stop, float]]:
    """(arrêt possible, poids de `nearest_stop`, construct.rs) : rendus 0,7, objectifs 1, prises 1,3 (quête de
    donjon : × 0,25), premier passage d'un donjon placé 0,5, passages suivants 0,8. Ordre stable (déterminisme)."""
    gray = gray_level(gd, state.level)
    out: list[tuple[Stop, float]] = []
    for quest_id in sorted(state.log):
        out += [(Stop("turnin", quest_id), TURNIN_WEIGHT), (Stop("objective", quest_id), 1.0)]
    for q in sorted(world.quests.values(), key=lambda q: q.id):
        if q.level > gray or q.dungeon is not None:
            weight = ACCEPT_WEIGHT * (DUNGEON_QUEST_WEIGHT if q.dungeon else 1.0)
            out.append((Stop("accept", q.id), weight * (REQUIRED_WEIGHT if q.id in world.required else 1.0)))
    out += [(Stop("dungeon_repeat", k), REPEAT_WEIGHT) for k in sorted(state.dungeons_done)]
    due = [lv for lv in world.train_levels if lv <= state.level and lv not in state.trained]
    if world.trainers and due:
        out.append((Stop("train", due[-1]), TRAIN_WEIGHT))
    out += [(Stop("prof", name), TRAIN_WEIGHT) for name in sorted(world.prof_visits)]
    out = [(s, w) for s, w in out if check_stop(gd, world, state, s) is None]
    return out + [(s, DUNGEON_WEIGHT) for s in _dungeon_ready(gd, world, state)]


def _misses(world: RouteWorld, start: RouteState, after: RouteState, before: RouteState | None = None) -> bool:
    """L'arrêt fait dépasser la fenêtre d'un donjon placé sans son premier passage, ou le retard permis d'un
    entraînement."""
    if before is not None and missed_visit(world, before, after) is not None:
        return True
    return any(
        k not in after.dungeons_done and start.level <= d.levels[1] < after.level for k, d in world.dungeons.items()
    )


def _zone(world: RouteWorld, stop: Stop) -> int | None:
    if stop.kind in ("dungeon", "dungeon_repeat", "train", "prof"):
        return None
    return world.quests[int(stop.ref)].zone


def construct(gd: GameData, world: RouteWorld, start: RouteState, *, end_level: int, cap: int) -> list[Stop]:
    """Route gloutonne (portage de `nearest_stop`, construct.rs) : l'arrêt le plus proche en temps, pondéré par sa
    sorte et par `zone_stay` hors de la zone courante (finir une zone avant d'en partir) ; une quête n'est prise que si
    elle vaut le détour, un passage suivant que s'il bat le farm ; jamais un arrêt qui ferait manquer la fenêtre d'un
    donjon placé (ses quêtes prises avant son passage). CJ1 (règle de l'utilisateur) : pas de farm quand des quêtes
    restent ; une prise moins rentable que le farm reste choisie s'il n'y a rien de mieux. Registre : I18, I17"""
    state = start
    zone: int | None = None
    stops: list[Stop] = []
    guard = 4 * len(world.quests) + 4 * len(world.dungeons) + 4
    for _ in range(guard):
        if state.level >= end_level:
            break
        best: tuple[float, Stop, RouteState] | None = None
        fallback: tuple[float, Stop, RouteState] | None = None  # prise moins rentable que le farm
        for stop, weight in _candidates(gd, world, state):
            after, result = apply_stop(gd, world, state, stop, cap=cap)
            if not math.isfinite(result.seconds):
                continue
            if _misses(world, start, after, state):
                continue
            if stop.kind == "dungeon_repeat" and (
                result.seconds <= 0 or result.xp / result.seconds <= _grind_rate(gd, world, state.level)
            ):
                continue
            here = _zone(world, stop)
            stay = 1.0 if zone is None or here == zone else world.params.zone_stay
            score = (result.travel_s + world.params.stop_overhead_s) * weight * stay
            if stop.kind == "accept" and not _worth_it(gd, world, state, int(stop.ref), result.travel_s):
                if fallback is None or score < fallback[0]:
                    fallback = (score, stop, after)
                continue
            if best is None or score < best[0]:
                best = (score, stop, after)
        best = best or fallback
        if best is None:
            break
        stops.append(best[1])
        state = best[2]
        zone = _zone(world, best[1]) or zone
    return stops


def _cost(gd: GameData, world: RouteWorld, stops: Sequence[Stop], start: RouteState, end_level: int, cap: int) -> float:
    result = simulate(gd, world, stops, start, end_level=end_level, cap=cap)
    return result.seconds if _acceptable(result) else math.inf


def _acceptable(result: RouteResult) -> bool:
    """Route possible et sans donjon manqué, même par le farm final (contrainte dure de l'optimiseur, I17)."""
    return result.feasible and not any(MISSED in w for w in result.warnings)


def _quest_stops(world: RouteWorld, quest_id: int) -> list[str]:
    q = world.quests[quest_id]
    kinds = ["accept"]
    if q.objective is not None and q.dungeon is None:
        kinds.append("objective")
    return [*kinds, "turnin"]


def _mutate(world: RouteWorld, stops: list[Stop], rng: random.Random) -> list[Stop] | None:
    move = rng.randrange(MOVES)
    n = len(stops)
    out = list(stops)
    if move == 0 and n >= 2:
        s = out.pop(rng.randrange(n))
        out.insert(rng.randrange(n), s)
        return out
    if move == 1 and n >= 3:
        i = rng.randrange(n - 1)
        k = rng.randint(2, min(BLOCK_MAX, n - i))
        block = out[i : i + k]
        del out[i : i + k]
        j = rng.randrange(len(out) + 1)
        return out[:j] + block + out[j:]
    if move == 2 and n >= 2:
        i, j = rng.randrange(n), rng.randrange(n)
        out[i], out[j] = out[j], out[i]
        return out
    taken = sorted({int(s.ref) for s in stops if s.kind == "accept"})
    removable = [q for q in taken if q not in world.required]  # une quête imposée n'est jamais retirée
    if move == 3 and removable:
        quest_id = rng.choice(removable)
        return [s for s in out if not (s.kind in ("accept", "objective", "turnin") and s.ref == quest_id)]
    if move == 4:
        unused = sorted(q for q in world.quests if q not in taken)
        if not unused:
            return None
        quest_id = rng.choice(unused)
        kinds = _quest_stops(world, quest_id)
        positions = sorted(rng.randrange(len(out) + 1) for _ in kinds)
        for offset, (pos, kind) in enumerate(zip(positions, kinds, strict=True)):
            out.insert(pos + offset, Stop(kind, quest_id))
        return out
    return None


def _dungeon_quests_first(world: RouteWorld, stops: Sequence[Stop]) -> bool:
    """Chaque quête d'un donjon prise par la route l'est avant son premier passage (I17, CJ1 : l'amélioration ne
    repousse plus une quête de donjon après le donjon)."""
    passed: set[str] = set()
    for s in stops:
        if s.kind == "dungeon":
            passed.add(str(s.ref))
        elif s.kind == "accept" and (q := world.quests.get(int(s.ref))) is not None and q.dungeon in passed:
            return False
    return True


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
    rng = random.Random(seed)
    best = list(stops)
    best_cost = _cost(gd, world, best, start, end_level, cap)
    for _ in range(tries):
        candidate = _mutate(world, best, rng)
        if candidate is None or not _dungeon_quests_first(world, candidate):
            continue
        cost = _cost(gd, world, candidate, start, end_level, cap)
        if cost < best_cost:
            best, best_cost = candidate, cost
    return best


def _missed_dungeon(world: RouteWorld, result: RouteResult) -> str | None:
    for d in world.dungeons.values():
        if any(d.name in w and MISSED in w for w in result.warnings):
            return d.key
    return None


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
    """Construction puis amélioration (réglages de `world.params` par défaut) ; un donjon que la construction ne peut
    pas placer dans sa fenêtre est retiré, avec un avertissement. Registre : I18"""
    tries = world.params.tries if tries is None else tries
    seed = world.params.seed if seed is None else seed
    warnings: list[str] = []
    while True:
        built = construct(gd, world, start, end_level=end_level, cap=cap)
        first = simulate(gd, world, built, start, end_level=end_level, cap=cap)
        missed = None if _acceptable(first) else _missed_dungeon(world, first)
        if missed is None:
            break
        d = world.dungeons[missed]
        warnings.append(f"donjon {d.name} retiré : impossible à placer dans sa fenêtre ({d.levels[0]}-{d.levels[1]})")
        world = replace(
            world,
            dungeons={k: v for k, v in world.dungeons.items() if k != missed},
            quests={k: q for k, q in world.quests.items() if q.dungeon != missed},
        )
    # CJ1 : l'amélioration réordonne sans retirer une quête de la construction (pas de farm quand des quêtes restent)
    kept = frozenset(int(s.ref) for s in built if s.kind == "accept")
    improved = improve(
        gd,
        replace(world, required=world.required | kept),
        built,
        start,
        end_level=end_level,
        cap=cap,
        tries=tries,
        seed=seed,
    )
    result = simulate(gd, world, improved, start, end_level=end_level, cap=cap)
    done = [Stop(r.kind, r.ref) for r in result.stops if r.kind != "grind"]
    return PlanResult(tuple(done), result, first.seconds, tries, tuple(warnings))
