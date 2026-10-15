"""Réponses des boutons de l'écran Équipement (essai CJ-6 du 2026-10-15, bloc 4c), rédigées par le pont sans le
modèle : un seul appel de `gear_report(action="leveling")` au niveau demandé, avec la classe, la race, le camp et les
métiers du contexte, et un texte fait de sa seule sortie (le modèle mêlait la route d'équipement de la liste BiS, sans
niveau). Chaque objet est une balise `[[item:<id>:<qualité>|<nom>]]` que l'addon rend en lien d'objet du jeu ; la
réponse remet les liens à copier ([Naowh : BiS] de ce niveau, [Naowh : poids] et [Forever Companion : échelle] pour le
Mage). Aucun chiffre de jeu ici : tout vient du résultat de l'outil."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.gear import gear_report

SET_ASIDE_SHOWN = 6  # objets mis à part montrés (réglage de présentation)

# Emplacements de GearQuest Forever -> français, et emplacements d'inventaire de l'export Naowh (ordre de repli).
SLOTS_FR = {
    "Head": "Tête", "Neck": "Cou", "Shoulder": "Épaules", "Back": "Dos", "Chest": "Torse", "Shirt": "Chemise",
    "Tabard": "Tabard", "Wrist": "Poignets", "Hands": "Mains", "Waist": "Taille", "Legs": "Jambes", "Feet": "Pieds",
    "Finger": "Doigt", "Trinket": "Bijou", "MainHand": "Main droite", "OneHand": "Une main", "TwoHand": "Deux mains",
    "SecondaryHand": "Main gauche", "OffHand": "Main gauche", "Ranged": "Distance",
}  # fmt: skip
INVENTORY = {
    "Head": (1,), "Neck": (2,), "Shoulder": (3,), "Chest": (5,), "Waist": (6,), "Legs": (7,), "Feet": (8,),
    "Wrist": (9,), "Hands": (10,), "Finger": (11, 12), "Trinket": (13, 14), "Back": (15,), "MainHand": (16,),
    "OneHand": (16,), "TwoHand": (16,), "SecondaryHand": (17,), "OffHand": (17,), "Ranged": (18,),
}  # fmt: skip
RANDOM_DROP = ("world_drop",)  # butin aléatoire : après les objets qu'on peut viser exprès


def _professions(context: Mapping[str, str]) -> list[str]:
    """Métiers du contexte (« nom:rang:rang maximal », séparés par des virgules, Message.lua), noms seuls."""
    raw = str(context.get("professions") or "")
    return [part.split(":", 1)[0].strip() for part in raw.split(",") if part.split(":", 1)[0].strip()]


def _race(deps: Any, context: Mapping[str, str]) -> str:
    """Nom de race de `races.json` pour la race envoyée par le jeu (nom ou fichier du client), Orc à défaut."""
    from forever.store import load_version

    races = load_version(deps).read_json("races.json").get("races") or {}
    sent = str(context.get("race") or "")
    return next((n for n, r in races.items() if sent in (n, r.get("client_file"))), "Orc")


def _talents(deps: Any, context: Mapping[str, str]) -> dict[str, Any]:
    """Mes talents lus en jeu (contexte relié à nos données) et mon niveau : poids avec mes vrais talents à mon
    niveau, avec mon plan de talents ailleurs (décision 282)."""
    from forever.bridge.context import load_context_data, resolve

    try:
        resolved = resolve(load_context_data(deps), context)
    except Exception:  # noqa: BLE001 : contexte illisible : plan de talents seul
        return {}
    if resolved.level is None or resolved.current is None:
        return {}
    return {"talents": dict(resolved.current), "talents_level": resolved.level}


def _leveling(deps: Any, context: Mapping[str, str], level: int, to_level: int | None = None) -> dict[str, Any]:
    """Un seul appel de l'outil : équipement obtenable au niveau `level` (ou de `level` à `to_level`) pour le
    personnage du contexte."""
    who = str(context.get("name") or "Mage")
    span = f"niveaux {level}-{to_level}" if to_level else f"niveau {level}"
    return gear_report(
        deps,
        "leveling",
        class_name=str(context.get("class") or "Mage"),
        level=level,
        race=_race(deps, context),
        faction=str(context.get("faction") or "").lower() or None,
        professions=_professions(context),
        name=f"Forever · {who} · {span}",
        to_level=to_level,
        **_talents(deps, context),
    )


def item_tag(item: int, quality: Any, name: Any) -> str:
    """Balise d'objet rendue en lien du jeu par ForeverBridge (`FB.FormatLine`)."""
    label = str(name or item).replace("]]", "] ]").replace("|", "/")
    return f"[[item:{int(item)}:{quality if isinstance(quality, int) else 1}|{label}]]"


