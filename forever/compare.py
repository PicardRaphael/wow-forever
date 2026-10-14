"""Comparaison avec une route de Factoruide (RX1, bloc G, question RTE1).

Le joueur exporte une route de Factoruide (bouton « Share », fichier `.fgguide` : JSON `factoruide-guide`, lu en
local, jamais recopié dans le dépôt). Ses arrêts de quête sont rejoués par notre simulation (`forever/engine/route.py`,
nos règles d'XP et de temps) ; un arrêt impossible chez nous (quête inconnue, prérequis, niveau) est sauté et dit ;
les visites au maître de classe sont placées comme dans nos routes ; aucun donjon des deux côtés (les arrêts
de Factoruide ne portent pas ses passages de donjon). Le résultat se compare à notre route pour la même
demande : temps, XP par heure, quêtes communes et propres à chacune.

Même comparaison avec les parcours gratuits en clair de RestedXP (RX1c, décisions 268 et 277) : référence d'apprentissage ;
lecture dans `forever/rxp_guides.py`, aucun texte de guide dans le résultat."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any, NamedTuple

from forever.engine.dungeon import SECONDS_PER_HOUR
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
    import json

    from forever.errors import InvalidArgumentError

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("format") not in FORMATS:
            raise ValueError("format inconnu")
        route = doc["outcome"]["route"]
        stops = [
            (str(s["kind"]), int(s["quest"]))
            for s in route.get("steps") or []
            if s.get("kind") in KINDS and isinstance(s.get("quest"), int)
        ]
        return FgGuide(
            class_name=str(route["class"]).strip().lower(),
            faction=str(route["faction"]).strip().lower(),
            from_level=int(route["from_level"]),
            to_level=int(route["to_level"]),
            total_time=float(route.get("total_time") or 0.0),
            stops=stops,
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise InvalidArgumentError(
            f"{path} n'est pas un guide de Factoruide lisible ({exc}).",
            "exporter la route par « Share » dans Factoruide",
        ) from exc


def replay_guide(
    gd: GameData, world: RouteWorld, steps: Sequence[tuple[str, int]], start: RouteState, *, end_level: int, cap: int
) -> Replay:
    """Arrêts de Factoruide rejoués par notre simulation : chaque arrêt possible est gardé, les autres sont sautés
    avec leur raison ; une visite au maître de classe est placée dès qu'elle est due. Registre : I18"""
    from forever.engine.route import apply_stop, check_stop, simulate

    world = replace(world, refuse_red=False, early_zones=None)  # CJ1 : route d'un autre outil rejouée telle quelle
    state = start
    stops: list[Stop] = []
    skipped: list[dict[str, Any]] = []
    for kind, quest in steps:
        if state.level >= end_level:
            break
        due = [lv for lv in world.train_levels if lv <= state.level and lv not in state.trained]
        if world.trainers and due:
            train = Stop("train", due[-1])
            if check_stop(gd, world, state, train) is None:
                state, _ = apply_stop(gd, world, state, train, cap=cap)
                stops.append(train)
        stop = Stop(KINDS[kind], quest)
        reason = check_stop(gd, world, state, stop)
        if reason is not None:
            skipped.append({"kind": kind, "quest": quest, "reason": reason})
            continue
        state, _ = apply_stop(gd, world, state, stop, cap=cap)
        stops.append(stop)
    return Replay(stops, skipped, simulate(gd, world, stops, start, end_level=end_level, cap=cap))


def _side(result: RouteResult, quests: set[int]) -> dict[str, Any]:
    hours = result.seconds / SECONDS_PER_HOUR
    return {
        "hours": hours,
        "xp_h": result.xp_h,
        "quests": len(quests),
        "certainty": result.certainty,
        "feasible": result.feasible,
        "reached": result.reached,
        "warnings": list(result.warnings),
    }


