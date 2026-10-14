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

KINDS = ("goto", "accept", "turnin", "click", "use_item", "note")
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
        row: dict[str, Any] = {"id": key, "name": d["name"], "levels": rng, "placement": None, "steps": []}
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
) -> tuple[Any, list[str]]:
    """Entrées du moteur de route (`RouteWorld`) tirées du livre des quêtes, des placements de donjon de DJ1 et des
    cartes de zone ; avertissements (quêtes écartées et pourquoi). Registre : I18"""
    raise NotImplementedError


def plan_route(deps: Any, request: RouteRequest, *, wow_dir: Any = None) -> dict[str, Any]:
    """Feuille de route calculée, gardée dans le cache, avec sa provenance (`forever route plan`). Registre : I18"""
    raise NotImplementedError


def load_plan(deps: Any, plan_id: str) -> dict[str, Any]:
    """Plan gardé dans le cache (`forever route show`)."""
    raise NotImplementedError
