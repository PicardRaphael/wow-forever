"""Lecture typée des tables CSV du client (wago.tools) : chaque table déclare les colonnes utilisées et leur type.

Les noms de colonnes sont ceux du format de fichier (WoWDBDefs), pas des chiffres de jeu."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

from forever.errors import DataSchemaError

Value = int | float | str
Row = Mapping[str, Value]


class Column(NamedTuple):
    name: str
    kind: type[int | float | str]


def _cols(spec: str) -> tuple[Column, ...]:
    """« ID:int Name_lang:str » -> colonnes typées."""
    kinds: dict[str, type[int | float | str]] = {"int": int, "float": float, "str": str}
    return tuple(Column(name, kinds[kind]) for name, kind in (item.split(":") for item in spec.split()))


TABLES: Mapping[str, tuple[Column, ...]] = {
    "SkillLineXTraitTree": _cols("ID:int SkillLineID:int TraitTreeID:int"),
    "TraitNode": _cols("ID:int TraitTreeID:int PosX:int PosY:int"),
    "TraitNodeXTraitNodeEntry": _cols("ID:int TraitNodeID:int TraitNodeEntryID:int _Index:int"),
    "TraitNodeEntry": _cols("ID:int TraitDefinitionID:int MaxRanks:int"),
    "TraitDefinition": _cols("ID:int SpellID:int OverrideName_lang:str OverrideDescription_lang:str"),
    "TraitDefinitionEffectPoints": _cols("ID:int TraitDefinitionID:int EffectIndex:int OperationType:int CurveID:int"),
    "TraitEdge": _cols("ID:int LeftTraitNodeID:int RightTraitNodeID:int"),
    "CurvePoint": _cols("ID:int CurveID:int Pos_0:float Pos_1:float OrderIndex:int"),
    "SkillLineAbility": _cols("ID:int SkillLine:int Spell:int AcquireMethod:int"),
    "Spell": _cols("ID:int NameSubtext_lang:str Description_lang:str"),
    "SpellName": _cols("ID:int Name_lang:str"),
    "SpellEffect": _cols(
        "ID:int SpellID:int DifficultyID:int EffectIndex:int Effect:int EffectAura:int EffectAuraPeriod:int "
        "EffectBasePointsF:float EffectRealPointsPerLevel:float Variance:float EffectTriggerSpell:int EffectMiscValue_0:int"
    ),
    "SpellLevels": _cols("ID:int SpellID:int DifficultyID:int BaseLevel:int MaxLevel:int SpellLevel:int"),
    "SpellMisc": _cols("ID:int SpellID:int DifficultyID:int Attributes_1:int CastingTimeIndex:int DurationIndex:int"),
    "SpellCastTimes": _cols("ID:int Base:int"),
    "SpellDuration": _cols("ID:int Duration:int"),
    "SpellPower": _cols("ID:int SpellID:int ManaCost:int PowerCostPct:float PowerType:int"),
    "SpellCooldowns": _cols(
        "ID:int SpellID:int DifficultyID:int RecoveryTime:int CategoryRecoveryTime:int StartRecoveryTime:int"
    ),
    "SpellAuraOptions": _cols("ID:int SpellID:int DifficultyID:int CumulativeAura:int ProcCharges:int"),
}


def read_table(path: Path, table: str) -> list[dict[str, Value]]:
    """Lignes typées d'une table (colonnes déclarées seulement) ; DataSchemaError si une colonne manque ou si une
    valeur n'a pas le type déclaré (le message nomme la table, la colonne et la ligne)."""
    columns = TABLES.get(table)
    if columns is None:
        raise DataSchemaError(f"Table du client non déclarée : {table} ({path}).")
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            missing = [c.name for c in columns if c.name not in header]
            if missing:
                raise DataSchemaError(f"{table} : colonne(s) absente(s) {', '.join(missing)} ({path}).")
            index = [(c, header.index(c.name)) for c in columns]
            rows: list[dict[str, Value]] = []
            for line, cells in enumerate(reader, start=2):
                row: dict[str, Value] = {}
                for column, i in index:
                    raw = cells[i] if i < len(cells) else None
                    try:
                        if raw is None:
                            raise ValueError("cellule absente")
                        row[column.name] = column.kind(raw)
                    except ValueError as exc:
                        raise DataSchemaError(
                            f"{table} : valeur {raw!r} invalide pour la colonne {column.name}, ligne {line} "
                            f"({column.kind.__name__} attendu, {path})."
                        ) from exc
                rows.append(row)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise DataSchemaError(f"{table} : fichier illisible ({path} : {exc}).") from exc
    return rows
