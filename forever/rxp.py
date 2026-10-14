"""Guide RestedXP d'une feuille de route (RX1, bloc D).

Texte au format des guides de RestedXP, relevé dans le code de RXPGuides 4.11.23 (`GuideLoader.lua`, `ParseGuide` et
`parseLine` ; `functions.lua`, commandes d'étape), lu pour la syntaxe seulement : aucun texte de RestedXP repris.
En-tête `#forever`, `#version`, `#group`, `#name`, camp `<< Horde|Alliance` ; une étape `step` par arrêt de la route,
commandes `.goto <uiMapID>,x,y`, `.accept`, `.complete <quête>,1`, `.turnin`, `.xp`, texte après `>>`. Textes en
anglais (client enUS). Jamais de chaîne d'import chiffrée. Aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

GUIDE_COMMANDS = ("goto", "accept", "complete", "turnin", "xp")


def guide_text(value: str) -> str:
    """Texte sûr dans une ligne de guide : ni `<<` (camp ou classe), ni `--` (commentaire), ni `|` (séquence
    d'interface), ni saut de ligne ; `>>` gardé (le premier `>>` d'une ligne ouvre le texte, la suite est du texte)."""
    raise NotImplementedError


def encode_guide(plan: Mapping[str, Any], *, name: str, group: str) -> str:
    """Guide RestedXP déterministe d'un plan de `forever route plan`."""
    raise NotImplementedError
