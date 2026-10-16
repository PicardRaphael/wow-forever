"""Étapes de route neutres (T04f, préparées pour RX1) : une étape à placer dans une route de leveling (aller, prendre,
rendre, cliquer, utiliser un objet, note). T04f fournit deux producteurs : la chaîne du sac de couchage
(`sleeping_bag_steps`) et les rappels de bonus d'XP (`bonus_reminders`) ; RX1 les place dans la route et les encode
au format RestedXP. Aucun chiffre de jeu ici."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
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


def dungeon_placements(
    deps: Any, *, class_name: str, faction: str | None, wow_dir: Any = None, below: int | None = None
) -> list[dict[str, Any]]:
    """Pour chaque donjon ouvert du livre (plage connue, camp permis) : niveau de placement et fenêtre (objectifs de
    leveling au premier niveau de sa plage), étapes de route, XP et minutes du premier passage (passages suivants
    sans quête). Un donjon au-delà du plafond de niveau est rendu sans placement ; `below` (CJ1) : donjons dont la
    plage commence à ce niveau ou plus laissés de côté (hors de la route, calcul évité).

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
        if below is not None and rng["min"] >= below:
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
    professions: tuple[tuple[str, int, int], ...] = ()  # (métier, rang, rang maximal), bloc H
    race: str | None = None  # CJ1 : race du personnage (nom de races.json), masques de race et zone de départ
    start_at: tuple[int, float, float] | None = None  # CJ1 : position réelle (uiMapID, x, y en pourcentage)
    done: tuple[int, ...] = ()  # CJ1 : quêtes déjà faites par ce personnage (profil, Questie)
    character: str | None = None  # CJ1 : nom du personnage (quêtes faites lues au profil, nom du guide)
    purpose: str | None = None  # bloc 4d : « équipement » pour une route d'équipement (nom stable du guide)


FILTERS_KEY = "route.filters"  # CJ1 : garde-fous des feuilles de route (mechanics.json)
CLASSIC_MASK_BITS = 32  # largeur des masques de races des sources Classic (Questie) : format, pas une valeur du jeu


@dataclass(frozen=True)
class RouteFilters:
    """Garde-fous de la route (`mechanics.json`, `route.filters`, CJ1) : catégories QuestSort écartées, catégories de
    métier, drapeaux de Questie, seuil des bas niveaux, capitales. Registre : I18"""

    excluded_sorts: frozenset[int]
    profession_sorts: Mapping[int, str]
    repeatable_flag: int
    event_flag: int
    low_level: int
    capitals: tuple[str, ...]


def route_filters(values: Any) -> RouteFilters | None:
    """Garde-fous lus dans les données (None : version sans `route.filters`). Registre : I18"""
    if FILTERS_KEY not in values:
        return None
    raw = values[FILTERS_KEY]["value"]
    return RouteFilters(
        excluded_sorts=frozenset(int(s) for s in raw["excluded_sorts"]),
        profession_sorts={int(k): str(v) for k, v in raw["profession_sorts"].items()},
        repeatable_flag=int(raw["repeatable_flag"]),
        event_flag=int(raw["event_flag"]),
        low_level=int(raw["low_level"]),
        capitals=tuple(str(c) for c in raw["capitals"]),
    )


def race_allowed(mask: Any, race_id: int, races: Mapping[str, Any]) -> bool:
    """Quête permise à la race `race_id` d'après son masque de races (0 ou absent : toutes). Une race au-delà des
    masques Classic (Skyborne) passe un masque qui couvre tout son camp ou qui porte un bit étendu des sources de
    Forever, jamais le masque d'autres races seulement. Registre : I18"""
    if not isinstance(mask, int) or mask == 0:
        return True
    if race_id <= CLASSIC_MASK_BITS:
        return bool(mask & (1 << (race_id - 1)))
    faction = next((str(r.get("faction", "")).lower() for r in races.values() if r.get("id") == race_id), "")
    classic = 0
    for r in races.values():
        if str(r.get("faction", "")).lower() == faction and int(r.get("id", 0)) <= CLASSIC_MASK_BITS:
            classic |= 1 << (int(r["id"]) - 1)
    return (mask >> CLASSIC_MASK_BITS) != 0 or (classic != 0 and mask & classic == classic)