def compare_route(deps: Any, path: Path, *, wow_dir: Path | None = None) -> dict[str, Any]:
    """Notre route et la route de Factoruide rejouée, pour la même demande, avec la provenance (`forever route
    compare`). Registre : I18"""
    from forever.engine.route import weakest
    from forever.freshness import freshness_for_version
    from forever.optimize.route import plan
    from forever.provenance import make_provenance
    from forever.route import RouteRequest, route_context

    guide = read_fgguide(path)
    # sans donjon des deux côtés : les arrêts de Factoruide ne portent pas ses passages de donjon
    request = RouteRequest(guide.class_name, guide.faction, guide.from_level, guide.to_level, dungeons="none")
    ctx = route_context(deps, request, wow_dir=wow_dir)
    ours = plan(ctx.gd, ctx.world, ctx.start, end_level=guide.to_level, cap=ctx.cap)
    replay = replay_guide(ctx.gd, ctx.world, guide.stops, ctx.start, end_level=guide.to_level, cap=ctx.cap)
    mine = {int(s.ref) for s in ours.stops if s.kind == "turnin"}
    theirs = {int(s.ref) for s in replay.stops if s.kind == "turnin"}
    certainty = weakest(ours.result.certainty, replay.result.certainty)
    fresh = freshness_for_version(deps, ctx.data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=ctx.data.game_version,
        data_sha=ctx.data.data_sha,
        freshness=fresh["freshness"],
        certainty=certainty,  # type: ignore[arg-type]
        assumptions=[
            *fresh["assumptions"],
            f"route de Factoruide lue en local ({path.name}), rejouée par nos règles d'XP et de temps",
            f"arrêts de Factoruide sautés chez nous : {len(replay.skipped)}",
            *ctx.warnings[:3],
        ],
    )
    return {
        "request": {
            "class": guide.class_name,
            "faction": guide.faction,
            "from": guide.from_level,
            "to": guide.to_level,
        },
        "ours": _side(ours.result, mine),
        "theirs": {
            **_side(replay.result, theirs),
            "factoruide_hours": guide.total_time / SECONDS_PER_HOUR,
            "skipped": replay.skipped,
        },
        "common": sorted(mine & theirs),
        "only_ours": sorted(mine - theirs),
        "only_theirs": sorted(theirs - mine),
        "provenance": provenance,
    }


# --- parcours gratuits en clair de RestedXP (RX1c, décision 268) ---------------------------------------------------


def _objective_kept(items: Sequence[tuple[int, Any]]) -> set[int]:
    """Indices des objectifs gardés : pour une quête, seule la dernière ligne `.complete` avant son rendu fait un arrêt
    (nos objectifs se font d'un seul arrêt) ; si l'étape de cette ligne reste fermée, l'objectif se fait au rendu."""
    kept: set[int] = set()
    last: dict[int, int] = {}
    for index, (_, action) in enumerate(items):
        if action.kind == "objective":
            last[action.ref] = index
        elif action.kind == "turnin" and action.ref in last:
            kept.add(last.pop(action.ref))
    kept |= set(last.values())
    return kept


def _guards_ok(world: RouteWorld, state: RouteState, step: Any, who: Any) -> bool:
    """Conditions d'une étape lues sur notre état : `.xp N,1` (sautée au niveau N ou plus), `.xp <N,1` ou saut négatif
    (sautée sous le niveau N), `.isOnQuest`, `.isQuestTurnedIn`, `.isQuestComplete`, `.isQuestAvailable` ; une condition
    dont le filtre ne vise pas le personnage est sans effet."""
    from forever.rxp_guides import applies

    if step.xp_guard is not None and applies(step.xp_guard[2], who):
        reverse, level, _ = step.xp_guard
        if (reverse and state.level < level) or (not reverse and state.level >= level):
            return False
    for guard, quest, expr in step.guards:
        if not applies(expr, who):
            continue
        q = world.quests.get(quest)
        complete = quest in state.progressed or (q is not None and q.objective is None and q.dungeon is None)
        ok = {
            "isonquest": quest in state.log,
            "isquestturnedin": quest in state.done,
            "isquestcomplete": quest in state.log and complete,
            "isquestavailable": quest not in state.done and quest not in state.log,
        }[guard]
        if not ok:
            return False
    return True


