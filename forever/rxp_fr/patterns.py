"""Phrases types des guides RestedXP (FR1) : tournures fréquentes, appliquées par motif sur le gabarit quand la
mémoire ne les a pas. Tournures relevées dans les guides que RestedXP a traduits (« Parlez à », « Acceptez la
quête », « Rendez la quête », « Tuez », « Apprenez »…) ; aucun texte de guide, aucun nom, aucun chiffre de jeu ici."""

from __future__ import annotations

import re

# Préfixes des lignes de quête (`.accept`, `.turnin`) : anglais de RestedXP -> tournure de sa version française.
QUEST_PREFIXES = {"accept": ("Accept ", "Acceptez la quête "), "turnin": ("Turn in ", "Rendez la quête ")}
_S = r"(\{\d+\})"  # un jeton
_I = r"(?P<icon>(?:\{\d+\})?)"  # icône facultative en tête
_END = r"(?P<end>[.!]?)"
# Motif (gabarit anglais entier) -> gabarit français ; \g<icon> et \g<end> gardent l'icône et la ponctuation.
PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(f"^{_I}{en}{_END}$"), fr)
    for en, fr in (
        (rf"Talk to {_S}", r"\g<icon>Parlez à \2\g<end>"),
        (rf"Talk to {_S} and {_S}", r"\g<icon>Parlez à \2 et à \3\g<end>"),
        (rf"Talk to {_S} or {_S}", r"\g<icon>Parlez à \2 ou à \3\g<end>"),
        (rf"Talk to the {_S}", r"\g<icon>Parlez au \2\g<end>"),
        (rf"Talk to {_S} upstairs", r"\g<icon>Parlez à \2 à l'étage\g<end>"),
        (rf"Talk to {_S} up stairs", r"\g<icon>Parlez à \2 à l'étage\g<end>"),
        (rf"Kill {_S}", r"\g<icon>Tuez \2\g<end>"),
        (rf"Kill {_S} and {_S}", r"\g<icon>Tuez \2 et \3\g<end>"),
        (rf"Kill {_S}, {_S} and {_S}", r"\g<icon>Tuez \2, \3 et \4\g<end>"),
        (rf"Kill {_S}\. Loot them for their {_S}", r"\g<icon>Tuez \2. Dépouillez-les pour leur \3\g<end>"),
        (rf"Kill {_S}\. Loot him for his {_S}", r"\g<icon>Tuez \2. Dépouillez-le pour son \3\g<end>"),
        (rf"Kill {_S}\. Loot him for the {_S}", r"\g<icon>Tuez \2. Dépouillez-le pour obtenir \3\g<end>"),
        (rf"Kill {_S}\. Loot them for the {_S}", r"\g<icon>Tuez \2. Dépouillez-les pour obtenir \3\g<end>"),
        (
            rf"Kill {_S} and {_S}\. Loot them for their {_S}",
            r"\g<icon>Tuez \2 et \3. Dépouillez-les pour leur \4\g<end>",
        ),
        (rf"Click the {_S}", r"\g<icon>Cliquez sur \2\g<end>"),
        (rf"Click on the {_S}", r"\g<icon>Cliquez sur \2\g<end>"),
        (rf"Click the {_S} on the ground", r"\g<icon>Cliquez sur \2 au sol\g<end>"),
        (rf"Loot the {_S} on the ground", r"\g<icon>Ramassez \2 au sol\g<end>"),
        (rf"Open the {_S}\. Loot it for the {_S}", r"\g<icon>Ouvrez \2. Fouillez-le pour obtenir \3\g<end>"),
        (r"Train your class spells", r"\g<icon>Apprenez vos sorts de classe\g<end>"),
        (r"Train your pet spells", r"\g<icon>Apprenez les sorts de votre familier\g<end>"),
        (rf"Train {_S}", r"\g<icon>Apprenez \2\g<end>"),
        (rf"Train {_S}{_S}", r"\g<icon>Apprenez \2\3\g<end>"),
        (rf"Travel to {_S}", r"\g<icon>Allez jusqu'à \2\g<end>"),
        (rf"Use the {_S}", r"\g<icon>Utilisez \2\g<end>"),
        (rf"Use {_S}{_S}", r"\g<icon>Utilisez \2\3\g<end>"),
        (rf"Cast {_S}{_S}", r"\g<icon>Lancez \2\3\g<end>"),
        (rf"Buy {_S}", r"\g<icon>Achetez \2\g<end>"),
        (rf"Equip the {_S}", r"\g<icon>Équipez \2\g<end>"),
        (rf"Hearth to {_S}", r"\g<icon>Utilisez votre pierre de foyer pour aller à \2\g<end>"),
    )
)
# Phrases à un lieu (« Fly to Tanaris ») : le lieu est un nom de zone traduit par la table des noms.
PLACE_PHRASES = {
    "Fly to ": "Volez vers ",
    "Travel to ": "Allez jusqu'à ",
    "Teleport to ": "Téléportez-vous à ",
    "Hearth to ": "Utilisez votre pierre de foyer pour aller à ",
}


def apply_patterns(pattern: str) -> str | None:
    for regex, french in PATTERNS:
        m = regex.match(pattern)
        if m:
            return m.expand(french)
    return None
