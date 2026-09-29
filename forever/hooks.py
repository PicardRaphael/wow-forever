"""Hooks du plugin Claude Code (T06, décision D4) : ligne de fraîcheur au démarrage, contrôle des chiffres de jeu en
fin de réponse.

Le plugin reste mince : `plugin/hooks/hooks.json` appelle `forever hook session-start` et `forever hook check-numbers`.
Les deux n'agissent que là où le plugin sert (dans le dépôt pour la ligne de fraîcheur ; dans une session qui a utilisé
un outil ou un skill de forever pour le contrôle des chiffres), ne lèvent jamais d'exception et n'appellent pas le
réseau."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import REPO_ROOT, Deps

GAME_NUMBER = re.compile(r"(?!)")
"""Chiffre de jeu dans un texte : nombre (ou suite « 20 à 22 ») suivi d'une unité de jeu."""

NUMBERS_MARKER = "[forever:chiffres]"
"""Préfixe du message du contrôle des chiffres (cherché par les correcteurs de l'évaluation)."""


@dataclass(frozen=True)
class GameNumber:
    text: str
    values: tuple[float, ...]
    decimals: tuple[int, ...]
    unit: str


def game_numbers(text: str) -> list[GameNumber]:
    """Chiffres de jeu d'un texte, dans l'ordre."""
    raise NotImplementedError


def session_used_forever(lines: Iterable[Mapping[str, Any]]) -> bool:
    """Vrai si le transcript contient un appel d'outil MCP `forever_*` ou d'un skill `forever-*`."""
    raise NotImplementedError


def unsourced_numbers(lines: Iterable[Mapping[str, Any]], last_message: str | None = None) -> list[str]:
    """Chiffres de jeu de la dernière réponse absents des résultats des outils `forever_*` (et de la question)."""
    raise NotImplementedError


def read_transcript(path: Path) -> list[dict[str, Any]]:
    """Lignes JSON d'un transcript (lignes illisibles ignorées ; fichier absent : liste vide)."""
    raise NotImplementedError


def check_numbers_output(hook_input: Mapping[str, Any]) -> dict[str, Any] | None:
    """Sortie du hook Stop : message à l'utilisateur, sans blocage ; None si rien à signaler ou hors de forever."""
    raise NotImplementedError


def session_line(deps: Deps, environ: Mapping[str, str]) -> str:
    """Ligne de fraîcheur, cache seulement (aucun réseau) ; ne lève jamais d'exception."""
    raise NotImplementedError


def session_start_output(
    hook_input: Mapping[str, Any], deps: Deps, environ: Mapping[str, str], repo_root: Path = REPO_ROOT
) -> dict[str, Any] | None:
    """Sortie du hook SessionStart : la ligne (visible et ajoutée au contexte) si la session s'ouvre dans le dépôt ;
    None ailleurs."""
    raise NotImplementedError