def replay_rxp(
    gd: GameData,
    world: RouteWorld,
    guides: Sequence[Any],
    who: Any,
    start: RouteState,
    *,
    end_level: int,
    cap: int,
) -> Replay:
    """Parcours RestedXP en clair rejoué par notre simulation : guides dont la tranche dépasse le niveau de départ,
    étapes et lignes filtrées pour le personnage (`<<`, `#xprate`), étapes de donjon écartées, conditions lues sur
    notre état au début de chaque étape, `.xp N` en farm jusqu'au niveau N, arrêts impossibles chez nous sautés et
    dits ; entraînements placés comme dans nos routes ; farm final jusqu'à `end_level`. Registre : I18"""
    from forever.engine.route import apply_stop, check_stop, grind_to, weakest
    from forever.rxp_guides import applies, xp_rate_ok

    # CJ1 : le jeu permet une quête rouge ou hors de la zone de départ ; seule notre route s'en garde
    world = replace(world, refuse_red=False, early_zones=None)

    steps = [
        s
        for g in guides
        if g.levels is None or g.levels[1] > start.level
        for s in g.steps
        if not s.dungeon
        and not s.hardcore
        and applies(s.filter, who)
        and (s.xp_rate is None or not applies(s.xp_rate[1], who) or xp_rate_ok(s.xp_rate[0]))
    ]
    items = [(i, a) for i, s in enumerate(steps) for a in s.actions if applies(a.filter, who)]
    kept = _objective_kept(items)
    state = start
    stops: list[Stop] = []
    results: list[Any] = []
    skipped: list[dict[str, Any]] = []
    feasible = True
    opened: dict[int, bool] = {}
    pending: set[int] = set()  # objectifs dont la dernière ligne n'est pas encore passée

    def attempt(kind: str, ref: int) -> None:
        nonlocal state
        stop = Stop(kind, ref)
        reason = check_stop(gd, world, state, stop)
        if reason is not None:
            skipped.append({"kind": kind, "quest": ref, "reason": reason})
            return
        after, res = apply_stop(gd, world, state, stop, cap=cap)
        if not math.isfinite(res.seconds):
            skipped.append({"kind": kind, "quest": ref, "reason": "trajet impossible"})
            return
        state = after
        stops.append(stop)
        results.append(res)

    for index, (step_index, action) in enumerate(items):
        if state.level >= end_level:
            break
        if step_index not in opened:
            opened[step_index] = _guards_ok(world, state, steps[step_index], who)
        if not opened[step_index]:
            continue
        if action.kind == "objective" and index not in kept:
            pending.add(action.ref)
            continue
        if action.kind == "grind":
            if state.level < action.ref:
                state, res = grind_to(gd, world, start, state, level=min(action.ref, end_level), cap=cap)
                stops.append(Stop("grind", action.ref))
                results.append(res)
            continue
        due = [lv for lv in world.train_levels if lv <= state.level and lv not in state.trained]
        if world.trainers and due and check_stop(gd, world, state, Stop("train", due[-1])) is None:
            state, res = apply_stop(gd, world, state, Stop("train", due[-1]), cap=cap)
            stops.append(Stop("train", due[-1]))
            results.append(res)
        if action.kind == "objective":
            pending.discard(action.ref)
        elif action.kind == "turnin" and action.ref in pending:  # dernière ligne `.complete` fermée : objectif ici
            pending.discard(action.ref)
            if action.ref in state.log and action.ref not in state.progressed:
                attempt("objective", action.ref)
        attempt(action.kind, action.ref)
    if state.level < end_level:
        state, res = grind_to(gd, world, start, state, level=end_level, cap=cap)
        stops.append(Stop("grind", end_level))
        results.append(res)
    seconds = sum(r.seconds for r in results)
    xp = sum(r.xp for r in results)
    feasible = math.isfinite(seconds)
    result = RouteResult(
        start_level=start.level,
        end_level=state.level,
        reached=state.level >= end_level,
        feasible=feasible,
        seconds=seconds,
        xp=xp,
        xp_h=xp / (seconds / SECONDS_PER_HOUR) if seconds > 0 and feasible else 0.0,
        stops=tuple(results),
        warnings=(),
        certainty=weakest(*(r.certainty for r in results)),
    )
    return Replay(stops, skipped, result)


def breakdown(world: RouteWorld, result: RouteResult, zone_names: Mapping[int, str]) -> dict[str, Any]:
    """Parts d'une route : heures de trajet, d'objectifs (combat), de farm et des autres arrêts ; part d'XP des rendus,
    des objectifs et du farm ; ordre des zones des rendus (zones consécutives fusionnées)."""
    hours = {"travel": 0.0, "objective": 0.0, "grind": 0.0, "other": 0.0}
    xp = {"quest": 0.0, "objective": 0.0, "grind": 0.0, "other": 0.0}
    zones: list[str] = []
    for r in result.stops:
        part = r.kind if r.kind in ("objective", "grind") else "other"
        hours["travel"] += r.travel_s / SECONDS_PER_HOUR
        hours[part] += (r.seconds - r.travel_s) / SECONDS_PER_HOUR
        xp["quest" if r.kind == "turnin" else part] += r.xp
        if r.kind == "turnin" and (q := world.quests.get(int(r.ref))) is not None and q.zone is not None:
            name = zone_names.get(q.zone) or str(q.zone)
            if not zones or zones[-1] != name:
                zones.append(name)
    total = sum(xp.values()) or 1.0
    return {
        "travel_hours": hours["travel"],
        "objective_hours": hours["objective"],
        "grind_hours": hours["grind"],
        "other_hours": hours["other"],
        "xp_share": {k: v / total for k, v in xp.items()},
        "zones": zones,
    }


