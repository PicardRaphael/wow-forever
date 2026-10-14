"""Guide RestedXP d'une feuille de route (RX1, bloc D).

Texte au format des guides de RestedXP, relevé dans le code de RXPGuides 4.11.23 (`GuideLoader.lua`, `ParseGuide` et
`parseLine` ; `functions.lua`, commandes d'étape), lu pour la syntaxe seulement : aucun texte de RestedXP repris.
En-tête `#forever`, `#version`, `#group`, `#name`, camp `<< Horde|Alliance` ; une étape `step` par arrêt de la route,
commandes `.goto <uiMapID>,x,y`, `.accept`, `.complete <quête>,1`, `.turnin`, `.xp`, texte après `>>`. Textes en
anglais (client enUS). Jamais de chaîne d'import chiffrée. Aucun chiffre de jeu ici."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

GUIDE_COMMANDS = ("goto", "accept", "complete", "turnin", "xp")
GUIDE_VERSION = 1  # version du format écrit par forever (en-tête #version)
FIRST_OBJECTIVE = 1  # .complete suit le premier objectif de la quête
INDENT = "    "
_SPACES = re.compile(r"\s+")


def guide_text(value: str) -> str:
    """Texte sûr dans une ligne de guide : ni `<<` (camp ou classe), ni `--` (commentaire), ni `|` (séquence
    d'interface), ni saut de ligne ; `>>` gardé (le premier `>>` d'une ligne ouvre le texte, la suite est du texte)."""
    text = _SPACES.sub(" ", value).strip()
    text = text.replace("|", "/")
    while "<<" in text:
        text = text.replace("<<", "<")
    while "--" in text:
        text = text.replace("--", "-")
    return text


def _goto(stop: Mapping[str, Any]) -> list[str]:
    if stop.get("map") is None or stop.get("x") is None or stop.get("y") is None:
        return []
    return [f"{INDENT}.goto {int(stop['map'])},{float(stop['x']):.1f},{float(stop['y']):.1f}"]


def _step(stop: Mapping[str, Any], end_level: int) -> list[str]:
    name = guide_text(str(stop.get("name") or stop.get("ref")))
    kind = stop["kind"]
    lines = ["step", *_goto(stop)]
    if kind == "accept":
        lines.append(f"{INDENT}.accept {int(stop['ref'])} >>Accept {name}")
    elif kind == "objective":
        lines.append(f"{INDENT}.complete {int(stop['ref'])},{FIRST_OBJECTIVE} >>Complete {name}")
    elif kind == "turnin":
        lines.append(f"{INDENT}.turnin {int(stop['ref'])} >>Turn in {name}")
    elif kind in ("dungeon", "dungeon_repeat"):
        verb = "Run" if kind == "dungeon" else "Run again"
        lines.append(f"{INDENT}>>{verb} {name} with your group")
    elif kind == "grind":
        lines.append(f"{INDENT}.xp {int(end_level)} >>Kill mobs of your level until level {int(end_level)}")
    else:
        raise ValueError(f"arrêt inconnu : {kind}")
    return lines


def encode_guide(plan: Mapping[str, Any], *, name: str, group: str) -> str:
    """Guide RestedXP déterministe d'un plan de `forever route plan`."""
    faction = str(plan.get("faction") or "").capitalize()
    end_level = int(plan["levels"]["to"])
    lines = [
        "#forever",
        f"#version {GUIDE_VERSION}",
        f"#group {guide_text(group)}",
        f"#name {guide_text(name)}",
    ]
    if faction in ("Horde", "Alliance"):
        lines.append(f"<< {faction}")
    prov = plan.get("provenance") or {}
    lines.append(
        f"-- forever route {plan.get('id', '')} : {plan.get('class', '')} {plan['levels']['from']}-{end_level}, "
        f"certitude {plan.get('certainty', 'suppose')}, données {prov.get('game_version', '?')} "
        f"{str(prov.get('data_sha', ''))[:12]}"
    )
    for stop in plan["stops"]:
        lines += _step(stop, end_level)
    return "\n".join(lines) + "\n"