def _races_doc(gd: GameData) -> dict[str, Any]:
    """Races de la version des données du paquet (repli quand l'appelant ne les donne pas)."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent / "data" / gd.game_version / "races.json"
    if not path.is_file():
        return {}
    races: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")).get("races") or {}
    return races


def done_quests(deps: Any, character: str | None) -> tuple[int, ...]:
    """Quêtes faites par ce personnage, lues au profil (Questie, par GUID) ; jamais l'union des personnages."""
    from forever.profile import character_values, load_profile, resolve_path

    if not character:
        return ()
    raw = (load_profile(resolve_path(deps)).get("characters") or {}).get(character)
    if not isinstance(raw, dict):
        return ()
    done = character_values(raw).get("quests_completed") or {}
    return tuple(sorted(int(q) for q in done if str(q).isdigit()))


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
    prof_visits: Any = None,
    races: Mapping[str, Any] | None = None,
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
    filters = route_filters(values)
    races = races if races is not None else (_races_doc(gd) if request.race else {})
    race_id = next((int(r["id"]) for name, r in races.items() if request.race and name == request.race), None)
    owned = {name.lower() for name, _, _ in request.professions}
    done = set(request.done)
    dropped: dict[str, list[int]] = {}
    quests: dict[int, Any] = {}
    for quest_id, q in sorted(book.quests.items()):
        forced = quest_id in request.include
        side, classes = value(q, "faction"), value(q, "classes")
        level, min_level = value(q, "level"), value(q, "min_level")
        reason = None
        if quest_id in done and not forced:
            continue  # déjà faite par ce personnage (profil) : jamais reprise
        if quest_id in request.exclude:
            reason = "exclues à la demande"
        elif race_id is not None and not race_allowed(value(q, "races"), race_id, races):
            continue  # autre race : rien à dire
        elif filters is not None and not forced and (why := _filtered(q, filters, owned)) is not None:
            reason = why
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
            class_quest=isinstance(classes, int) and classes != 0,
        )
    # quêtes dont un prérequis est hors de la route (ni dans la route, ni déjà faite) : jamais prenables
    changed = True
    while changed:
        changed = False
        for quest_id, rq in list(quests.items()):
            known = set(quests) | done
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
        prof_visits={
            name: (level, points)
            for name, (level, people) in (prof_visits or {}).items()
            if (points := _trainer_points(maps, people, request.faction))
        },
        train_levels=tuple(lv for lv in sorted(set(train_levels)) if request.start_level < lv < request.end_level),
        dropped={qid: reason for reason, ids in dropped.items() for qid in ids},
    )
    return world, warnings


def _filtered(quest: Any, filters: RouteFilters, owned: set[str]) -> str | None:
    """Raison d'écarter une quête d'après les garde-fous (CJ1) : catégorie d'événement ou d'effort de guerre, drapeaux
    répétable ou événement, quête de métier sans le métier (None : gardée). Registre : I18"""
    from forever.quests import value

    sort, special, skill = value(quest, "sort"), value(quest, "special"), value(quest, "skill")
    if isinstance(sort, int) and sort in filters.excluded_sorts:
        return "quêtes d'événement, d'effort de guerre ou de champ de bataille"
    if isinstance(special, int) and special & filters.event_flag:
        return "quêtes d'événement mensuel"
    if isinstance(special, int) and special & filters.repeatable_flag:
        return "quêtes répétables"
    if isinstance(sort, int) and sort in filters.profession_sorts:
        if filters.profession_sorts[sort].lower() not in owned:
            return "quêtes d'un métier que le personnage n'a pas"
    elif isinstance(skill, int) and not owned:
        return "quêtes d'un métier que le personnage n'a pas"
    return None


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
    if kind in ("grind", "train", "prof"):
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
    "prof": "train",
}
STEP_VERB = {
    "accept": "prends",
    "objective": "fais l'objectif de",
    "turnin": "rends",
    "dungeon": "fais",
    "dungeon_repeat": "refais",
    "train": "apprends tes nouveaux sorts chez",
    "prof": "apprends le rang suivant chez",
}


def _quest_value(quest: Any, name: str) -> Any:
    from forever.quests import value

    return value(quest, name)


