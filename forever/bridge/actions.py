"""Actions du jeu traitées par le pont sans le modèle (P06b, décision 235). Un message porte le drapeau
`a=<action>[:<identifiant>]` ; le pont l'intercepte avant la file : l'agent n'est jamais appelé pour une action.
Liste fermée ; l'identifiant venu de la bande est apparié exactement à une entrée connue (carte publiée), jamais passé
tel quel à une commande.

Bloc A : seules les cartes de test (`forever bridge selftest --card`) sont connues ; le pont note l'action et ne lance
rien. Bloc B : attentes de `forever update` et commandes fixées."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

ACTIONS = ("update", "approve", "reject", "profile_apply", "profile_dismiss")
WITH_ID = frozenset({"approve", "reject", "profile_apply", "profile_dismiss"})
_ID = re.compile(r"[A-Za-z0-9._-]{1,120}")


def parse_action(flag: str) -> tuple[str, str | None] | None:
    """(action, identifiant) d'un drapeau `a=…` ; None si l'action n'est pas de la liste fermée, si l'identifiant
    manque, est en trop ou porte un caractère hors de `[A-Za-z0-9._-]`."""
    if not flag.startswith("a="):
        return None
    name, sep, target = flag[2:].partition(":")
    if name not in ACTIONS:
        return None
    if name in WITH_ID:
        return (name, target) if sep and _ID.fullmatch(target) else None
    return None if sep else (name, None)


def action_flag(flags: frozenset[str]) -> str | None:
    """Drapeau `a=…` du message, s'il en porte un."""
    return next((f for f in sorted(flags) if f.startswith("a=")), None)


def card_for(cards: Sequence[Mapping[str, Any]], action: str, target: str | None) -> Mapping[str, Any] | None:
    """Carte publiée dont l'identifiant est exactement `target` et qui offre le bouton de cette action."""
    if target is None:
        return None
    wanted = f"{action}:{target}"
    for card in cards:
        if card.get("id") != target:
            continue
        if any(isinstance(b, Mapping) and b.get("action") == wanted for b in card.get("buttons") or ()):
            return card
    return None


def approvable(entry: Mapping[str, Any]) -> bool:
    """Attente que Valider et Refuser peuvent traiter : installation d'action `attente` ou mesure, à l'état
    `en_attente`."""
    raise NotImplementedError


def update_argv(kind: str, pending_id: str | None = None) -> list[str]:
    """Commande fixée d'une action : passage, approbation ou rejet d'une attente."""
    raise NotImplementedError


class ActionHandler:
    """Actions de mise à jour du jeu (bloc B) : commandes fixées lancées par `spawn(argv, journal_du_passage)`."""

    def __init__(self, *, cache_dir: Any, now: Any, offline: bool = False, spawn: Any = None) -> None:
        raise NotImplementedError

    def handle(self, action: str, target: str | None) -> tuple[str, str]:
        """(résultat noté au journal, texte de la réponse)."""
        raise NotImplementedError
