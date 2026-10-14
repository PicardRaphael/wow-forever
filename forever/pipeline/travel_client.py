"""Trajets décodés du client (`travel.json`, RX1, bloc B).

Points de vol (`TaxiNodes` : nom, continent, position monde, camp par les drapeaux), trajets (`TaxiPath` : départ,
arrivée, coût) et leur longueur (somme des segments de `TaxiPathNode`, segment de téléportation ou de changement de
continent exclu), passage carte ↔ monde (`UiMapAssignment` : bornes de la carte de zone dans son continent). Toutes
les constantes de lecture viennent de `decode_rules.json` (`travel`) ; aucun chiffre de jeu ici. Registre : I19."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.pipeline.tables import Row

TRAVEL_FILE = "travel.json"
TRAVEL_FILES = (TRAVEL_FILE,)
SCHEMA_VERSION = 1

Tables = Mapping[str, Sequence[Row]]


def travel_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des trajets (`travel_tables`, téléchargées à part, facultatives)."""
    raise NotImplementedError


def load_travel_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    raise NotImplementedError


def decode_travel(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    raise NotImplementedError


def travel_errors(doc: Any) -> list[str]:
    raise NotImplementedError