def _stop_payload(book: Any, rows: dict[str, Any], r: Any, *, end_level: int) -> dict[str, Any]:
    place = _place_of(book, rows, r.kind, r.ref)
    if r.kind in ("dungeon", "dungeon_repeat"):
        name = (rows.get(str(r.ref)) or {}).get("name", str(r.ref))
    elif r.kind == "grind":
        name = None
    elif r.kind == "train":
        name = "ton maître de classe"
    elif r.kind == "prof":
        name = f"ton maître de {r.ref}"
    else:
        q = book.quests.get(r.ref)
        name = (q or {}).get("name") or f"la quête {r.ref}"
    classes = _quest_value(q, "classes") if r.kind in ("accept", "objective", "turnin") and q else None
    target = r.ref if r.kind == "grind" and isinstance(r.ref, int) else end_level  # farm du milieu d'une route
    text = (
        f"farme des monstres de ton niveau jusqu'au niveau {target}"
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
        **({"class_quest": True} if isinstance(classes, int) and classes else {}),  # CJ1 : résumé de la route
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


@dataclass
class RouteContext:
    """Ce qu'il faut pour calculer ou rejouer une route : données, monde du moteur, départ, sources lues."""

    cls: str
    data: Any
    cap: int
    gd: Any
    book: Any
    rows: list[dict[str, Any]]
    world: Any
    warnings: list[str]
    start: Any
    kill: Any
    walker: Any
    network: Any
    trainers: Any
    train_levels: Any


def _distance(a: Any, b: Any) -> float:
    if a is None or b is None or a.continent != b.continent:
        return math.inf
    return math.hypot(a.x - b.x, a.y - b.y)


def start_quest(quests: Any, level: int, *, near: Any = None) -> Any:
    """Quête dont le donneur sert de départ : permise au niveau de départ, au niveau le plus proche (RX1c : la quête de
    plus bas niveau du livre pouvait être une quête neutre de l'autre continent, et toute la route devenait infinie) ;
    à égalité, le donneur le plus proche de `near` (CJ1 : l'identifiant départageait, et un Gnome partait d'Elwynn
    Forest). Registre : I18"""
    return min(
        quests,
        key=lambda q: (q.min_level > level, abs(q.level - level), q.min_level, _distance(near, q.giver), q.id),
        default=None,
    )


def rxp_start_giver(library: Any, who: Any, quests: Any, level: int) -> Any:
    """Donneur de la première quête prise du parcours gratuit de la race et de la classe (zone de départ de la race,
    décision 277) au-delà du niveau `level` ; None sans parcours ou sans quête connue. Registre : I18"""
    from forever.errors import InvalidArgumentError
    from forever.rxp_guides import applies, guide_chain

    try:
        chain = guide_chain(library, who)
    except InvalidArgumentError:
        return None
    for g in chain.guides:
        if g.levels is not None and g.levels[1] <= level:
            continue
        for s in g.steps:
            if s.dungeon or not applies(s.filter, who):
                continue
            for a in s.actions:
                if a.kind == "accept" and a.ref in quests and applies(a.filter, who):
                    return quests[a.ref].giver
    return None


def reference_zones(library: Any, who: Any, quests: Any, *, below: int) -> frozenset[int]:
    """Zones (cartes des donneurs) des quêtes que le parcours gratuit de la race et de la classe prend dans ses guides
    qui commencent sous le niveau `below` (étapes et lignes filtrées pour le personnage, `#xprate` compris, étapes de
    donjon écartées) ; vide sans parcours. Registre : I18"""
    from forever.errors import InvalidArgumentError
    from forever.rxp_guides import applies, guide_chain, xp_rate_ok

    try:
        chain = guide_chain(library, who)
    except InvalidArgumentError:
        return frozenset()
    zones: set[int] = set()
    for g in chain.guides:
        if g.levels is not None and g.levels[0] >= below:
            continue
        for s in g.steps:
            if s.dungeon or s.hardcore or not applies(s.filter, who):
                continue
            if s.xp_rate is not None and applies(s.xp_rate[1], who) and not xp_rate_ok(s.xp_rate[0]):
                continue
            for a in s.actions:
                if a.kind == "accept" and a.ref in quests and applies(a.filter, who) and quests[a.ref].zone is not None:
                    zones.add(quests[a.ref].zone)
    return frozenset(zones)


def start_position(maps: Any, request: RouteRequest, quests: Any, *, rxp_giver: Any) -> tuple[Any, str]:
    """Départ d'une route et sa raison : la position réelle du contexte (`position`), sinon le premier donneur du
    parcours gratuit de la race (`parcours`), sinon le donneur d'une quête permise au niveau de départ (`quête`).
    Registre : I18"""
    near = None
    if request.start_at is not None:
        ui_map, x, y = request.start_at
        near = _point(maps, {"map": ui_map, "x": x, "y": y})
        if near is not None:
            return near, "position"
    if rxp_giver is not None:
        return rxp_giver, "parcours"
    first = start_quest(list(quests.values()), request.start_level, near=near)
    return (first.giver if first is not None else None), "quête"


START_ZONES_KEY = "route.start_zones"


def race_start_zone(values: Any, race: str | None) -> dict[str, Any] | None:
    """Zone de départ de la race (`{zone, subzone}`) lue dans la table des données (décision 283) ; None sans table
    ou sans race. Registre : I18"""
    if not race or START_ZONES_KEY not in values:
        return None
    entry = (values[START_ZONES_KEY]["value"] or {}).get(race)
    return {"zone": entry.get("zone"), "subzone": entry.get("subzone")} if isinstance(entry, dict) else None


def start_zone_map(values: Any, race: str | None, zone_names: Any) -> int | None:
    """Carte (uiMapID) de la zone de départ de la race, d'après les noms de zone du livre des quêtes. Registre : I18"""
    found = race_start_zone(values, race)
    if found is None:
        return None
    return next((int(m) for m, name in zone_names.items() if name == found["zone"]), None)


def start_giver_in_zone(quests: Any, ui_map: int | None, *, level: int) -> Any:
    """Donneur de départ supposé dans la zone de départ de la race : quête de cette zone permise au niveau, la plus
    basse d'abord ; None sans quête dans la zone. Registre : I18"""
    if ui_map is None:
        return None
    inside = [q for q in quests.values() if q.zone == ui_map and q.min_level <= level]
    inside.sort(key=lambda q: (q.level, q.min_level))
    return inside[0].giver if inside else None


START_REASONS = {
    "position": "départ : position du personnage dans le jeu",
    "parcours": "départ : zone de départ de la race (table des zones de départ ; premier donneur du parcours gratuit de "
    "RestedXP de sa race dans cette zone)",
    "quête": "départ supposé : donneur d'une quête permise au niveau de départ (position et race inconnues)",
}


def _race_reference(addons: Any, request: RouteRequest, quests: Any) -> tuple[Any, Any, Any]:
    """Donneur de départ pris du parcours gratuit de la race (lecture locale de RestedXP, décisions 277 et 278), avec
    la bibliothèque des parcours et les jetons du personnage ; (None, None, None) sans race ou sans RestedXP installé.
    Registre : I18"""
    from forever.errors import InvalidArgumentError
    from forever.rxp_guides import read_rxp_guides, who_for

    if not request.race or addons is None:
        return None, None, None
    try:
        library = read_rxp_guides(addons)
    except InvalidArgumentError:
        return None, None, None
    who = who_for(request.class_name, request.race, request.faction)
    giver = None if request.start_at is not None else rxp_start_giver(library, who, quests, request.start_level)
    return giver, library, who


def _replayed_zones(gd: Any, world: Any, library: Any, who: Any, start: Any, *, below: int, cap: int) -> frozenset[int]:
    """Zones des quêtes que le parcours gratuit de la race prend avant le niveau `below`, d'après son rejeu par nos
    règles depuis le même départ (un guide « 1-14 » finit ailleurs après le niveau 10). Registre : I18"""
    from forever.compare import replay_rxp
    from forever.errors import InvalidArgumentError
    from forever.rxp_guides import guide_chain

    try:
        chain = guide_chain(library, who)
    except InvalidArgumentError:
        return frozenset()
    replay = replay_rxp(gd, world, chain.guides, who, start, end_level=below, cap=cap)
    return frozenset(
        z
        for s in replay.stops
        if s.kind == "accept" and int(s.ref) in world.quests and (z := world.quests[int(s.ref)].zone) is not None
    )


def _map_of(maps: Any, point: Any) -> int | None:
    """Carte (uiMapID) qui contient un point du monde : la plus petite des cartes de son continent qui le couvrent."""
    if point is None:
        return None
    best: tuple[float, int] | None = None
    for ui_map, m in maps.items():
        if m.continent != point.continent:
            continue
        if min(m.min_x, m.max_x) <= point.x <= max(m.min_x, m.max_x) and min(m.min_y, m.max_y) <= point.y <= max(
            m.min_y, m.max_y
        ):
            area = abs(m.max_x - m.min_x) * abs(m.max_y - m.min_y)
            if best is None or area < best[0]:
                best = (area, ui_map)
    return best[1] if best else None


def route_context(deps: Any, request: RouteRequest, *, wow_dir: Any = None) -> RouteContext:
    """Monde de la route d'une demande : livre des quêtes, donjons placés, trajets (client, Journeys), maîtres de
    classe, temps par monstre, départ. Registre : I18"""

    from forever.engine.route import RouteState
    from forever.engine.travel import travel_params, travel_time
    from forever.errors import InvalidArgumentError
    from forever.gamedata import MECHANICS_FILE, build_game_data
    from forever.kill_time import kill_params, kill_time, load_kill_times
    from forever.leveling import check_level, level_cap
    from forever.pipeline.questie import CLASS_IDS, CLASS_MASKS
    from forever.pipeline.travel_sources import (
        read_journeys_network,
        read_journeys_walks,
        read_profession_data,
        read_questie_trainers,
        read_training_levels,
    )
    from forever.quests import build_quests
    from forever.sim.objectives import MAGE
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
        """Temps par monstre : relevés du joueur d'abord ; à défaut, moteur du Mage (combat, repos, course), sinon
        estimation (combat seul, sous-estime la durée)."""
        if level not in kill_memo:
            found = kill_time(kp, class_name=cls, level=level, measures=measures, camp=True)
            if cls == MAGE and found.source != "measured":
                from forever.sim.objectives import _engine_kill_time

                try:
                    engine = _engine_kill_time(deps, level, None)
                except InvalidArgumentError:  # niveau sans rotation du moteur (premiers niveaux) : estimation gardée
                    kill_memo[level] = found
                    return found
                found = found._replace(
                    source="engine", seconds=engine["seconds"], low=engine["low"], high=engine["high"],
                    certainty=engine["certainty"], method=engine["method"], scope="total",
                )  # fmt: skip
            kill_memo[level] = found
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
    prof_visits = (
        profession_visits(
            read_profession_data(addons),
            {name: (rank, cap) for name, rank, cap in request.professions},
            faction=request.faction,
            start_level=request.start_level,
            end_level=request.end_level,
        )
        if addons and request.professions
        else {}
    )

    rows: list[dict[str, Any]] = []
    if request.dungeons != "none":
        rows = dungeon_placements(
            deps, class_name=cls, faction=request.faction, wow_dir=wow_dir, below=request.end_level
        )
    races = data.read_json("races.json").get("races") or {}
    if request.race and request.race not in races:
        raise InvalidArgumentError(f"Race inconnue : {request.race}.", f"choisir parmi : {', '.join(races)}")
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
        prof_visits=prof_visits,
        races=races,
    )
    if not world.quests:
        warnings.append("aucune quête placée : la route n'est que du farm")
    filters = route_filters(values)
    low = filters.low_level if filters is not None and request.start_level < filters.low_level else None
    giver, library, who = _race_reference(addons, request, world.quests)
    zone_map = start_zone_map(values, request.race, book.zone_names)  # décision 283 : table des zones de départ
    if zone_map is not None and request.start_at is None:
        giver_zone = next((q.zone for q in world.quests.values() if q.giver == giver), None)
        if giver is None or giver_zone != zone_map:  # jamais un départ supposé hors de la zone de départ de la race
            giver = start_giver_in_zone(world.quests, zone_map, level=request.start_level) or giver
    position, reason = start_position(maps, request, world.quests, rxp_giver=giver)
    if position is None:
        position = next(iter(maps.values()), None)
        position = position and _point(maps, {"map": position.ui_map, "x": 50.0, "y": 50.0})
    warnings.insert(0, START_REASONS[reason])
    if low is not None and request.race:
        here = request.start_at[0] if request.start_at is not None else _map_of(maps, position)
        start_zone = zone_map or next((q.zone for q in world.quests.values() if q.giver == position), None) or here
        first = RouteState(level=request.start_level, xp=0.0, position=position, done=frozenset(request.done))
        zones = (
            _replayed_zones(gd, world, library, who, first, below=low, cap=cap) if library is not None else frozenset()
        )
        allowed = frozenset(z for z in (*zones, start_zone) if z is not None)
        if allowed:
            world = replace(world, early_zones=allowed, early_level=low)
            names = ", ".join(sorted(str(book.zone_names.get(z) or z) for z in allowed))
            warnings.insert(
                1,
                f"zone de départ d'abord : jusqu'au niveau {low}, quêtes de {names} seulement (hors classe et donjon)",
            )
    done = frozenset(request.done)
    start = RouteState(level=request.start_level, xp=0.0, position=position, done=done)
    return RouteContext(
        cls, data, cap, gd, book, rows, world, warnings, start, kill, walker, network, trainers, train_levels
    )


