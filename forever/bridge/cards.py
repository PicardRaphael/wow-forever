"""Cartes « À valider » publiées par le pont (P06b, décision 235) : `{id, kind, title, lines, buttons}`, rendues par
l'addon dans le panneau « À valider (n) ». Un bouton porte `action` (envoyée en `a=<action>` après un second clic de
confirmation) ou `explain` (question fixe passée par la file).

Bloc A : carte de test de `forever bridge selftest --card`, écrite dans `<cache>/bridge/cards/selftest.json` (le pont
en marche réécrit les emplacements à chaque publication : il relit ce fichier lui-même), retirée après une action ou
au bout de `SELFTEST_TTL_S` secondes. Bloc B : cartes des attentes de `forever update`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SELFTEST_PREFIX = "selftest-"
SELFTEST_TTL_S = 900


def card_dir(cache_dir: Path) -> Path:
    return cache_dir / "bridge" / "cards"


def selftest_card(stamp: str) -> dict[str, Any]:
    """Carte de test : Valider et Refuser (second clic de confirmation), aucune commande derrière."""
    raise NotImplementedError


def write_selftest_card(cache_dir: Path, *, stamp: str, now: float) -> dict[str, Any]:
    """Écrit la carte de test (atomiquement) ; rend la carte."""
    raise NotImplementedError


def read_selftest_cards(cache_dir: Path, *, now: float) -> list[dict[str, Any]]:
    """Carte de test en cours ([] si absente, illisible ou périmée)."""
    raise NotImplementedError


def clear_selftest_card(cache_dir: Path) -> None:
    raise NotImplementedError


class CardSource:
    """Cartes que le pont publie (bloc A : la carte de test) ; `done` retire la carte après une action."""

    def __init__(self, cache_dir: Path, now: Any = None) -> None:
        raise NotImplementedError

    def current(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def done(self, card_id: str) -> None:
        raise NotImplementedError
