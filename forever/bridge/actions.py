"""Actions du jeu traitées par le pont sans le modèle (P06b, décision 235). Un message porte le drapeau
`a=<action>[:<identifiant>]` ; le pont l'intercepte avant la file : l'agent n'est jamais appelé pour une action.
Liste fermée ; l'identifiant venu de la bande est apparié exactement à une entrée connue (carte publiée), jamais passé
tel quel à une commande.

Bloc A : seules les cartes de test (`forever bridge selftest --card`) sont connues ; le pont note l'action et ne lance
rien. Bloc B : attentes de `forever update` et commandes fixées."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

ACTIONS = ("update", "approve", "reject", "profile_apply", "profile_dismiss")
WITH_ID = frozenset({"approve", "reject", "profile_apply", "profile_dismiss"})


def parse_action(flag: str) -> tuple[str, str | None] | None:
    """(action, identifiant) d'un drapeau `a=…` ; None si l'action n'est pas de la liste fermée, si l'identifiant
    manque, est en trop ou porte un caractère hors de `[A-Za-z0-9._-]`."""
    raise NotImplementedError


def card_for(cards: Sequence[Mapping[str, Any]], action: str, target: str | None) -> Mapping[str, Any] | None:
    """Carte publiée dont l'identifiant est exactement `target` et qui offre le bouton de cette action."""
    raise NotImplementedError