def plan_route(deps: Any, request: RouteRequest, *, wow_dir: Any = None) -> dict[str, Any]:
    """Feuille de route calculée, gardée dans le cache, avec sa provenance (`forever route plan`). Registre : I18"""
    import hashlib
    import json
    from dataclasses import asdict

    from forever.freshness import freshness_for_version
    from forever.optimize.route import plan
    from forever.provenance import make_provenance

    if request.character and not request.done:
        request = replace(request, done=done_quests(deps, request.character))
    ctx = route_context(deps, request, wow_dir=wow_dir)
    cls, data, cap, gd, book, rows = ctx.cls, ctx.data, ctx.cap, ctx.gd, ctx.book, ctx.rows
    world, warnings, start, kill, walker, network = (
        ctx.world,
        ctx.warnings,
        ctx.start,
        ctx.kill,
        ctx.walker,
        ctx.network,
    )
    trainers, train_levels = ctx.trainers, ctx.train_levels
    found = plan(gd, world, start, end_level=request.end_level, cap=cap, tries=request.tries, seed=request.seed)
    from forever.compare import delivered_route

    result, basis = delivered_route(deps, ctx, request, found, wow_dir=wow_dir)
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
        f"temps par monstre : {k.source} ({k.method}, {k.certainty}) ; durée : "
        + ("combat, récupération et déplacement" if k.scope == "total" else "combat seul (sous-estime la route)"),
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
        (
            f"quêtes déjà faites par {request.character} (profil, Questie) : {len(request.done)} retirée(s)"
            if request.character
            else "quêtes déjà faites : personnage inconnu, aucune retirée"
        ),
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
        "basis": basis,
        "provenance": provenance,
    }
    path = deps.cache_dir / ROUTES_DIR / f"{plan_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")  # écriture atomique : le pont peut lire le plan au même moment
    tmp.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    tmp.replace(path)
    return payload


