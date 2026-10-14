"""Étapes de route neutres (T04f, préparées pour RX1) : une étape à placer dans une route de leveling (aller, prendre,
rendre, cliquer, utiliser un objet, note). T04f fournit deux producteurs : la chaîne du sac de couchage
(`sleeping_bag_steps`) et les rappels de bonus d'XP (`bonus_reminders`) ; RX1 les place dans la route et les encode
au format RestedXP. Aucun chiffre de jeu ici."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from forever.engine.model import GameData
from forever.engine.xp import XpBonusState

KINDS = ("goto", "accept", "turnin", "click", "use_item", "note", "complete", "dungeon", "xp", "train")
SECONDS_PER_HOUR = 3600.0  # conversion d'unité
FOOD_EXAMPLES = 3  # nourritures citées dans un rappel


@dataclass(frozen=True)
class RouteStep:
    kind: str  # KINDS
    text: str
    quest_id: int | None = None
    item_id: int | None = None
    map: int | None = None  # uiMapID
    zone: str | None = None  # nom anglais de la carte
    x: float | None = None  # position en pourcentage de la carte
    y: float | None = None
    level: int | None = None
    at_s: float | None = None  # rappel : instant de la séance (secondes depuis son début)
    source: str = ""
    certainty: str = "suppose"


def sleeping_bag_steps(chain: Any) -> list[RouteStep]:
    """Étapes de la chaîne du sac de couchage (`xp_bonuses.sleeping_bag_chain`), une par point, dans l'ordre du camp."""
    return list(chain.steps)


def bonus_reminders(gd: GameData, state: XpBonusState, *, hours: float, level: int) -> list[RouteStep]:
    """Rappels des bonus d'XP sur une séance de `hours` heures : sac de couchage reposé à chaque recharge de l'objet,
    nourriture nutritive de son niveau (sans nourriture active), tente avant la séance. Valeurs lues dans les données.

    Registre : D5, D9, E3"""
    from forever.engine.xp import xp_bonus_data

    data = xp_bonus_data(gd)
    out: list[RouteStep] = []
    bag = data.sleeping_bag
    if bag is not None and level >= bag.required_level and bag.cooldown_s > 0:
        aura = data.auras.get(bag.aura)
        count = math.ceil(hours * SECONDS_PER_HOUR / bag.cooldown_s)
        out += [
            RouteStep(
                "use_item",
                f"pose {bag.name} et reste assis dedans jusqu'à {bag.max_stacks} cumuls de "
                f"{aura.name if aura else bag.aura}",
                item_id=bag.item,
                level=level,
                at_s=i * bag.cooldown_s,
                source="xp_bonuses.json (sleeping_bag, client)",
                certainty="probable",
            )
            for i in range(count)
        ]
    foods = sorted((f for f in data.food if f.required_level <= level), key=lambda f: (-f.required_level, f.name))
    if not state.food and foods:
        names = ", ".join(f.name for f in foods[:FOOD_EXAMPLES])
        out.append(
            RouteStep(
                "note",
                f"mange une nourriture nutritive de ton niveau ({names})",
                level=level,
                at_s=0.0,
                source="xp_bonuses.json (food, client) ; xp.food_bonus",
                certainty="suppose",
            )
        )
    if data.tent_threshold_pct is not None:
        out.append(
            RouteStep(
                "note",
                "monte une tente près d'un feu de camp avant la séance (repos remonté)",
                level=level,
                at_s=0.0,
                source="xp_bonuses.json (camp, client) ; xp.camp_tent",
                certainty="probable",
            )
        )
    return sorted(out, key=lambda s: s.at_s or 0.0)


def _quest_step(kind: str, quest_id: int, quests: Any, place_field: str, verb: str, source: str) -> RouteStep:
    from forever.quests import value

    quest = quests.quests.get(quest_id) if quests is not None else None
    name = quest["name"] if quest else None
    place = value(quest, place_field) if quest else None
    place = place if isinstance(place, dict) else {}
    who = f" auprès de {place['name']}" if place.get("name") else ""
    return RouteStep(
        kind,
        f"{verb} {name or f'la quête {quest_id}'}{who}",
        quest_id=quest_id,
        map=place.get("map"),
        x=place.get("x"),
        y=place.get("y"),
        source=source,
        certainty="suppose",
    )


