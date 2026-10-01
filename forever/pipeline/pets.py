"""Système de familiers du Chasseur décodé du client (`pets.json`, CH0, bloc A).

Familles (CreatureFamily dont la ligne de compétence est une ligne de familier du Chasseur), capacités et rangs
(SkillLineAbility, Spell*), bonus de famille (aura passive de chaque ligne), régime (masque de CreatureFamily et
ItemPetFood), effets de « Hunter Pet Scaling », cartes (UiMap). Toutes les constantes de lecture viennent de
`decode_rules.json` (`pet_tables`, `localized_pet_tables`, `pets`) ; aucun chiffre de jeu ici. Les sens tirés d'une
colonne sans nom ou d'un type d'aura restent `probable` ; un écart interne au client est listé dans
`observations`, jamais tranché."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.pipeline.tables import Row

PETS_FILE = "pets.json"
PETS_FILES = (PETS_FILE,)
SCHEMA_VERSION = 1

Tables = Mapping[str, Sequence[Row]]


def pet_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(clé de table, chemin relatif) de chaque CSV des familiers (`pet_tables`, `localized_pet_tables`)."""
    raise NotImplementedError


def load_pet_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    """Tables des familiers lues dans `csv_dir/<locale>/<Table>.csv` (CsvMissingError si un fichier manque)."""
    raise NotImplementedError


def decode_pets(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `pets.json`."""
    raise NotImplementedError


def pets_errors(doc: Any) -> list[str]:
    """Contrôle de forme de `pets.json` : chaque famille a au moins une capacité, chaque rang un niveau, rangs
    numérotés de 1 à n sans trou ni doublon, aucune famille de démon."""
    raise NotImplementedError