def guide_name(plan: Any) -> str:
    """Nom stable du guide RestedXP d'un plan (CJ1, bloc 2) : « Forever · <personnage> · a-b », la classe à défaut du
    personnage ; le même nom pour le même personnage et les mêmes niveaux, d'une livraison à l'autre."""
    lv = plan["levels"]
    request = plan.get("request") or {}
    who = str(request.get("character") or "") or str(plan.get("class", "")).capitalize()
    if request.get("purpose"):  # bloc 4d : « Forever · Go · équipement », remplacée à chaque livraison
        return f"Forever · {who} · {request['purpose']}"
    return f"Forever · {who} · {lv['from']}-{lv['to']}"


def load_plan(deps: Any, plan_id: str) -> dict[str, Any]:
    """Plan gardé dans le cache (`forever route show`)."""
    import json

    from forever.errors import InvalidArgumentError

    path = deps.cache_dir / ROUTES_DIR / f"{plan_id}.json"
    if not plan_id.isalnum() or not path.is_file():
        raise InvalidArgumentError(f"Feuille de route inconnue : {plan_id}.", "lancer forever route plan")
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


PREVIEW_FIELDS = ("id", "levels", "hours", "xp_h", "dungeons", "rewards", "bonuses", "certainty", "stops", "basis")


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
        "basis": {k: (plan.get("basis") or {}).get(k) for k in ("kind", "verdict", "guides")},
    }