def _how(p: Mapping[str, Any]) -> str:
    """Comment l'obtenir : butin aléatoire dit comme tel, sans zone ; sinon l'accès et la zone."""
    if p.get("source") in RANDOM_DROP and p.get("drop_levels"):
        low, high = p["drop_levels"]
        return f"butin aléatoire des monstres de niveau {low} à {high}, n'importe où"
    zone = f", {p['zone']}" if p.get("zone") else ""
    detour = f" ; détour : {p['detour']}, hors de ta route" if p.get("detour") else ""
    return f"{p.get('access') or p.get('source') or '?'}{zone}{detour}"


def _ordered(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Objets qu'on peut viser exprès d'abord, butin aléatoire ensuite (tri stable)."""
    return sorted(picks, key=lambda p: p.get("source") in RANDOM_DROP)


def _why(p: Mapping[str, Any], level: int) -> str:
    g = p.get("gearquest_choice")
    if not g:
        return ""
    theirs = g.get("score") if g.get("score") is not None else "inconnu"
    return (
        f" ; GearQuest proposait {item_tag(g['item'], g.get('quality'), g.get('name'))} : nos poids du Mage au niveau "
        f"{level} le placent derrière (score {theirs} contre {p.get('score')})"
    )


def _links(
    doc: Mapping[str, Any], context: Mapping[str, str], level: int, deps: Any, span: str | None = None
) -> tuple[list[str], list[dict[str, str]]]:
    """Liens à copier : [Naowh : BiS] de la liste de ce niveau, poids et échelle du Mage."""
    from forever.bridge.exports import WHERE, typed_link
    from forever.exports.naowh import naowh_bis
    from forever.gear import DEFAULT_SPECS
    from forever.pipeline.gear_sources import read_naowh_bis

    lines: list[str] = []
    links: list[dict[str, str]] = []
    token = str(context.get("class") or "").upper()
    if doc.get("naowh") and doc.get("pawn"):
        links += [typed_link("naowh_weights", doc["naowh"]), typed_link("companion_scale", doc["pawn"])]
        lines.append(
            f"Poids du Mage au niveau {level} : [Naowh : poids] dans {WHERE['naowh_weights']} ; "
            f"[Forever Companion : échelle] dans {WHERE['companion_scale']}."
        )
    keys: list[str] = []
    if deps.wow_dir is not None:
        lists, _ = read_naowh_bis(deps.wow_dir / "Interface" / "AddOns")
        keys = [k for k, s in lists.items() if s.class_token == token]
    spec = DEFAULT_SPECS.get(token) or (keys[0] if keys else None)
    chosen: dict[int, int] = {}
    extra: dict[int, list[int]] = {}
    segments = doc.get("segments") or []
    finals = [s for s in segments if s["to"] == doc.get("to_level")] if segments else doc["picks"]
    for p in finals:  # tranche : objet du haut de la tranche, les précédents en repli dans l'ordre inverse
        free = [s for s in INVENTORY.get(p["slot"], ()) if s not in chosen]
        if free:
            chosen[free[0]] = int(p["item"])
            earlier = [int(s["item"]) for s in reversed(segments) if s["slot"] == p["slot"] and s["item"] != p["item"]]
            if earlier:
                extra[free[0]] = list(dict.fromkeys(earlier))
    if spec and chosen:
        who = str(context.get("name") or "Mage")
        label = span or f"niveau {level}"
        export = naowh_bis(f"Forever · {who} · {label}", spec, chosen, extra)
        links.append(typed_link("naowh_bis", export))
        lines.append(f"Cette liste ({label}) : [Naowh : BiS] dans {WHERE['naowh_bis']}.")
    return lines, links


def _tail(doc: Mapping[str, Any], level: int) -> list[str]:
    lines = list(doc.get("weights_notes") or [])  # sort pas encore appris, ordre de GearQuest, niveau manquant
    aside = doc.get("set_aside") or []
    if aside:
        shown = ", ".join(
            f"{item_tag(a['item'], None, a.get('name'))} ({a['reason']})" for a in aside[:SET_ASIDE_SHOWN]
        )
        more = f" et {len(aside) - SET_ASIDE_SHOWN} autre(s)" if len(aside) > SET_ASIDE_SHOWN else ""
        lines.append(f"Mis à part, source ou niveau inconnus : {shown}{more}.")
    if doc.get("excluded"):
        lines.append(f"Écartés car pas obtenables au niveau {level} : {len(doc['excluded'])} objet(s).")
    if not doc.get("professions"):
        lines.append("Objets de métier : aucun, pas de métier dans ton profil.")
    prov = doc.get("provenance") or {}
    lines.append(f"Provenance : données {prov.get('game_version', '?')} · certitude {prov.get('certainty', '?')}.")
    return lines


def _span(low: int, high: int) -> str:
    return f"niveau {low}" if low == high else f"niveaux {low} à {high}"


def _range_reply(deps: Any, context: Mapping[str, str], low: int, high: int) -> tuple[str, list[dict[str, str]]]:
    """Tranche de niveaux (bloc 4c) : une ligne par emplacement, un segment par palier où l'objet visé change."""
    doc = _leveling(deps, context, low, high)
    if "segments" not in doc:
        return (
            f"Équipement du niveau {low} au niveau {high} : {doc.get('error') or doc.get('message') or 'non calculé'}",
            [],
        )
    lines = [f"## Équipement du niveau {low} au niveau {high} (GearQuest Forever, objets obtenables à chaque niveau)"]
    by_slot: dict[str, list[dict[str, Any]]] = {}
    for s in sorted(doc["segments"], key=lambda s: s["from"]):
        by_slot.setdefault(s["slot"], []).append(s)
    lines.append(_summary(list({s["item"]: s for s in doc["segments"]}.values())))
    order = sorted(by_slot, key=lambda slot: all(s.get("source") in RANDOM_DROP for s in by_slot[slot]))
    for slot in order:  # décision 282 : titre de l'emplacement, puis un objet par ligne, du plus tôt au plus tard
        lines.append(f"- {SLOTS_FR.get(slot, slot)} :")
        lines += [
            f"  · {_span(s['from'], s['to'])} : {item_tag(s['item'], s.get('quality'), s.get('name'))} "
            f"(niveau requis {s['required_level']} ; {_how(s)})"
            for s in by_slot[slot]
        ]
    if not by_slot:
        lines.append("- Aucun objet de GearQuest Forever obtenable dans cette tranche pour ta classe et ton camp.")
    extra, links = _links(doc, context, high, deps, span=f"niveaux {low}-{high}")
    return "\n".join(lines + extra + _tail(doc, high)), links


def gear_level_reply(
    deps: Any, context: Mapping[str, str], level: int | tuple[int, int]
) -> tuple[str, list[dict[str, str]]]:
    """« Mon équipement à ce niveau » : un objet par emplacement (lien, niveau requis, comment l'obtenir), objets
    visés exprès d'abord, butin aléatoire ensuite ; Mage : choix de GearQuest montré quand nos poids en préfèrent un
    autre ; objets mis à part, écartés, liens à copier, provenance. Une tranche (de, à) : `_range_reply`."""
    if isinstance(level, tuple):
        return _range_reply(deps, context, *level)
    doc = _leveling(deps, context, level)
    if "picks" not in doc:  # erreur de l'outil : son message tel quel
        return f"Équipement au niveau {level} : {doc.get('error') or doc.get('message') or 'non calculé'}", []
    lines = [
        f"## Équipement au niveau {level} (GearQuest Forever, objets obtenables à ce niveau)",
        _summary(doc["picks"]),
    ]
    for p in _ordered(doc["picks"]):
        slot = SLOTS_FR.get(p["slot"], p["slot"])
        tag = item_tag(p["item"], p.get("quality"), p.get("name"))
        lines.append(f"- {slot} : {tag} (niveau requis {p['required_level']} ; {_how(p)}{_why(p, level)})")
    if not doc["picks"]:
        lines.append("- Aucun objet de GearQuest Forever obtenable à ce niveau pour ta classe et ton camp.")
    extra, links = _links(doc, context, level, deps)
    offer = [NEXT_STEP] if doc["picks"] else []  # décision 282 : la suite, avec le bouton posé par le pont
    return "\n".join(lines + extra + _tail(doc, level) + offer), links


NEXT_STEP = "Veux-tu la feuille de route pour obtenir ces objets ?"
KINDS = (
    ("quest_reward", "de quêtes"), ("seasonal_quest", "de quêtes"), ("boss_drop", "de donjon"), ("raid_trash", "de donjon"),
    ("vendor", "de marchand"), ("world_drop", "de butin aléatoire"),
)  # fmt: skip


def _summary(picks: list[dict[str, Any]]) -> str:
    """Résumé d'abord : combien d'objets par origine (décision 282)."""
    counts: dict[str, int] = {}
    labels = dict(KINDS)
    for p in picks:
        label = labels.get(str(p.get("source")), "d'autres origines")
        counts[label] = counts.get(label, 0) + 1
    if not counts:
        return "En bref : aucun objet."
    parts = [f"{n} objet{'s' if n > 1 else ''} {label}" for label, n in counts.items()]
    return "En bref : " + ", ".join(parts) + "."


def gear_route_reply(deps: Any, context: Mapping[str, str], level: int) -> tuple[str, list[dict[str, str]]]:
    """« En faire une route » (bloc 4c) : les objets obtenables au niveau `level` (même sortie que
    `gear_level_reply`), regroupés par origine : donjons avec leurs passages attendus (taux du livre des donjons),
    quêtes par zone, autres origines, butin aléatoire en dernier ; l'ordre par l'optimiseur de trajets et la livraison
    dans RestedXP viennent au bloc 4d."""
    from forever.dungeons import build_dungeons, where_item
    from forever.gear_route import plan_gear_route

    doc = _leveling(deps, context, level)
    if "picks" not in doc:
        return f"Route d'équipement au niveau {level} : {doc.get('error') or doc.get('message') or 'non calculée'}", []
    dungeons = build_dungeons(deps)
    items = []
    tags = {}
    for p in _ordered(doc["picks"]):
        tags[p["item"]] = item_tag(p["item"], p.get("quality"), p.get("name"))
        drops = list(where_item(dungeons, p["item"])) if p.get("source") in ("boss_drop", "raid_trash") else []
        if drops:
            best = max(drops, key=lambda d: d["rate"] if isinstance(d.get("rate"), int | float) else -1)
            rate = best["rate"] if isinstance(best.get("rate"), int | float) else None
            source = {"kind": "donjon", **best, "rate": rate}
        elif p.get("quest"):
            source = {"kind": "quête", "quest": p["quest"], "zone": p.get("zone")}
        else:
            source = {"kind": "autre", "text": _how(p)}
        items.append({"slot": p["slot"], "item": p["item"], "sources": [source]})
    plan = plan_gear_route(items)
    lines = [f"## Route d'équipement au niveau {level} (objets obtenables à ce niveau, GearQuest Forever)"]
    for d in plan["dungeons"]:
        objects = ", ".join(tags[i] for i in d["items"])
        if d["expected_runs"] is None:
            lines.append(f"- Donjon {d['name']} : {objects} ; taux inconnu, passages non chiffrés")
        else:
            lines.append(
                f"- Donjon {d['name']} : {objects} ; environ {d['expected_runs']:.1f} passage(s) en moyenne, "
                f"{d['runs_for_chance']} pour 9 chances sur 10"
            )
    for z in plan["quests"]:
        quests = ", ".join(f"{q} ({', '.join(tags[i] for i in _quest_items(items, q))})" for q in z["quests"])
        lines.append(f"- Quêtes en {z['zone']} : {quests}")
    for o in plan["others"]:  # dans l'ordre de `_ordered` : butin aléatoire en dernier
        lines.append(f"- {tags[o['item']]} : {o['text']}")
    if not doc["picks"]:
        lines.append("- Aucun objet de GearQuest Forever obtenable à ce niveau pour ta classe et ton camp.")
    lines.append("Ordre par l'optimiseur de trajets et livraison dans RestedXP : bloc 4d.")
    extra, links = _links(doc, context, level, deps)
    return "\n".join(lines + extra + _tail(doc, level)), links


def _quest_items(items: list[dict[str, Any]], quest: Any) -> list[int]:
    return [i["item"] for i in items for s in i["sources"] if s.get("kind") == "quête" and s.get("quest") == quest]
