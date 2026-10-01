"""Savoir des familiers du Chasseur (CH0) : recoupement client ↔ Forever Bestiary ↔ Questie, fiches et guide
d'apprivoisement, en fonctions pures (aucun calcul de combat : filtres et tris de données).

Le client fait foi : un écart avec l'addon ou Questie est listé avec ses deux valeurs et leurs sources, jamais
tranché ; les fiches rendent la valeur du client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.pipeline.questie import QuestieDB

GAP_KINDS = (
    "family_missing_addon",
    "family_missing_client",
    "family_bonus",
    "family_diet",
    "family_abilities",
    "ability_missing_client",
    "rank_level",
    "beast_family_unknown",
    "beast_level_questie",
    "beast_zone_questie",
)


def crosscheck(
    pets: Mapping[str, Any], bestiary: Mapping[str, Any], questie: QuestieDB | None = None
) -> dict[str, Any]:
    """Écarts entre `pets.json` (client), la base de Forever Bestiary et Questie : chaque écart porte son type
    (`GAP_KINDS`), son sujet, ses deux valeurs et leurs sources."""
    raise NotImplementedError


def render_crosscheck_markdown(report: Mapping[str, Any]) -> str:
    """Rapport Markdown déterministe du recoupement (`docs/research/familiers-recoupement.md`)."""
    raise NotImplementedError