def _skip_reasons(skipped: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in skipped:
        key = str(s["reason"]).split(" (")[0]
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _addons(deps: Any, wow_dir: Path | None) -> Path:
    from forever.errors import InvalidArgumentError

    root = wow_dir or deps.wow_dir
    if root is None:
        raise InvalidArgumentError("Dossier du jeu inconnu (FOREVER_WOW_DIR).", "régler FOREVER_WOW_DIR")
    return Path(root) / "Interface" / "AddOns"


def compare_rxp(
    deps: Any,
    *,
    class_name: str,
    race: str,
    faction: str,
    from_level: int,
    to_level: int,
    start_guide: str | None = None,
    wow_dir: Path | None = None,
) -> dict[str, Any]:
    """Notre route et le parcours gratuit en clair de RestedXP du même personnage, rejoué par nos règles, pour la même
    tranche de niveaux, sans donjon des deux côtés (`forever route rxp-compare`, décision 268). Aucun texte de guide
    dans le résultat. Registre : I18"""
    from forever.engine.route import weakest
    from forever.freshness import freshness_for_version
    from forever.optimize.route import plan
    from forever.provenance import make_provenance
    from forever.route import RouteRequest, route_context
    from forever.rxp_guides import applies, guide_chain, read_rxp_guides, who_for

    library = read_rxp_guides(_addons(deps, wow_dir))
    who = who_for(class_name, race, faction)
    chain = guide_chain(library, who, start=start_guide)
    request = RouteRequest(class_name.strip().lower(), faction.strip().lower(), from_level, to_level, dungeons="none")
    ctx = route_context(deps, request, wow_dir=wow_dir)
    # même départ des deux côtés : donneur de la première quête prise du parcours, sinon le départ de nos routes
    giver = next(
        (
            ctx.world.quests[a.ref].giver
            for g in chain.guides
            if g.levels is None or g.levels[1] > from_level
            for s in g.steps
            for a in s.actions
            if a.kind == "accept" and a.ref in ctx.world.quests and applies(a.filter, who) and applies(s.filter, who)
        ),
        None,
    )
    start = replace(ctx.start, position=giver) if giver is not None else ctx.start
    ours = plan(ctx.gd, ctx.world, start, end_level=to_level, cap=ctx.cap)
    replay = replay_rxp(ctx.gd, ctx.world, chain.guides, who, start, end_level=to_level, cap=ctx.cap)
    mine = {int(s.ref) for s in ours.stops if s.kind == "turnin"}
    theirs = {int(s.ref) for s in replay.stops if s.kind == "turnin"}
    certainty = weakest(ours.result.certainty, replay.result.certainty)
    fresh = freshness_for_version(deps, ctx.data.game_version, allow_network=False)
    levels = [g.levels[1] for g in chain.guides if g.levels]
    provenance = make_provenance(
        deps,
        game_version=ctx.data.game_version,
        data_sha=ctx.data.data_sha,
        freshness=fresh["freshness"],
        certainty=certainty,  # type: ignore[arg-type]
        assumptions=[
            *fresh["assumptions"],
            (
                "parcours gratuits en clair de RestedXP lus en local (RXPGuides/Guides/Forever), rejoués par nos règles "
                "d'XP et de temps : référence d'apprentissage de notre optimiseur (décisions 268 et 277)"
            ),
            f"blocs non lisibles en clair ignorés sans être décodés : {library.refused}",
            "sans donjon des deux côtés, même point de départ ; objectifs d'une quête faits en un arrêt",
            f"étapes de RestedXP impossibles chez nous : {len(replay.skipped)}",
            *ctx.warnings[:3],
        ],
    )
    zone_names = ctx.book.zone_names
    return {
        "request": {
            "class": request.class_name,
            "race": who.race,
            "faction": request.faction,
            "from": from_level,
            "to": to_level,
        },
        "guides": {
            "count": len(chain.guides),
            "missing": list(chain.missing),
            "max_level": max(levels) if levels else None,
            "refused": library.refused,
        },
        "ours": {**_side(ours.result, mine), **breakdown(ctx.world, ours.result, zone_names)},
        "theirs": {
            **_side(replay.result, theirs),
            **breakdown(ctx.world, replay.result, zone_names),
            "skipped": replay.skipped,
            "skip_reasons": _skip_reasons(replay.skipped),
        },
        "common": sorted(mine & theirs),
        "only_ours": sorted(mine - theirs),
        "only_theirs": sorted(theirs - mine),
        "provenance": provenance,
    }


def rxp_coverage(deps: Any, *, wow_dir: Path | None = None, dungeon_guides: bool = False) -> dict[str, Any]:
    """Jusqu'où vont les parcours gratuits en clair de RestedXP installés (`forever route rxp-coverage`)."""
    from forever.provenance import local_provenance
    from forever.rxp_guides import coverage, read_rxp_guides

    library = read_rxp_guides(_addons(deps, wow_dir), dungeon_guides=dungeon_guides)
    return {
        "files": library.files,
        "guides": len(library.guides),
        "refused": library.refused,
        "chains": coverage(library),
        "provenance": local_provenance(
            deps,
            certainty="probable",
            assumptions=[
                (
                    "en-têtes des parcours gratuits en clair de RestedXP lus en local (décision 268) ; une suite annoncée "
                    "absente en clair est un guide payant ou non livré"
                ),
                f"blocs non lisibles en clair ignorés sans être décodés : {library.refused}",
            ],
        ),
    }
