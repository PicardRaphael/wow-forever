"""Savoir des familiers du Chasseur (CH0) : recoupement client ↔ Forever Bestiary ↔ Questie, fiches et guide
d'apprivoisement, en fonctions pures (aucun calcul de combat : filtres et tris de données).

Le client fait foi : un écart avec l'addon ou Questie est listé avec ses deux valeurs et leurs sources, jamais
tranché ; les fiches rendent la valeur du client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.pipeline.pets import family_key
from forever.pipeline.questie import QuestieDB

GAP_KINDS = (
    "family_missing_addon",
    "family_missing_client",
    "family_bonus",
    "family_diet",
    "family_abilities",
    "ability_missing_client",
    "rank_level",
    "beast_family_unknown",
    "beast_level_questie",
    "beast_zone_questie",
)
GAP_TITLES = {
    "family_missing_addon": "Familles du client absentes de l'addon",
    "family_missing_client": "Familles de l'addon absentes du client",
    "family_bonus": "Bonus de famille différents",
    "family_diet": "Régimes différents",
    "family_abilities": "Capacités d'une famille différentes",
    "ability_missing_client": "Capacités de l'addon absentes du client",
    "rank_level": "Niveau requis d'un rang différent",
    "beast_family_unknown": "Bêtes de l'addon d'une famille inconnue du client",
    "beast_level_questie": "Plage de niveau d'un PNJ différente de Questie",
    "beast_zone_questie": "Zone d'un PNJ différente de Questie",
}


def _sources(pets: Mapping[str, Any], bestiary: Mapping[str, Any], questie: QuestieDB | None) -> dict[str, Any]:
    info = bestiary.get("info", {})
    return {
        "client": f"client {pets.get('build')} (pets.json)",
        "addon": (
            f"Forever Bestiary {info.get('version')} (base du {info.get('date')}, client {info.get('client_build')} ; "
            f"carte communautaire du {info.get('community_date')})"
        ),
        "questie": f"Questie {questie.info.version} (base Classic Era)" if questie is not None else None,
    }


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def crosscheck(
    pets: Mapping[str, Any], bestiary: Mapping[str, Any], questie: QuestieDB | None = None
) -> dict[str, Any]:
    """Écarts entre `pets.json` (client), la base de Forever Bestiary et Questie : chaque écart porte son type
    (`GAP_KINDS`), son sujet, ses deux valeurs et leurs sources."""
    src = _sources(pets, bestiary, questie)
    gaps: list[dict[str, Any]] = []

    def gap(kind: str, subject: str, field: str | None, a: tuple[str, Any], b: tuple[str, Any]) -> None:
        gaps.append(
            {
                "kind": kind,
                "subject": subject,
                "field": field,
                "values": {a[0]: a[1], b[0]: b[1]},
                "sources": {a[0]: src[a[0]], b[0]: src[b[0]]},
            }
        )

    aliases = pets.get("aliases", {})
    client_fams: Mapping[str, Any] = pets.get("families", {})
    addon_fams: Mapping[str, Any] = {aliases.get(k, k): v for k, v in bestiary.get("families", {}).items()}
    for key in sorted(set(client_fams) - set(addon_fams)):
        gap("family_missing_addon", key, None, ("client", client_fams[key]["name"]["en"]), ("addon", None))
    for key in sorted(set(addon_fams) - set(client_fams)):
        gap("family_missing_client", key, None, ("client", None), ("addon", addon_fams[key]["name"].get("en")))
    common = sorted(set(client_fams) & set(addon_fams))
    for key in common:
        ours, theirs = client_fams[key], addon_fams[key]
        for field, value in ours.get("bonus", {}).items():
            other = theirs.get("bonus", {}).get(field)
            if _number(value) is not None and _number(other) is not None and _number(value) != _number(other):
                gap("family_bonus", key, field, ("client", value), ("addon", other))
        diet = [d["en"] for d in ours.get("diet") or []]
        if ours.get("diet") is not None and sorted(diet) != sorted(theirs.get("diet", [])):
            gap("family_diet", key, None, ("client", diet), ("addon", list(theirs.get("diet", []))))
        mine = sorted(ours.get("abilities", []))
        listed = sorted(family_key(a) for a in theirs.get("abilities", []))
        if mine != listed:
            gap("family_abilities", key, None, ("client", mine), ("addon", listed))

    client_abilities: Mapping[str, Any] = pets.get("abilities", {})
    for name, ability in sorted(bestiary.get("abilities", {}).items()):
        key = family_key(name)
        client = client_abilities.get(key)
        if client is None:
            gap("ability_missing_client", key, None, ("client", None), ("addon", name))
            continue
        levels = {r["rank"]: r["level"] for r in client.get("ranks", [])}
        for r in ability.get("ranks", []):
            rank, level = r.get("rank"), r.get("level")
            if level is not None and rank in levels and levels[rank] != level:
                gap("rank_level", key, f"rang {rank}", ("client", levels[rank]), ("addon", level))

    beasts = bestiary.get("beasts", [])
    zone_names = questie.zone_names() if questie is not None else {}
    for b in beasts:
        subject = str(b.get("id"))
        family = aliases.get(b.get("family"), b.get("family"))
        if family not in client_fams:
            gap("beast_family_unknown", subject, "famille", ("client", None), ("addon", b.get("family")))
        if questie is None or not isinstance(b.get("id"), int):
            continue
        npc = questie.npc(b["id"])
        if npc is None:
            continue
        if [npc.min_level, npc.max_level] != list(b.get("level", [])):
            gap(
                "beast_level_questie",
                subject,
                "niveau",
                ("questie", [npc.min_level, npc.max_level]),
                ("addon", b["level"]),
            )
        zone = zone_names.get(npc.zone_id)
        if zone and b.get("zones") and zone not in b["zones"]:
            gap("beast_zone_questie", subject, "zone", ("questie", zone), ("addon", list(b["zones"])))

    order = {k: i for i, k in enumerate(GAP_KINDS)}
    gaps.sort(key=lambda g: (order[g["kind"]], g["subject"], str(g["field"])))
    return {
        "sources": src,
        "counts": {
            "families_client": len(client_fams),
            "families_addon": len(addon_fams),
            "families_compared": len(common),
            "abilities_addon": len(bestiary.get("abilities", {})),
            "beasts": len(beasts),
            "beasts_in_questie": sum(
                1 for b in beasts if questie is not None and isinstance(b.get("id"), int) and questie.npc(b["id"])
            ),
        },
        "gaps": gaps,
    }


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "—"
    return str(value).replace("|", "\\|")


def render_crosscheck_markdown(report: Mapping[str, Any]) -> str:
    """Rapport Markdown déterministe du recoupement (`docs/research/familiers-recoupement.md`)."""
    src, counts = report["sources"], report["counts"]
    lines = [
        "# Familiers du Chasseur : recoupement client ↔ Forever Bestiary ↔ Questie",
        "",
        "Rapport généré par `forever pets crosscheck --markdown` : ne pas éditer à la main. Le client fait foi ;",
        "chaque écart est listé avec ses deux valeurs et leurs sources, jamais tranché.",
        "",
        f"- Client : {src['client']}",
        f"- Addon : {src['addon']}",
        f"- Questie : {src['questie'] or 'non lu'}",
        (
            f"- Familles : {counts['families_client']} dans le client, {counts['families_addon']} dans l'addon, "
            f"{counts['families_compared']} comparées ; capacités de l'addon : {counts['abilities_addon']} ; "
            f"bêtes de l'addon : {counts['beasts']} (dont {counts['beasts_in_questie']} dans Questie)"
        ),
        f"- Écarts : {len(report['gaps'])}",
        "",
    ]
    for kind in GAP_KINDS:
        rows = [g for g in report["gaps"] if g["kind"] == kind]
        if not rows:
            continue
        lines += [f"## {GAP_TITLES[kind]} ({len(rows)})", ""]
        sides = list(rows[0]["values"])
        lines += [
            f"| Sujet | Champ | {sides[0]} | {sides[1]} |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| {_cell(g['subject'])} | {_cell(g['field'])} | {_cell(g['values'][sides[0]])} | "
            f"{_cell(g['values'][sides[1]])} |"
            for g in rows
        ]
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"