def _allowed(quest_id: int, quests: Any, faction: str | None) -> bool:
    from forever.quests import value

    quest = quests.quests.get(quest_id) if quests is not None else None
    side = value(quest, "faction") if quest else None
    return faction is None or side in (faction, "both", None)


def dungeon_steps(book: Any, key: str, *, faction: str | None, level: int, quests: Any = None) -> list[RouteStep]:
    """Étapes d'un donjon pour RX1 : prérequis hors du donjon (pris et rendus, dans l'ordre), quêtes du donjon prises
    auprès de leur donneur, entrée, passage, rendus. Positions des sources (`suppose`), jamais devinées.

    Registre : I17"""
    d = book.dungeons[key]
    source = f"livre des donjons ({', '.join(d['sources'])}) et livre des quêtes"
    steps: list[RouteStep] = []
    for quest_id in d["first_steps"]:
        if _allowed(quest_id, quests, faction):
            steps.append(_quest_step("accept", quest_id, quests, "giver", "prends", source))
            steps.append(_quest_step("turnin", quest_id, quests, "turn_in", "rends", source))
    inside = [
        q["id"]
        for q in d["quests"]
        if _allowed(q["id"], quests, faction) and (q["min_level"] is None or q["min_level"] <= level)
    ]
    steps += [_quest_step("accept", quest_id, quests, "giver", "prends", source) for quest_id in inside]
    entrance = d["fields"].get("entrance")
    e = entrance["value"] if entrance else {}
    steps.append(
        RouteStep(
            "goto",
            f"va à l'entrée de {d['name']}",
            map=e.get("map"),
            x=e.get("x"),
            y=e.get("y"),
            level=level,
            source=f"entrée : {entrance['source']}" if entrance else "entrée inconnue des sources",
            certainty=entrance["certainty"] if entrance else "suppose",
        )
    )
    steps.append(RouteStep("note", f"fais {d['name']} avec ton groupe", level=level, source=source))
    steps += [_quest_step("turnin", quest_id, quests, "turn_in", "rends", source) for quest_id in inside]
    return steps