FIRST_STOPS = 5  # arrêts montrés dans le résumé (réglage de présentation)
SUMMARY_WARNINGS = 5
SUMMARY_REQUEST = (
    "class_name",
    "faction",
    "start_level",
    "end_level",
    "race",
    "character",
    "dungeons",
    "class_quests",
    "purpose",
)


def route_summary(plan: Any) -> dict[str, Any]:
    """Résumé compact d'un plan pour la conversation (essai CJ-6 du 2026-10-15 : le plan complet, guide RestedXP
    compris, dépassait ce qu'un résultat d'outil peut porter) : aperçu, zones dans l'ordre de première visite, donjons,
    quêtes de classe, récompenses notables, cinq premiers arrêts, base utilisée sans le texte du guide, quelques
    avertissements, provenance ; la route complète reste sur le disque (`<cache>/routes/<id>.json`) pour la
    livraison et `forever_route(action="show", detail=True)`."""
    stops = list(plan.get("stops") or [])
    zones: list[str] = []
    for stop in stops:
        zone = stop.get("zone")
        if zone and zone not in zones:
            zones.append(zone)
    class_quests: list[str] = []
    for stop in stops:
        if stop.get("class_quest") and stop.get("kind") == "accept" and stop.get("name") not in class_quests:
            class_quests.append(stop["name"])
    preview = route_preview(plan)
    dungeons: list[dict[str, Any]] = []  # un donjon une fois, à son premier passage
    for d in preview["dungeons"]:
        if all(d["name"] != seen["name"] for seen in dungeons):
            dungeons.append(d)
    basis = plan.get("basis") or {}
    request = plan.get("request") or {}
    warnings = list(plan.get("warnings") or [])
    return {
        "id": plan["id"],
        "name": guide_name(plan),
        "class": plan.get("class"),
        "faction": plan.get("faction"),
        "levels": plan.get("levels"),
        "feasible": plan.get("feasible"),
        "hours": plan.get("hours"),
        "xp_h": plan.get("xp_h"),
        "certainty": plan.get("certainty"),
        "zones": zones,
        "dungeons": dungeons,
        "class_quests": class_quests,
        "rewards": list(plan.get("rewards") or []),
        "first_stops": [
            {k: s.get(k) for k in ("kind", "text", "zone", "x", "y", "level")} for s in stops[:FIRST_STOPS]
        ],
        "stops_total": len(stops),
        "basis": {k: basis.get(k) for k in ("kind", "verdict", "guides", "attribution") if k in basis},
        "warnings": warnings[:SUMMARY_WARNINGS],
        "warnings_total": len(warnings),
        "request": {k: request[k] for k in SUMMARY_REQUEST if k in request},
        "full_route": "route complète sur le disque (plan id), livrée par « Valider et livrer » ; détail : "
        'forever_route(action="show", plan_id, detail=True)',
        "preview": preview,
        "provenance": plan.get("provenance"),
    }


