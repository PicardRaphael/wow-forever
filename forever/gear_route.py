"""Route d'équipement (CJ1, bloc 4b, décision 277, point 6) : pour les objets de la liste BiS personnelle (bloc 4),
leur origine lue dans ce que les sources savent déjà (DJ1 : boss et taux de Naowh, Forever Guide, AtlasLoot ; quêtes
du livre : récompenses de Forever Guide et de GearQuest ; sinon le lieu de Naowh : métier, réputation, marchand),
puis une route regroupée : donjons (objets cumulés, passages attendus et pour neuf chances sur dix), quêtes par zone,
autres origines. Rien recalculé des addons, écarts de taux gardés tels que DJ1 les rend."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from forever.engine.loot import expected_runs, runs_for_chance

CHANCE = 0.9  # « neuf chances sur dix » : seuil affiché au joueur (réglage de présentation)


def item_sources(
    item: int,
    where: Callable[[int], list[dict[str, Any]]],
    quests_for: Callable[[int], list[int]],
    naowh: Mapping[int, str],
) -> list[dict[str, Any]]:
    """Origines d'un objet, dans l'ordre : boss de donjon (avec taux), quête qui le donne, lieu dit par Naowh Forever,
    sinon « inconnue »."""
    found_drops = where(item)
    drops = [{"kind": "donjon", **d} for d in found_drops if isinstance(d.get("rate"), int | float)]
    if drops:
        return sorted(drops, key=lambda d: -float(d["rate"]))
    if found_drops:  # boss connu, taux inconnu des sources : donjon gardé, passages non chiffrés
        return [{"kind": "donjon", **found_drops[0], "rate": None}]
    found = quests_for(item)
    if found:
        return [{"kind": "quête", "quest": q} for q in found]
    if item in naowh:
        return [{"kind": "autre", "text": naowh[item]}]
    return [{"kind": "inconnue"}]


def plan_gear_route(items: Sequence[Mapping[str, Any]], *, chance: float = CHANCE) -> dict[str, Any]:
    """Route regroupée : donjons (meilleure source de chaque objet, objets d'un même donjon cumulés ; les donjons qui
    donnent le plus d'objets d'abord, puis le moins de passages), quêtes par zone, autres origines, objets sans origine.
    Registre : I16"""
    dungeons: dict[str, dict[str, Any]] = {}
    zones: dict[str, dict[str, Any]] = {}
    others: list[dict[str, Any]] = []
    unknown: list[int] = []
    for entry in items:
        item, sources = int(entry["item"]), list(entry.get("sources") or [])
        best = sources[0] if sources else {"kind": "inconnue"}
        if best["kind"] == "donjon":
            d = dungeons.setdefault(
                str(best["dungeon"]), {"dungeon": str(best["dungeon"]), "name": best.get("dungeon_name"), "items": [],
                                       "rates": [], "bosses": []},
            )  # fmt: skip
            d["items"].append(item)
            d["rates"].append(float(best["rate"]) if isinstance(best.get("rate"), int | float) else None)
            if best.get("boss") and best["boss"] not in d["bosses"]:
                d["bosses"].append(best["boss"])
        elif best["kind"] == "quête":
            zone = str(best.get("zone") or "zone inconnue")
            z = zones.setdefault(zone, {"zone": zone, "quests": [], "items": []})
            if best["quest"] not in z["quests"]:
                z["quests"].append(best["quest"])
            z["items"].append(item)
        elif best["kind"] == "autre":
            others.append({"item": item, "text": best.get("text")})
        else:
            unknown.append(item)
    ordered = []
    for d in dungeons.values():
        rates = d.pop("rates")
        if any(r is None for r in rates):  # taux inconnu d'au moins un objet : passages non chiffrés
            ordered.append({**d, "expected_runs": None, "runs_for_chance": None, "rate_unknown": True})
            continue
        ordered.append({**d, "expected_runs": expected_runs(rates), "runs_for_chance": runs_for_chance(rates, chance)})
    ordered.sort(key=lambda d: (-len(d["items"]), d["expected_runs"] if d["expected_runs"] is not None else math.inf))
    return {"dungeons": ordered, "quests": list(zones.values()), "others": others, "unknown": unknown}


def quest_index(book: Any) -> dict[int, list[int]]:
    """Objet -> quêtes qui le donnent (récompenses et choix du livre des quêtes)."""
    from forever.quests import value

    out: dict[int, list[int]] = {}
    for quest_id, q in book.quests.items():
        rewards = value(q, "rewards")
        if not isinstance(rewards, dict):
            continue
        items = [r.get("item") for r in rewards.get("items") or [] if isinstance(r, dict)]
        items += [c for c in rewards.get("choices") or [] if isinstance(c, int)]
        for item in items:
            if isinstance(item, int):
                out.setdefault(item, []).append(int(quest_id))
    return out


def gear_route(deps: Any, addons: Any, bis: Mapping[str, Any], *, chance: float = CHANCE) -> dict[str, Any]:
    """Route d'équipement des objets choisis d'une liste BiS personnelle (`personal_bis`) : origines (DJ1, livre des
    quêtes, Naowh) et route regroupée. Registre : I16"""
    from forever.dungeons import build_dungeons, where_item
    from forever.pipeline.gear_sources import read_naowh_bis
    from forever.quests import build_quests, value

    dungeons = build_dungeons(deps)
    quests = build_quests(deps)
    by_item = quest_index(quests)
    _, naowh = read_naowh_bis(addons)

    def zone_of(quest_id: int) -> str | None:
        if quest_id not in quests.quests:
            return None
        q = quests.quests[quest_id]
        giver = value(q, "giver")
        ui_map = giver.get("map") if isinstance(giver, dict) and giver.get("map") is not None else value(q, "map")
        return quests.zone_names.get(ui_map) if ui_map is not None else None

    items = []
    for row in bis["items"]:
        if not row.get("chosen"):
            continue
        sources = item_sources(int(row["item"]), lambda i: where_item(dungeons, i), lambda i: by_item.get(i, []), naowh)
        for s in sources:
            if s["kind"] == "quête":
                s["zone"] = zone_of(int(s["quest"]))
        items.append({"slot": row["slot"], "item": row["item"], "sources": sources})
    return {"items": items, **plan_gear_route(items, chance=chance)}
