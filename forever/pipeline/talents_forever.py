"""Talents Forever (`TalentsForeverBook/Data.lua`) : arbres lus et recoupés avec `classes.json` (T08d, bloc D).

Lecture locale par `forever/pipeline/lua_table.py`, jamais par du Lua exécuté ; rien de l'addon n'est recopié dans
le dépôt : seuls des comptes et des écarts sortent d'ici. Fonctions reprises de `scripts/compare_talents_forever.py`
(T08c), qui les appelle."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def read_trees(path: Path) -> tuple[dict[str, Any], dict[str, dict[int, dict[str, Any]]]]:
    """En-tête (`build`, `generated`, `codeVersion`) et nœuds par fichier de classe de `Data.lua`."""
    raise NotImplementedError


def our_trees(classes_json: Path) -> dict[str, dict[int, dict[str, Any]]]:
    """Nœuds de `classes.json` par fichier de classe."""
    raise NotImplementedError


def compare(mine: dict[int, dict[str, Any]], theirs: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Comptes et écarts entre deux jeux de nœuds."""
    raise NotImplementedError


def crosscheck(data_lua: Path, classes_json: Path) -> dict[str, Any]:
    """Recoupement résumé : en-tête de Talents Forever et, par classe, comptes (aucune valeur de l'addon)."""
    raise NotImplementedError