def profession_visits(
    data: Any, professions: Any, *, faction: str, start_level: int, end_level: int
) -> dict[str, tuple[int, list[Any]]]:
    """RX1, bloc H : métiers dont le rang suivant est ouvert (compétence actuelle au moins celle du rang, plafond
    actuel sous le sien) et dont le niveau requis tombe dans la route : niveau de la visite et maîtres du camp.
    `professions` : nom -> (rang, rang maximal). La montée de compétence n'est pas simulée (MT1). Registre : I18"""
    side = {"horde": "H", "alliance": "A"}.get(faction, "")
    out: dict[str, tuple[int, list[Any]]] = {}
    for name, (rank, cap) in sorted(professions.items()):
        prof = data.get(name)
        if prof is None:
            continue
        nxt = next((r for r in sorted(prof.ranks, key=lambda r: r.cap) if r.cap > cap and r.skill <= rank), None)
        if nxt is None:
            continue
        level = max(start_level, nxt.level or start_level)
        trainers = [t for t in prof.trainers if side in t.sides]
        if level < end_level and trainers:
            out[name] = (level, trainers)
    return out


def parse_professions(raw: Any) -> tuple[tuple[str, int, int], ...]:
    """Métiers « Nom:rang:rang maximal » (CLI, outil MCP) -> (nom, rang, rang maximal)."""
    from forever.errors import InvalidArgumentError

    out = []
    for item in raw:
        name, sep, rest = item.rpartition(":")
        head, sep2, cap = name.rpartition(":")
        if not (sep and sep2 and head.strip() and rest.isdigit() and cap.isdigit()):
            raise InvalidArgumentError(
                f"Métier illisible : {item}.", "donner « Nom:rang:rang maximal », rangs lus en jeu"
            )
        out.append((head.strip(), int(cap), int(rest)))
    return tuple(out)
