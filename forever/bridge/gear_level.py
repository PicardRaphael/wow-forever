"""Réponse du bouton « Mon équipement à ce niveau » de l'écran Équipement (essai CJ-6 du 2026-10-15), rédigée par le
pont sans le modèle : un seul appel de `gear_report(action="leveling")` au niveau demandé, avec la classe, la race, le
camp et les métiers du contexte, et un texte fait de sa seule sortie (le modèle mêlait la route d'équipement de la liste
BiS, sans niveau). Aucun chiffre de jeu ici : tout vient du résultat de l'outil."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.gear import gear_report

SET_ASIDE_SHOWN = 6  # objets mis à part montrés (réglage de présentation)


def _professions(context: Mapping[str, str]) -> list[str]:
    """Métiers du contexte (« nom:rang:rang maximal », séparés par des virgules, Message.lua), noms seuls."""
    raw = str(context.get("professions") or "")
    return [part.split(":", 1)[0].strip() for part in raw.split(",") if part.split(":", 1)[0].strip()]


def _leveling(deps: Any, context: Mapping[str, str], level: int) -> dict[str, Any]:
    """Un seul appel de l'outil : équipement obtenable au niveau `level` pour le personnage du contexte."""
    return gear_report(
        deps,
        "leveling",
        class_name=str(context.get("class") or "Mage"),
        level=level,
        race=str(context.get("race") or "Orc"),
        faction=str(context.get("faction") or "").lower() or None,
        professions=_professions(context),
    )


def _tail(doc: Mapping[str, Any], level: int) -> list[str]:
    lines = []
    aside = doc.get("set_aside") or []
    if aside:
        shown = ", ".join(f"{a['name'] or a['item']} ({a['reason']})" for a in aside[:SET_ASIDE_SHOWN])
        more = f" et {len(aside) - SET_ASIDE_SHOWN} autre(s)" if len(aside) > SET_ASIDE_SHOWN else ""
        lines.append(f"Mis à part, source ou niveau inconnus : {shown}{more}.")
    if doc.get("excluded"):
        lines.append(f"Écartés car pas obtenables au niveau {level} : {len(doc['excluded'])} objet(s).")
    if not doc.get("professions"):
        lines.append("Objets de métier : aucun, pas de métier dans ton profil.")
    prov = doc.get("provenance") or {}
    lines.append(f"Provenance : données {prov.get('game_version', '?')} · certitude {prov.get('certainty', '?')}.")
    return lines


def gear_route_reply(deps: Any, context: Mapping[str, str], level: int) -> str:
    """« En faire une route » (bloc 4c) : les objets obtenables au niveau `level` (la même sortie que
    `gear_level_reply`), regroupés par origine : donjons avec leurs passages attendus (taux du livre des donjons),
    quêtes par zone, autres origines ; l'ordre par l'optimiseur de trajets et la livraison dans RestedXP viennent au
    bloc 4d."""
    from forever.dungeons import build_dungeons, where_item
    from forever.gear_route import plan_gear_route

    doc = _leveling(deps, context, level)
    if "picks" not in doc:
        return f"Route d'équipement au niveau {level} : {doc.get('error') or doc.get('message') or 'non calculée'}"
    dungeons = build_dungeons(deps)
    items = []
    names = {}
    for p in doc["picks"]:
        names[p["item"]] = p["name"] or str(p["item"])
        drops = [d for d in where_item(dungeons, p["item"])] if p.get("source") in ("boss_drop", "raid_trash") else []
        if drops:
            best = max(drops, key=lambda d: d["rate"] if isinstance(d.get("rate"), int | float) else -1)
            rate = best["rate"] if isinstance(best.get("rate"), int | float) else None
            source = {"kind": "donjon", **best, "rate": rate}
        elif p.get("quest"):
            source = {"kind": "quête", "quest": p["quest"], "zone": p.get("zone")}
        else:
            where = f", {p['zone']}" if p.get("zone") else ""
            source = {"kind": "autre", "text": f"{p.get('access') or p.get('source') or '?'}{where}"}
        items.append({"slot": p["slot"], "item": p["item"], "sources": [source]})
    plan = plan_gear_route(items)
    lines = [f"## Route d'équipement au niveau {level} (objets obtenables à ce niveau, GearQuest Forever)"]
    for d in plan["dungeons"]:
        objects = ", ".join(names[i] for i in d["items"])
        if d["expected_runs"] is None:
            lines.append(f"- Donjon {d['name']} : {objects} ; taux inconnu, passages non chiffrés")
        else:
            lines.append(
                f"- Donjon {d['name']} : {objects} ; environ {d['expected_runs']:.1f} passage(s) en moyenne, "
                f"{d['runs_for_chance']} pour 9 chances sur 10"
            )
    for z in plan["quests"]:
        quests = ", ".join(f"{q} ({', '.join(names[i] for i, s in _quest_items(items, q))})" for q in z["quests"])
        lines.append(f"- Quêtes en {z['zone']} : {quests}")
    for o in plan["others"]:
        lines.append(f"- {names[o['item']]} : {o['text']}")
    if not doc["picks"]:
        lines.append("- Aucun objet de GearQuest Forever obtenable à ce niveau pour ta classe et ton camp.")
    lines.append("Ordre par l'optimiseur de trajets et livraison dans RestedXP : bloc 4d.")
    return "\n".join(lines + _tail(doc, level))


def _quest_items(items: list[dict[str, Any]], quest: Any) -> list[tuple[int, Any]]:
    return [(i["item"], s) for i in items for s in i["sources"] if s.get("kind") == "quête" and s.get("quest") == quest]


def gear_level_reply(deps: Any, context: Mapping[str, str], level: int) -> str:
    """Texte de la réponse : un objet par emplacement (nom, niveau requis, comment l'obtenir, zone), objets mis à
    part (source ou niveau inconnus), nombre d'objets écartés, provenance."""
    doc = _leveling(deps, context, level)
    if "picks" not in doc:  # erreur de l'outil : son message tel quel
        return f"Équipement au niveau {level} : {doc.get('error') or doc.get('message') or 'non calculé'}"
    lines = [f"## Équipement au niveau {level} (GearQuest Forever, objets obtenables à ce niveau)"]
    for p in doc["picks"]:
        how = p.get("access") or p.get("source") or "?"
        zone = f", {p['zone']}" if p.get("zone") else ""
        lines.append(f"- {p['slot']} : {p['name'] or p['item']} (niveau requis {p['required_level']} ; {how}{zone})")
    if not doc["picks"]:
        lines.append("- Aucun objet de GearQuest Forever obtenable à ce niveau pour ta classe et ton camp.")
    return "\n".join(lines + _tail(doc, level))
