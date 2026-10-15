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


def gear_level_reply(deps: Any, context: Mapping[str, str], level: int) -> str:
    """Texte de la réponse : un objet par emplacement (nom, niveau requis, comment l'obtenir, zone), objets mis à
    part (source ou niveau inconnus), nombre d'objets écartés, provenance."""
    doc = gear_report(
        deps,
        "leveling",
        class_name=str(context.get("class") or "Mage"),
        level=level,
        race=str(context.get("race") or "Orc"),
        faction=str(context.get("faction") or "").lower() or None,
        professions=_professions(context),
    )
    if "picks" not in doc:  # erreur de l'outil : son message tel quel
        return f"Équipement au niveau {level} : {doc.get('error') or doc.get('message') or 'non calculé'}"
    lines = [f"## Équipement au niveau {level} (GearQuest Forever, objets obtenables à ce niveau)"]
    for p in doc["picks"]:
        how = p.get("access") or p.get("source") or "?"
        zone = f", {p['zone']}" if p.get("zone") else ""
        lines.append(f"- {p['slot']} : {p['name'] or p['item']} (niveau requis {p['required_level']} ; {how}{zone})")
    if not doc["picks"]:
        lines.append("- Aucun objet de GearQuest Forever obtenable à ce niveau pour ta classe et ton camp.")
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
    return "\n".join(lines)
