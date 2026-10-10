"""Jargon interne du projet dans une réponse au joueur (sonde en jeu H du 2026-10-10, décision 238) : noms de
tranche (T10a, P06b, FA1…), noms de champ ou d'outil (`next_step`, `forever_build`). Critère « jargon interne » du banc
de la conversation « jeu » (`speed.quality_failures`)."""

from __future__ import annotations

import re

_SLICE = re.compile(
    r"\b(?:T\d{2}[a-z]?|P0\d[a-z]?|FA\d|CH\d|PV\d|SIM\d|AN\d|LN\d|EX\d|DE\d|CM\d|PA\d|GU\d|VO\d|PR\d|DR\d)\b"
)
_IDENTIFIER = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")  # snake_case : champ ou outil (next_step, forever_build)


def internal_jargon(text: str) -> list[str]:
    """Termes internes trouvés dans le texte, dans l'ordre (vide : réponse en mots de joueur)."""
    found = [m.group(0) for m in _SLICE.finditer(text or "")]
    found += [m.group(0) for m in _IDENTIFIER.finditer(text or "")]
    return list(dict.fromkeys(found))
