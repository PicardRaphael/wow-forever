"""Consultation des familiers du Chasseur (CH0, bloc D) : lit `pets.json`, `pet_rules.json`, Forever Bestiary, sa
sauvegarde et Questie sur disque (jamais par le réseau), appelle les fonctions pures de `forever/pets.py` et ajoute
la provenance (version du jeu, empreinte des données, version et empreinte de l'addon, date de sa base, date de la
carte communautaire, date de ma sauvegarde). La CLI (`forever pets …`) et le MCP (`forever_lookup(kind="pets")`)
appellent ces fonctions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from forever.config import Deps


def lookup_pets(
    deps: Deps,
    name: str | None = None,
    *,
    rank: int | None = None,
    zone: str | None = None,
    level: int | None = None,
    detail: bool = False,
    addon_dir: Path | None = None,
    saved_path: Path | None = None,
    questie_dir: Path | None = None,
) -> dict[str, Any]:
    """`name` absent : règles ; famille, capacité ou bête : sa fiche ; avec `zone` et `level` : guide."""
    raise NotImplementedError


def pets_crosscheck(deps: Deps, *, addon_dir: Path | None = None, questie_dir: Path | None = None) -> dict[str, Any]:
    """Recoupement client ↔ Forever Bestiary ↔ Questie, avec provenance."""
    raise NotImplementedError


def pets_mine(deps: Deps, *, saved_path: Path | None = None) -> dict[str, Any]:
    """Mes observations et mes familiers (`ForeverBestiaryDB`), sans aucune donnée de tiers."""
    raise NotImplementedError
