"""Cartes « À valider » publiées par le pont (P06b, décision 235) : `{id, kind, title, lines, buttons}`, rendues par
l'addon dans le panneau « À valider (n) ». Un bouton porte `action` (envoyée en `a=<action>` après un second clic de
confirmation) ou `explain` (question fixe passée par la file).

Bloc A : carte de test de `forever bridge selftest --card`, écrite dans `<cache>/bridge/cards/selftest.json` (le pont
en marche réécrit les emplacements à chaque publication : il relit ce fichier lui-même), retirée après une action ou
au bout de `SELFTEST_TTL_S` secondes. Bloc B : cartes des attentes de `forever update`."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SELFTEST_PREFIX = "selftest-"
SELFTEST_TTL_S = 900
_SELFTEST_FILE = "selftest.json"


def card_dir(cache_dir: Path) -> Path:
    return cache_dir / "bridge" / "cards"


def selftest_card(stamp: str) -> dict[str, Any]:
    """Carte de test : Valider et Refuser (second clic de confirmation), aucune commande derrière."""
    card_id = SELFTEST_PREFIX + stamp
    return {
        "id": card_id,
        "kind": "update",
        "title": "Carte de test du pont",
        "lines": [
            "Valider ou Refuser, puis Confirmer : le pont note l'action dans son journal sans rien lancer.",
            "Créée par forever bridge selftest --card.",
        ],
        "buttons": [
            {"key": "approve", "label": "Valider", "action": f"approve:{card_id}", "confirm": True},
            {"key": "reject", "label": "Refuser", "action": f"reject:{card_id}", "confirm": True},
        ],
    }


def write_selftest_card(cache_dir: Path, *, stamp: str, now: float) -> dict[str, Any]:
    """Écrit la carte de test (atomiquement) ; rend la carte."""
    card = selftest_card(stamp)
    path = card_dir(cache_dir) / _SELFTEST_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(json.dumps({"created": now, "card": card}, ensure_ascii=False, indent=1).encode("utf-8"))
    os.replace(tmp, path)
    return card


def read_selftest_cards(cache_dir: Path, *, now: float) -> list[dict[str, Any]]:
    """Carte de test en cours ([] si absente, illisible ou périmée)."""
    try:
        doc = json.loads((card_dir(cache_dir) / _SELFTEST_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    card = doc.get("card") if isinstance(doc, dict) else None
    created = doc.get("created") if isinstance(doc, dict) else None
    if not isinstance(card, dict) or not isinstance(created, int | float) or now - created > SELFTEST_TTL_S:
        return []
    if not str(card.get("id", "")).startswith(SELFTEST_PREFIX):
        return []
    return [card]


def clear_selftest_card(cache_dir: Path) -> None:
    (card_dir(cache_dir) / _SELFTEST_FILE).unlink(missing_ok=True)


class CardSource:
    """Cartes que le pont publie (bloc A : la carte de test) ; `done` retire la carte après une action."""

    def __init__(self, cache_dir: Path, now: Callable[[], float] | None = None) -> None:
        self.cache_dir = cache_dir
        self.now = now or time.time

    def current(self) -> list[dict[str, Any]]:
        return read_selftest_cards(self.cache_dir, now=self.now())

    def done(self, card_id: str) -> None:
        if card_id.startswith(SELFTEST_PREFIX):
            clear_selftest_card(self.cache_dir)


def card_lines(entry: dict[str, Any]) -> list[str]:
    """Lignes d'une carte, rédigées par le pont depuis les champs de l'attente."""
    raise NotImplementedError


def update_cards(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cartes des attentes ouvertes (`en_attente`, `approuvée`), dans l'ordre reçu."""
    raise NotImplementedError
