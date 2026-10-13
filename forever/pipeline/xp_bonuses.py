"""Bonus d'XP décodés du client (`xp_bonuses.json`, T04f, bloc A).

Chaque sort du client qui porte une aura d'XP (codes de `decode_rules.json`, `xp_bonuses.aura_codes`) avec son nom,
ses effets, sa durée, son cumul, sa voie d'accès (objet, perk Legacy, nourriture, aucune) ; la chaîne du sac de
couchage, les nourritures nutritives, les éléments de camp et les conditions de joueur citées par les descriptions.
Toutes les constantes de lecture viennent de `decode_rules.json` ; aucun chiffre de jeu ici. Les valeurs lues sont
`certain` ; le sens d'un code d'aura, déduit des descriptions, reste `probable`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.pipeline.tables import Row

XP_BONUS_FILE = "xp_bonuses.json"
XP_BONUS_FILES = (XP_BONUS_FILE,)
SCHEMA_VERSION = 1
ACCESS = ("item", "legacy", "food", "camp", "none")
XP_BONUS_SCHEMAS = {"ItemSparse": "XpItemSparse"}  # niveau requis des objets en plus

Tables = Mapping[str, Sequence[Row]]


def xp_bonus_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    raise NotImplementedError


def xp_bonus_gate_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    raise NotImplementedError


def load_xp_bonus_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    raise NotImplementedError


def decode_xp_bonuses(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    raise NotImplementedError


def xp_bonuses_errors(doc: Mapping[str, Any]) -> list[str]:
    raise NotImplementedError
