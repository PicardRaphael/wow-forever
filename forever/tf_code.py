"""Code de build de Talents Forever, génération 6 (FA1, décision 209) : lecture et écriture sur une disposition
abstraite (rangs maximaux par arbre et par position de liste), sans aucune donnée de l'addon.

Format réimplémenté d'après la lecture de l'addon (aucune licence, décisions 172 et 196), décrit dans
`tasks/FA1-plan.md`. Règle d'échange, pas une formule de combat : hors de `forever/engine/`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

CODE_VERSION = "6"
SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz056789"
SITE = "https://talentsforever.com/"


@dataclass(frozen=True)
class TfPlan:
    """Build lu ou à écrire : rangs par arbre et par position de liste, ordre (arbre, position) d'un pas par point."""

    class_slug: str
    level: int
    ranks: tuple[tuple[int, ...], ...]
    order: tuple[tuple[int, int], ...] | None = None
    legacy: tuple[str, ...] | None = None


def encode(plan: TfPlan) -> str:
    raise NotImplementedError


def decode(code: str, max_ranks: Sequence[Sequence[int]], class_slug: str | None = None) -> TfPlan:
    raise NotImplementedError


def code_of(text: str) -> str:
    raise NotImplementedError


def link(code: str) -> str:
    raise NotImplementedError
