"""Donjons décodés du client (`dungeons.json`, DJ1, bloc A).

Instances de groupe (`Map`), entrées de l'outil de recherche de groupe (`LFGDungeons`) et leur niveau
(`ContentTuning`), rencontres (`DungeonEncounter`) et zones de l'instance (`AreaTable`). Le client ne relie pas une
entrée `LFGDungeons` à sa carte (colonne `MapID` vide) : le lien se fait par le nom, avec les alias déclarés dans
`decode_rules.json` (`dungeons.lfg_names`) ; une entrée non reliée est listée, jamais devinée. Les tables du journal
(`JournalInstance`, `JournalEncounter`, `JournalEncounterItem`) sont absentes de la version 1.60.1.70338 sur
wago.tools (question DON9) : aucun butin ne vient du client. Toutes les constantes de lecture viennent de
`decode_rules.json` ; aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.pipeline.tables import Row

DUNGEON_FILE = "dungeons.json"
DUNGEON_FILES = (DUNGEON_FILE,)
SCHEMA_VERSION = 1

Tables = Mapping[str, Sequence[Row]]


def dungeon_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des donjons (`dungeon_tables`, téléchargées à part, facultatives) :
    présentes, le fichier est décodé ; absentes, il est hérité de la base."""
    raise NotImplementedError


def load_dungeon_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    raise NotImplementedError


def decode_dungeons(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Document `dungeons.json`."""
    raise NotImplementedError


def dungeons_errors(doc: Any) -> list[str]:
    """Contrôle de forme du document."""
    raise NotImplementedError