def dungeon_placements(deps: Any, *, class_name: str, faction: str | None, wow_dir: Any = None) -> list[dict[str, Any]]:
    """Pour chaque donjon ouvert du livre (plage connue, camp permis) : niveau de placement et fenêtre (objectifs de
    leveling au premier niveau de sa plage), étapes de route, XP et minutes du premier passage (passages suivants
    sans quête). Un donjon au-delà du plafond de niveau est rendu sans placement.

    Registre : I17"""
    from forever.dungeons import build_dungeons
    from forever.leveling import level_cap
    from forever.quests import build_quests
    from forever.sim.objectives import objectives
    from forever.store import load_version

    book = build_dungeons(deps, wow_dir=wow_dir)
    quests = build_quests(deps, wow_dir=wow_dir)
    cap = level_cap(load_version(deps))
    reports: dict[int, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    for key, d in sorted(book.dungeons.items()):
        rng = (d["fields"].get("levels") or {}).get("value")
        own = (d["fields"].get("faction") or {}).get("value")
        if d["closed"] or not rng or (faction is not None and own not in (None, faction)):
            continue
        row: dict[str, Any] = {
            "id": key,
            "name": d["name"],
            "levels": rng,
            "placement": None,
            "steps": [],
            "quests": [q["id"] for q in d["quests"]],
        }
        if rng["min"] > cap:
            row["note"] = f"plage au-delà du plafond de niveau ({cap})"
            out.append(row)
            continue
        lvl = rng["min"]
        if lvl not in reports:
            reports[lvl] = objectives(deps, class_name=class_name, level=lvl, faction=faction, wow_dir=wow_dir)
        entry = next((x for x in reports[lvl]["dungeons"] if x["id"] == key), None)
        if entry is not None:
            chosen = entry["first_pass"] or entry["repeat"]
            row.update(
                placement=entry["placement"],
                xp=chosen["xp"],
                minutes=chosen["minutes"],
                kind=chosen["kind"],
                run=entry["run"],
            )
        at = row["placement"]["level"] if row["placement"] else lvl
        row["steps"] = dungeon_steps(book, key, faction=faction, level=at, quests=quests)
        out.append(row)
    return out


# --- RX1, bloc C : feuille de route assemblée (hors moteur) -----------------------------------------------------

ROUTES_DIR = "routes"  # plans gardés dans <cache>/routes/<id>.json
LISTED_IDS = 20  # identifiants cités dans un avertissement (paramètre d'affichage)
ID_LENGTH = 12  # caractères de l'identifiant d'un plan


@dataclass(frozen=True)
class RouteRequest:
    """Demande d'une feuille de route : personnage, niveaux, donjons (`auto`, `none` ou clés du livre), quêtes de
    classe, quêtes exclues ou imposées, réglages de la recherche (défaut : `route.search`)."""

    class_name: str
    faction: str
    start_level: int
    end_level: int
    dungeons: str | tuple[str, ...] = "auto"
    group: bool = False
    class_quests: bool = True
    exclude: tuple[int, ...] = ()
    include: tuple[int, ...] = ()
    tries: int | None = None
    seed: int | None = None


def _ids(label: str, ids: list[int]) -> str:
    shown = ", ".join(str(i) for i in sorted(ids)[:LISTED_IDS])
    more = f" ; {len(ids) - LISTED_IDS} autre(s)" if len(ids) > LISTED_IDS else ""
    return f"{label} ({len(ids)}) : {shown}{more}"


def route_params(values: Any) -> Any:
    """Réglages de la route (`mechanics.json`, `route.search`). Registre : I18"""
    from forever.engine.route import SEARCH_KEY, RouteParams

    raw = values[SEARCH_KEY]["value"]
    return RouteParams(
        log_size=int(raw["log_size"]),
        stop_overhead_s=float(raw["stop_overhead_s"]),
        tries=int(raw["tries"]),
        seed=int(raw["seed"]),
        zone_stay=float(raw["zone_stay"]),
        min_efficiency=float(raw["min_efficiency"]),
        train_time_s=float(raw["train_time_s"]),
        train_max_delay=int(raw["train_max_delay"]),
    )


def _point(maps: Any, place: Any) -> Any:
    from forever.engine.travel import map_to_world

    if not isinstance(place, dict) or place.get("map") not in maps:
        return None
    if not isinstance(place.get("x"), int | float) or not isinstance(place.get("y"), int | float):
        return None
    return map_to_world(maps[place["map"]], float(place["x"]), float(place["y"]))


def _dungeon_rows(rows: Any, request: RouteRequest, maps: Any, warnings: list[str]) -> dict[str, Any]:
    from forever.engine.route import RouteDungeon, weakest

    wanted = request.dungeons
    out: dict[str, Any] = {}
    for row in rows:
        keys = {str(w).lower() for w in wanted} if isinstance(wanted, tuple) else None
        if keys is not None and str(row["id"]).lower() not in keys and str(row["name"]).lower() not in keys:
            continue
        placement = row.get("placement")
        if not placement:
            warnings.append(f"donjon {row['name']} : aucun niveau de placement (ignoré)")
            continue
        low = int(placement["level"])
        high = max([low, *(int(w) for w in placement.get("window") or [] if int(w) >= low)])
        if high < request.start_level or low >= request.end_level:
            continue
        goto = next((s for s in row.get("steps") or [] if _step_kind(s) == "goto"), None)
        entrance = _point(maps, _step_place(goto)) if goto is not None else None
        if entrance is None:
            warnings.append(f"donjon {row['name']} : entrée sans position connue (ignoré)")
            continue
        run = row["run"]
        out[str(row["id"])] = RouteDungeon(
            key=str(row["id"]),
            name=row["name"],
            entrance=entrance,
            levels=(low, high),
            quests=tuple(int(q) for q in row.get("quests") or []),
            minutes=float(run["minutes"]),
            kills=float(run["kills"]),
            mob_level=int(run["mob_level"]),
            group=int(row.get("group") or 0) or 1,
            certainty=weakest(run.get("certainty", "suppose"), "suppose"),
        )
    return out


def _step_kind(step: Any) -> str | None:
    return step.kind if isinstance(step, RouteStep) else (step or {}).get("kind")


def _step_place(step: Any) -> dict[str, Any]:
    if isinstance(step, RouteStep):
        return {"map": step.map, "x": step.x, "y": step.y}
    return {"map": step.get("map"), "x": step.get("x"), "y": step.get("y")}


def _camps(obj: dict[str, Any]) -> list[dict[str, Any]]:
    """Camps d'objectif en positions `{map, x, y}` (Journeys les écrit `[carte, x, y]`)."""
    out = []
    for c in obj.get("camps") or []:
        if isinstance(c, list | tuple) and len(c) == 3:
            out.append({"map": c[0], "x": c[1], "y": c[2]})
        elif isinstance(c, dict):
            out.append(c)
    return out


def _objective(maps: Any, quest: Any, giver: Any, kills_per_quest: float) -> tuple[Any, float, bool]:
    """(position, monstres, position supposée) de l'objectif : camp de Journeys, sinon donneur ; aucun objectif
    connu : rien à faire entre la prise et le rendu."""
    from forever.quests import value

    obj = value(quest, "objectives")
    if not isinstance(obj, dict):
        return None, 0.0, False
    camps = [p for p in (_point(maps, c) for c in _camps(obj)) if p is not None]
    fights = bool(obj.get("creatures") or obj.get("items") or obj.get("camps"))
    if camps:
        return camps[0], kills_per_quest if fights else 0.0, False
    if fights or obj.get("objects"):
        return giver, kills_per_quest if fights else 0.0, True
    return None, 0.0, False


def route_world(
    gd: GameData,
    book: Any,
    maps: Any,
    *,
    request: RouteRequest,
    values: Any,
    dungeons: Any,
    travel: Any,
    kill_seconds: Any,
    trainers: Any = (),
    train_levels: Any = (),
) -> tuple[Any, list[str]]:
    """Entrées du moteur de route (`RouteWorld`) tirées du livre des quêtes, des placements de donjon de DJ1 et des
    cartes de zone ; avertissements (quêtes écartées et pourquoi). Registre : I18"""
    from forever.engine.route import RouteQuest, RouteWorld, best_zone_xp_h, weakest
    from forever.engine.xp import gray_level
    from forever.pipeline.questie import CLASS_MASKS
    from forever.quests import routable, value
    from forever.sim.objectives import OBJECTIVES_KEY

    warnings: list[str] = []
    objectives = values[OBJECTIVES_KEY]["value"]
    kills_per_quest = float(objectives["kills_per_quest"])
    overhead = float(objectives["quest_overhead_s"])
    group = int(objectives["dungeon_party"])
    rows = [{**r, "group": group} for r in dungeons]
    chosen = _dungeon_rows(rows, request, maps, warnings)
    dungeon_of = {q: d.key for d in chosen.values() for q in d.quests}
    mask = CLASS_MASKS.get(request.class_name.strip().lower(), 0)
    gray = gray_level(gd, request.start_level)
    dropped: dict[str, list[int]] = {}
    quests: dict[int, Any] = {}
    for quest_id, q in sorted(book.quests.items()):
        forced = quest_id in request.include
        side, classes = value(q, "faction"), value(q, "classes")
        level, min_level = value(q, "level"), value(q, "min_level")
        reason = None
        if quest_id in request.exclude:
            reason = "exclues à la demande"
        elif not routable(q):
            reason = "sans donneur positionné ou vues seulement chez Factoruide"
        elif side not in (request.faction, "both", None):
            continue  # autre camp : rien à dire
        elif isinstance(classes, int) and classes and not classes & mask:
            continue  # autre classe
        elif isinstance(classes, int) and classes and not request.class_quests and not forced:
            reason = "quêtes de classe laissées de côté"
        elif not isinstance(level, int) or not isinstance(min_level, int):
            reason = "sans niveau connu"
        elif min_level >= request.end_level:
            reason = "niveau minimal au-delà de la route"
        elif level <= gray and not forced:
            continue  # grise dès le départ
        elif value(q, "dungeon") and quest_id not in dungeon_of:
            reason = "quêtes d'un donjon hors de la route"
        if reason is not None:
            dropped.setdefault(reason, []).append(quest_id)
            continue
        giver = _point(maps, value(q, "giver"))
        if giver is None:
            dropped.setdefault("donneur sur une carte inconnue", []).append(quest_id)
            continue
        turn_in = _point(maps, value(q, "turn_in")) or giver
        objective, kills, guessed = _objective(maps, q, giver, kills_per_quest)
        xp = q["fields"].get("xp")
        chain = value(q, "chain") or {}
        giver_place = value(q, "giver")
        quests[quest_id] = RouteQuest(
            id=quest_id,
            name=q["name"] or str(quest_id),
            level=level,
            min_level=min_level,
            base_xp=float(xp["value"]) if xp and isinstance(xp["value"], int | float) else 0.0,
            xp_source=xp["source"] if xp else "XP inconnue des sources",
            xp_certainty=xp["certainty"] if xp else "suppose",
            giver=giver,
            turn_in=turn_in,
            objective=objective,
            kills=kills,
            mob_level=level,
            zone=giver_place.get("map") if isinstance(giver_place, dict) else None,
            prereq_all=tuple(value(q, "prereq_all") or ()),
            prereq_any=tuple(value(q, "prereq_any") or ()),
            after=tuple(chain.get("after") or ()),
            exclusive=tuple(value(q, "exclusive") or ()),
            dungeon=dungeon_of.get(quest_id),
            certainty=weakest(q["fields"]["giver"]["certainty"], *(["suppose"] if guessed else [])),
        )
    # quêtes dont un prérequis est hors de la route : jamais prenables
    changed = True
    while changed:
        changed = False
        for quest_id, rq in list(quests.items()):
            known = set(quests)
            if (
                not set(rq.prereq_all) <= known
                or (rq.prereq_any and not set(rq.prereq_any) & known)
                or (rq.after and not set(rq.after) & known)
            ):
                dropped.setdefault("prérequis hors de la route", []).append(quest_id)
                del quests[quest_id]
                changed = True
    warnings += [_ids(f"quêtes écartées, {reason}", ids) for reason, ids in sorted(dropped.items())]
    zone_quests = [q for q in quests.values() if q.dungeon is None]
    memo: dict[int, float | None] = {}

    def best_zone(level: int) -> float | None:
        if level not in memo:
            memo[level] = best_zone_xp_h(
                gd, zone_quests, level, kill_seconds=kill_seconds(level), overhead_s=overhead, bonuses=None
            )
        return memo[level]

    world = RouteWorld(
        quests=quests,
        dungeons=chosen,
        params=route_params(values),
        travel=travel,
        kill_seconds=kill_seconds,
        best_zone_xp_h=best_zone,
        required=frozenset(q for q in request.include if q in quests),
        trainers=_trainer_points(maps, trainers, request.faction),
        train_levels=tuple(lv for lv in sorted(set(train_levels)) if request.start_level < lv < request.end_level),
    )
    return world, warnings


def _trainer_points(maps: Any, trainers: Any, faction: str) -> tuple[Any, ...]:
    """Positions monde des maîtres de classe amicaux pour le camp, sans doublon."""
    side = {"horde": "H", "alliance": "A"}.get(faction, "")
    out: list[Any] = []
    for t in trainers:
        point = _point(maps, {"map": t.ui_map, "x": t.x, "y": t.y}) if side in t.sides else None
        if point is not None and point not in out:
            out.append(point)
    return tuple(out)


def _place_of(book: Any, rows: dict[str, Any], kind: str, ref: Any) -> dict[str, Any]:
    from forever.quests import value

    if kind in ("dungeon", "dungeon_repeat"):
        row = rows.get(str(ref)) or {}
        goto = next((s for s in row.get("steps") or [] if _step_kind(s) == "goto"), None)
        return _step_place(goto) if goto is not None else {}
    if kind in ("grind", "train"):
        return {}
    q = book.quests.get(ref)
    if q is None:
        return {}
    if kind == "objective":
        obj = value(q, "objectives")
        camps = _camps(obj) if isinstance(obj, dict) else []
        place = camps[0] if camps else value(q, "giver")
    else:
        place = value(q, "turn_in" if kind == "turnin" else "giver") or value(q, "giver")
    return place if isinstance(place, dict) else {}


STEP_KIND = {
    "accept": "accept",
    "objective": "complete",
    "turnin": "turnin",
    "dungeon": "dungeon",
    "dungeon_repeat": "dungeon",
    "grind": "xp",
    "train": "train",
}
STEP_VERB = {
    "accept": "prends",
    "objective": "fais l'objectif de",
    "turnin": "rends",
    "dungeon": "fais",
    "dungeon_repeat": "refais",
    "train": "apprends tes nouveaux sorts chez",
}


def _stop_payload(book: Any, rows: dict[str, Any], r: Any, *, end_level: int) -> dict[str, Any]:
    place = _place_of(book, rows, r.kind, r.ref)
    if r.kind in ("dungeon", "dungeon_repeat"):
        name = (rows.get(str(r.ref)) or {}).get("name", str(r.ref))
    elif r.kind == "grind":
        name = None
    elif r.kind == "train":
        name = "ton maître de classe"
    else:
        q = book.quests.get(r.ref)
        name = (q or {}).get("name") or f"la quête {r.ref}"
    text = (
        f"farme des monstres de ton niveau jusqu'au niveau {end_level}"
        if r.kind == "grind"
        else (f"{STEP_VERB[r.kind]} {name}")
    )
    return {
        "kind": r.kind,
        "ref": r.ref,
        "name": name,
        "text": text,
        "level": r.level,
        "xp": r.xp,
        "seconds": r.seconds,
        "travel_s": r.travel_s,
        "certainty": r.certainty,
        "map": place.get("map"),
        "zone": book.zone_names.get(place.get("map")) if place.get("map") is not None else None,
        "x": place.get("x"),
        "y": place.get("y"),
    }


def _step(stop: dict[str, Any]) -> RouteStep:
    return RouteStep(
        STEP_KIND[stop["kind"]],
        stop["text"],
        quest_id=stop["ref"] if isinstance(stop["ref"], int) else None,
        map=stop["map"],
        zone=stop["zone"],
        x=stop["x"],
        y=stop["y"],
        level=stop["level"],
        source="feuille de route (forever route plan)",
        certainty=stop["certainty"],
    )


def _rewards(book: Any, stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Objets de récompense des quêtes rendues sur la route (sources du livre des quêtes), au plus LISTED_IDS."""
    from forever.quests import value

    out: list[dict[str, Any]] = []
    for s in stops:
        quest = book.quests.get(s["ref"]) if s["kind"] == "turnin" else None
        rewards = value(quest, "rewards") if quest else None
        for item in (rewards or {}).get("items") or [] if isinstance(rewards, dict) else []:
            if isinstance(item, dict) and item.get("item") is not None:
                out.append({"quest": s["ref"], "item": item["item"], "name": item.get("name")})
    return out[:LISTED_IDS]


def plan_route(deps: Any, request: RouteRequest, *, wow_dir: Any = None) -> dict[str, Any]:
    """Feuille de route calculée, gardée dans le cache, avec sa provenance (`forever route plan`). Registre : I18"""
    import hashlib
    import json
    from dataclasses import asdict

    from forever.engine.route import RouteState
    from forever.engine.travel import travel_params, travel_time
    from forever.errors import InvalidArgumentError
    from forever.freshness import freshness_for_version
    from forever.gamedata import MECHANICS_FILE, build_game_data
    from forever.kill_time import kill_params, kill_time, load_kill_times
    from forever.leveling import check_level, level_cap
    from forever.optimize.route import plan
    from forever.pipeline.questie import CLASS_IDS, CLASS_MASKS
    from forever.pipeline.travel_sources import (
        read_journeys_network,
        read_journeys_walks,
        read_questie_trainers,
        read_training_levels,
    )
    from forever.provenance import make_provenance
    from forever.quests import build_quests
    from forever.store import load_version
    from forever.travel import WalkCache, load_travel, transports_from_network, walk_nets

    cls = request.class_name.strip().lower()
    if cls not in CLASS_MASKS:
        raise InvalidArgumentError(
            f"Classe inconnue : {request.class_name}.", f"choisir parmi : {', '.join(CLASS_MASKS)}"
        )
    if request.faction not in ("horde", "alliance"):
        raise InvalidArgumentError(f"Camp inconnu : {request.faction}.", "choisir horde ou alliance")
    data = load_version(deps)
    cap = level_cap(data)
    check_level(request.start_level, cap, "Niveau de départ")
    check_level(request.end_level, cap, "Niveau d'arrivée")
    if request.end_level <= request.start_level:
        raise InvalidArgumentError(
            "Niveau d'arrivée au plus égal au niveau de départ.", "donner --to plus grand que --from"
        )
    gd = build_game_data(data)
    values = data.read_json(MECHANICS_FILE)["values"]
    book = build_quests(deps, wow_dir=wow_dir)
    graph, maps = load_travel(deps, request.faction)
    tp = travel_params(values)
    measures = load_kill_times(deps)
    kp = kill_params(values)
    kill_memo: dict[int, Any] = {}

    def kill(level: int) -> Any:
        if level not in kill_memo:
            kill_memo[level] = kill_time(kp, class_name=cls, level=level, measures=measures)
        return kill_memo[level]

    addons = (wow_dir or deps.wow_dir) / "Interface" / "AddOns" if (wow_dir or deps.wow_dir) else None
    network = read_journeys_network(addons) if addons else None
    if network is not None:  # bateaux, zeppelins, portail et tram de Journeys (bloc F, suppose)
        graph = graph._replace(transports=transports_from_network(network, request.faction))
    nets = walk_nets(read_journeys_walks(addons)) if addons else {}
    walker = WalkCache(nets, tp.detour) if nets else None
    travel_memo: dict[tuple[Any, Any, int], float] = {}

    def travel(a: Any, b: Any, level: int) -> float:
        key = (a, b, int(level >= tp.mount_level))
        if key not in travel_memo:
            travel_memo[key] = travel_time(
                graph, a, b, params=tp, level=level, flights_known=frozenset(), walk=walker
            ).seconds
        return travel_memo[key]

    trainers = read_questie_trainers(addons, f"{cls.capitalize()} Trainer") if addons else []
    train_levels = read_training_levels(addons).get(CLASS_IDS[cls], ()) if addons else ()

    rows: list[dict[str, Any]] = []
    if request.dungeons != "none":
        rows = dungeon_placements(deps, class_name=cls, faction=request.faction, wow_dir=wow_dir)
    world, warnings = route_world(
        gd,
        book,
        maps,
        request=request,
        values=values,
        dungeons=rows,
        travel=travel,
        kill_seconds=lambda level: kill(level).seconds,
        trainers=trainers,
        train_levels=train_levels,
    )
    if not world.quests:
        warnings.append("aucune quête placée : la route n'est que du farm")
    first = min(world.quests.values(), key=lambda q: (q.min_level, q.level, q.id), default=None)
    if first is not None:
        position = first.giver
    else:
        position = next(iter(maps.values()), None)
        position = position and _point(maps, {"map": position.ui_map, "x": 50.0, "y": 50.0})
    start = RouteState(level=request.start_level, xp=0.0, position=position)
    found = plan(gd, world, start, end_level=request.end_level, cap=cap, tries=request.tries, seed=request.seed)
    result = found.result
    by_id = {str(r["id"]): r for r in rows}
    stops = [_stop_payload(book, by_id, r, end_level=request.end_level) for r in result.stops]
    reminders = bonus_reminders(gd, XpBonusState(), hours=result.seconds / SECONDS_PER_HOUR, level=request.start_level)
    request_doc = {**asdict(request), "class_name": cls}
    plan_id = hashlib.sha256(
        json.dumps([request_doc, data.data_sha, book.fingerprint], sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:ID_LENGTH]
    k = kill(request.start_level)
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    assumptions = [
        *fresh["assumptions"],
        f"temps par monstre : {k.source} ({k.method}, {k.certainty})",
        (
            "trajets : marche par le réseau de Naowh Journeys "
            + ("lu en local" if walker else "absent : ligne droite allongée")
            + ", bateaux, zeppelins, portail et tram de Journeys "
            + (f"{network.version or ''} (suppose)" if network else "absents : aucun changement de continent")
            + " ; vitesses de route.travel reprises de Factoruide (suppose, TRV1) ; vols connus du personnage inconnus : "
            "aucun vol pris"
        ),
        (
            f"maître de classe : {len(train_levels)} niveau(x) d'entraînement (Naowh Training), "
            f"{len(trainers)} position(s) de maître (Questie), visite au plus tard un niveau après (route.search)"
            if trainers and train_levels
            else "maître de classe : niveaux ou positions inconnus, visites non comptées"
        ),
        "position de départ supposée : donneur de la première quête de la route",
        "objectif d'une quête : camp de Journeys, sinon donneur (suppose) ; monstres par quête de leveling.objectives",
        "bonus d'XP : aucun pris en compte dans le calcul (rappels à part)",
        "recherche : sous-ensemble porté de Factoruide (MIT, brouznouf/factoruide@f7da6da), graine fixe",
        *warnings,
        *found.warnings,
        *result.warnings,
    ]
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty=result.certainty,  # type: ignore[arg-type]
        assumptions=assumptions,
    )
    payload = {
        "id": plan_id,
        "request": request_doc,
        "class": cls,
        "faction": request.faction,
        "levels": {"from": request.start_level, "to": request.end_level, "reached": result.end_level},
        "feasible": result.feasible,
        "seconds": result.seconds,
        "hours": result.seconds / SECONDS_PER_HOUR,
        "xp": result.xp,
        "xp_h": result.xp_h,
        "stops": stops,
        "steps": [asdict(_step(s)) for s in stops],
        "dungeons": [
            {"id": s["ref"], "name": s["name"], "level": s["level"], "kind": s["kind"]}
            for s in stops
            if s["kind"] in ("dungeon", "dungeon_repeat")
        ],
        "reminders": [asdict(r) for r in reminders],
        "rewards": _rewards(book, stops),
        "warnings": [*warnings, *found.warnings, *result.warnings],
        "search": {
            "tries": found.tries,
            "seed": request.seed if request.seed is not None else world.params.seed,
            "construct_seconds": found.construct_seconds,
            "seconds": result.seconds,
        },
        "certainty": result.certainty,
        "provenance": provenance,
    }
    path = deps.cache_dir / ROUTES_DIR / f"{plan_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")  # écriture atomique : le pont peut lire le plan au même moment
    tmp.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    tmp.replace(path)
    return payload


def guide_name(plan: Any) -> str:
    """Nom du guide RestedXP d'un plan (anglais, client enUS) : classe et niveaux."""
    lv = plan["levels"]
    return f"Forever {str(plan.get('class', '')).capitalize()} {lv['from']}-{lv['to']} ({plan['id'][:6]})"


def load_plan(deps: Any, plan_id: str) -> dict[str, Any]:
    """Plan gardé dans le cache (`forever route show`)."""
    import json

    from forever.errors import InvalidArgumentError

    path = deps.cache_dir / ROUTES_DIR / f"{plan_id}.json"
    if not plan_id.isalnum() or not path.is_file():
        raise InvalidArgumentError(f"Feuille de route inconnue : {plan_id}.", "lancer forever route plan")
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


PREVIEW_FIELDS = ("id", "levels", "hours", "xp_h", "dungeons", "rewards", "bonuses", "certainty", "stops")


def route_preview(plan: Any) -> dict[str, Any]:
    """Aperçu d'un plan pour le joueur (bouton « Feuille de route », outil `forever_route`) : niveaux, temps, XP par
    heure, donjons placés, récompenses notables, bonus rappelés, certitude, nombre d'arrêts."""
    return {
        "id": plan["id"],
        "levels": plan["levels"],
        "hours": plan.get("hours"),
        "xp_h": plan.get("xp_h"),
        "dungeons": [
            {"name": s["name"], "level": s["level"]}
            for s in plan["stops"]
            if s["kind"] in ("dungeon", "dungeon_repeat")
        ],
        "rewards": list(plan.get("rewards") or []),
        "bonuses": [r["text"] for r in plan.get("reminders") or []],
        "certainty": plan["certainty"],
        "stops": len(plan["stops"]),
    }
