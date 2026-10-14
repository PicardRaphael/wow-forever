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
    return {"hours": hours, "xp_h": result.xp_h, "quests": len(quests), "certainty": result.certainty}


def compare_route(deps: Any, path: Path, *, wow_dir: Path | None = None) -> dict[str, Any]:
    """Notre route et la route de Factoruide rejouée, pour la même demande, avec la provenance (`forever route
    compare`). Registre : I18"""
    from forever.engine.route import weakest
    from forever.freshness import freshness_for_version
    from forever.optimize.route import plan
    from forever.provenance import make_provenance
    from forever.route import RouteRequest, route_context

    guide = read_fgguide(path)
    request = RouteRequest(guide.class_name, guide.faction, guide.from_level, guide.to_level)
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
