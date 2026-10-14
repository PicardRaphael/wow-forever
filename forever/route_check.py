"""Acceptation automatique d'une feuille de route (CJ1, décision 279) : notre route est comparée au parcours gratuit en
clair de RestedXP de la même race et de la même classe, sur les mêmes niveaux, rejoué par nos règles depuis le même
départ. Acceptée : même enchaînement de zones et au plus `MAX_DIFFERENCES` différences, chacune expliquée (quête de
classe, donjon avec ses quêtes, gain mesuré par la simulation) ; sinon refusée, chaque écart dit. Aucun texte de guide
dans le résultat (décision 268) ; Polestar servira de référence au-delà des parcours gratuits (décision 278).

Registre : I18."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

MAX_DIFFERENCES = 3  # règle de l'utilisateur (décision 279) : « à deux ou trois différences près »
SECONDS_PER_MINUTE = 60.0  # conversion d'unité
LISTED = 6  # différences citées dans l'explication (paramètre d'affichage)


def zone_sequence(zones: Iterable[str | None]) -> list[str]:
    """Zones dans l'ordre, zones consécutives fusionnées, zones inconnues ignorées."""
    out: list[str] = []
    for z in zones:
        if z is not None and (not out or out[-1] != z):
            out.append(z)
    return out


def _difference(
    quest_id: int, side: str, quests: Mapping[int, Any], dropped: Mapping[int, str], gains: Mapping[int, float]
) -> dict[str, Any]:
    q = quests.get(quest_id)
    if q is not None and getattr(q, "dungeon", None):
        reason, explained, group = "donjon avec ses quêtes", True, f"donjon {q.dungeon}"
    elif q is not None and getattr(q, "class_quest", False):
        reason, explained, group = "quête de classe", True, "classe"
    elif side == "ours" and gains.get(quest_id, 0.0) > 0:
        minutes = gains[quest_id] / SECONDS_PER_MINUTE
        reason, explained, group = f"gain mesuré : {minutes:.0f} min de moins avec elle", True, f"quête {quest_id}"
    elif side == "reference":
        why = dropped.get(quest_id) or ("absente de nos données" if q is None else "non prise par notre route")
        reason, explained, group = f"faite par le parcours, pas par notre route ({why})", False, f"quête {quest_id}"
    else:
        reason, explained, group = "prise par notre route seulement", False, f"quête {quest_id}"
    return {"quest": quest_id, "side": side, "reason": reason, "explained": explained, "group": group}


def accept_route(
    ours: Sequence[tuple[int, int | None]],
    reference: Sequence[tuple[int, int | None]],
    quests: Mapping[int, Any],
    zone_names: Mapping[int, str],
    *,
    dropped: Mapping[int, str] | None = None,
    gains: Mapping[int, float] | None = None,
) -> dict[str, Any]:
    """Verdict de la décision 279 sur deux suites de rendus `(quête, carte du donneur)` : notre route et la référence.
    Une différence = une quête rendue d'un seul côté ; les quêtes d'un même donjon forment une seule différence, les
    quêtes de classe aussi ; l'enchaînement des zones se compare sans les quêtes des différences expliquées.
    Registre : I18"""
    dropped, gains = dropped or {}, gains or {}

    ours_ids = list(dict.fromkeys(q for q, _ in ours))
    ref_ids = list(dict.fromkeys(q for q, _ in reference))
    differences = [_difference(q, "ours", quests, dropped, gains) for q in ours_ids if q not in set(ref_ids)]
    differences += [_difference(q, "reference", quests, dropped, gains) for q in ref_ids if q not in set(ours_ids)]
    explained = {d["quest"] for d in differences if d["explained"]}

    def names(rows: Sequence[tuple[int, int | None]]) -> list[str]:
        # une différence expliquée (quête de classe en ville, donjon) ne change pas l'enchaînement comparé
        return zone_sequence(None if z is None or q in explained else zone_names.get(z) or str(z) for q, z in rows)

    zones_ours, zones_ref = names(ours), names(reference)
    same_zones = zones_ours == zones_ref
    groups = {d["group"] for d in differences}
    unexplained = [d for d in differences if not d["explained"]]
    accepted = same_zones and not unexplained and len(groups) <= MAX_DIFFERENCES
    parts: list[str] = []
    if not same_zones:
        parts.append(f"enchaînement des zones différent ({' → '.join(zones_ours)} contre {' → '.join(zones_ref)})")
    if len(groups) > MAX_DIFFERENCES:
        parts.append(f"{len(groups)} différences (au plus {MAX_DIFFERENCES})")
    if unexplained:
        shown = "; ".join(f"{d['quest']} : {d['reason']}" for d in unexplained[:LISTED])
        more = f" ; {len(unexplained) - LISTED} autre(s)" if len(unexplained) > LISTED else ""
        parts.append(f"{len(unexplained)} différence(s) sans explication ({shown}{more})")
    if accepted:
        kept = sorted({d["reason"].split(" :")[0] for d in differences})
        explanation = "acceptée : mêmes zones et mêmes quêtes" + (
            f", écarts expliqués ({', '.join(kept)})" if kept else ""
        )
    else:
        explanation = "refusée : " + " ; ".join(parts)
    return {
        "accepted": accepted,
        "zones_ours": zones_ours,
        "zones_reference": zones_ref,
        "common": len(set(ours_ids) & set(ref_ids)),
        "differences": differences,
        "explanation": explanation,
    }
