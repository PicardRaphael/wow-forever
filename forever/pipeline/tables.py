"""Lecture typée des tables CSV du client (wago.tools) : chaque table déclare les colonnes utilisées et leur type.

Les noms de colonnes sont ceux du format de fichier (WoWDBDefs), pas des chiffres de jeu."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from forever.errors import DataSchemaError

Value = int | float | str
Row = Mapping[str, Value]


class ColumnNamesError(DataSchemaError):
    """Aucun des noms d'une colonne déclarée n'est dans l'en-tête du CSV (colonne renommée par le client)."""

    def __init__(self, table: str, missing: Sequence[tuple[str, ...]], header: Sequence[str], path: Path) -> None:
        self.table = table
        self.missing = tuple(tuple(names) for names in missing)
        self.header = tuple(header)
        self.path = path
        tried = " ; ".join(" ou ".join(names) for names in self.missing)
        super().__init__(
            f"{table} : colonne(s) absente(s) {tried} ({path}).",
            "ajouter le nouveau nom en tête de la liste de la colonne (forever/pipeline/tables.py et decode_rules.json)",
        )


def column_value(row: Row, names: str | Sequence[str]) -> Value:
    """Valeur du premier nom de `names` présent dans la ligne (`names` : un nom, ou une liste de noms de règles)."""
    tried = (names,) if isinstance(names, str) else tuple(names)
    for name in tried:
        if name in row:
            return row[name]
    raise DataSchemaError(f"Colonne absente de la ligne : {' ou '.join(tried)}.")


def propose_names(old_header: Sequence[str], new_header: Sequence[str], names: Sequence[str]) -> str | None:
    """Nom proposé pour une colonne absente : celui qui occupe, dans le nouvel en-tête, la place d'un de ses noms
    dans l'ancien en-tête (en-têtes de même longueur seulement) ; None sinon."""
    if len(old_header) != len(new_header):
        return None
    for name in names:
        if name in old_header:
            proposed = new_header[list(old_header).index(name)]
            return None if proposed in names or proposed in old_header else proposed
    return None


class Column(NamedTuple):
    name: str
    kind: type[int | float | str]
    aliases: tuple[str, ...] = ()  # anciens noms de la colonne (renommée par le client), du plus récent au plus ancien

    @property
    def names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


def _cols(spec: str) -> tuple[Column, ...]:
    """« ID:int Name_lang:str » -> colonnes typées ; « Nouveau|Ancien:float » : une colonne à plusieurs noms, le
    nouveau d'abord."""
    kinds: dict[str, type[int | float | str]] = {"int": int, "float": float, "str": str}
    columns = []
    for names, kind in (item.split(":") for item in spec.split()):
        first, *aliases = names.split("|")
        columns.append(Column(first, kinds[kind], tuple(aliases)))
    return tuple(columns)


TABLES: Mapping[str, tuple[Column, ...]] = {
    "SkillLineXTraitTree": _cols("ID:int SkillLineID:int TraitTreeID:int"),
    "TraitNode": _cols("ID:int TraitTreeID:int PosX:int PosY:int"),
    "TraitNodeXTraitNodeEntry": _cols("ID:int TraitNodeID:int TraitNodeEntryID:int _Index:int"),
    "TraitNodeEntry": _cols("ID:int TraitDefinitionID:int MaxRanks:int"),
    "TraitDefinition": _cols("ID:int SpellID:int OverrideName_lang:str OverrideDescription_lang:str"),
    "TraitDefinitionEffectPoints": _cols("ID:int TraitDefinitionID:int EffectIndex:int OperationType:int CurveID:int"),
    "TraitEdge": _cols("ID:int LeftTraitNodeID:int RightTraitNodeID:int Type:int"),
    "CurvePoint": _cols("ID:int CurveID:int Pos_0:float Pos_1:float OrderIndex:int"),
    "SkillLineAbility": _cols(
        "ID:int SkillLine:int Spell:int AcquireMethod:int ClassMask:int RaceMasks_0:int RaceMasks_1:int"
    ),
    "Spell": _cols("ID:int NameSubtext_lang:str Description_lang:str"),
    "SpellName": _cols("ID:int Name_lang:str"),
    "SpellEffect": _cols(
        "ID:int SpellID:int DifficultyID:int EffectIndex:int Effect:int EffectAura:int EffectAuraPeriod:int "
        "EffectBasePointsF:float EffectRealPointsPerLevel:float Variance:float EffectTriggerSpell:int EffectMiscValue_0:int "
        "EffectBonusCoefficient:float EffectMechanic:int ImplicitTarget_0:int ImplicitTarget_1:int"
    ),
    "SpellLevels": _cols("ID:int SpellID:int DifficultyID:int BaseLevel:int MaxLevel:int SpellLevel:int"),
    "SpellMisc": _cols(
        "ID:int SpellID:int DifficultyID:int Attributes_0:int Attributes_1:int CastingTimeIndex:int DurationIndex:int "
        "PvPDurationIndex:int RangeIndex:int SchoolMask:int"
    ),
    "SpellCastTimes": _cols("ID:int Base:int"),
    "SpellDuration": _cols("ID:int Duration:int"),
    "SpellPower": _cols("ID:int SpellID:int ManaCost:int PowerCostPct:float PowerType:int"),
    "SpellCooldowns": _cols(
        "ID:int SpellID:int DifficultyID:int RecoveryTime:int CategoryRecoveryTime:int StartRecoveryTime:int"
    ),
    "SpellAuraOptions": _cols("ID:int SpellID:int DifficultyID:int CumulativeAura:int ProcCharges:int"),
    # PV1 : tables des 9 classes, des races et des objets (decode_rules.json, class_tables).
    "ChrClasses": _cols("ID:int Name_lang:str Filename:str"),
    "SkillLine": _cols("ID:int DisplayName_lang:str CategoryID:int"),
    "SpellRange": _cols(
        "ID:int DisplayName_lang:str RangeMin_0:float RangeMin_1:float RangeMax_0:float RangeMax_1:float"
    ),
    "SpellCategories": _cols(
        "ID:int SpellID:int DifficultyID:int Category:int DiminishType:int DispelType:int Mechanic:int "
        "StartRecoveryCategory:int"
    ),
    "SpellCategory": _cols("ID:int Name_lang:str Flags:int"),
    "SpellMechanic": _cols("ID:int StateName_lang:str"),
    "SpellDispelType": _cols("ID:int Name_lang:str"),
    "SpellInterrupts": _cols(
        "ID:int SpellID:int DifficultyID:int InterruptFlags:int AuraInterruptFlags_0:int AuraInterruptFlags_1:int "
        "ChannelInterruptFlags_0:int ChannelInterruptFlags_1:int"
    ),
    "SpellClassOptions": _cols("ID:int SpellID:int SpellClassSet:int"),
    "SpellAuraRestrictions": _cols(
        "ID:int SpellID:int DifficultyID:int CasterAuraState:int TargetAuraState:int CasterAuraSpell:int "
        "TargetAuraSpell:int"
    ),
    "SpellShapeshift": _cols("ID:int SpellID:int ShapeshiftMask_0:int ShapeshiftMask_1:int"),
    "ChrRaces": _cols(
        "ID:int ClientFileString:str Name_lang:str Flags:int FactionID:int PlayableRaceBit:int Alliance:int"
    ),
    "CharBaseInfo": _cols("ID:int RaceID:int ClassID:int"),
    "SkillRaceClassInfo": _cols("ID:int SkillID:int ClassMask:int Flags:int RaceMasks_0:int RaceMasks_1:int"),
    "Item": _cols("ID:int ClassID:int SubclassID:int InventoryType:int"),
    "ItemSparse": _cols("ID:int Display_lang:str AllowableClass:int"),
    "ItemEffect": _cols(
        "ID:int TriggerType:int CoolDownMSec:int CategoryCoolDownMSec:int SpellCategoryID:int SpellID:int"
    ),
    "ItemXItemEffect": _cols("ID:int ItemEffectID:int ItemID:int"),
    # T08b, bloc A : ratios du personnage, XP, repos, constante d'armure, courbes (decode_rules.json, character_tables).
    # HPPerStamina : nom de la colonne Field_1_60_1_69876_005 dans les tables de 1.60.1.70235 (T08d).
    "PlayerExpectedStat": _cols(
        "ID:int Level:int ClassID:int ContentSetID:int BaseMana:float HPPerStamina|Field_1_60_1_69876_005:float "
        "CritPerAgility:float SpellCritPerIntellect:float"
    ),
    "LevelExperience": _cols("ID:int Level:int ContentSetID:int Experience:int"),
    "Exhaustion": _cols("ID:int Name_lang:str Xp:int Factor:float OutdoorHours:float InnHours:float Threshold:float"),
    "ExpectedStat": _cols("ID:int ExpansionID:int ContentSetID:int Lvl:int ArmorConstant:float CreatureHealth:float"),
    "GlobalCurve": _cols("ID:int CurveID:int Type:int Subtype:int"),
    "NumTalentsAtLevel": _cols("ID:int NumTalents:int"),
    "TraitCond": _cols(
        "ID:int CondType:int TraitTreeID:int TraitNodeGroupID:int TraitNodeID:int TraitCurrencyID:int "
        "SpentAmountRequired:int RequiredLevel:int"
    ),
    # CH0, bloc A : familiers du Chasseur (decode_rules.json, pet_tables). SkillLineAbility relue avec la chaîne des
    # rangs et la colonne sans nom du coût en points d'entraînement (pets.training_cost_column, sens probable).
    "PetSkillLineAbility": _cols(
        "ID:int SkillLine:int Spell:int AcquireMethod:int SupercedesSpell:int Field_5_5_4_67090_014_1:int"
    ),
    "CreatureFamily": _cols("ID:int Name_lang:str PetFoodMask:int PetTalentType:int SkillLine_0:int SkillLine_1:int"),
    "ItemPetFood": _cols("ID:int Name_lang:str"),
    "UiMap": _cols("ID:int Name_lang:str ParentUiMapID:int Type:int"),
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
            found = [(c, next((n for n in c.names if n in header), None)) for c in columns]
            missing = [c.names for c, name in found if name is None]
            if missing:
                raise ColumnNamesError(table, missing, header, path)
            index = [(c, header.index(name)) for c, name in found if name is not None]
            rows: list[dict[str, Value]] = []
            for line, cells in enumerate(reader, start=2):
                row: dict[str, Value] = {}
                for column, i in index:
                    raw = cells[i] if i < len(cells) else None
                    try:
                        if raw is None:
                            raise ValueError("cellule absente")
                        value = column.kind(raw)
                        for name in column.names:  # valeur rangée sous chacun des noms de la colonne
                            row[name] = value
                    except ValueError as exc:
                        raise DataSchemaError(
                            f"{table} : valeur {raw!r} invalide pour la colonne {column.name}, ligne {line} "
                            f"({column.kind.__name__} attendu, {path})."
                        ) from exc
                rows.append(row)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise DataSchemaError(f"{table} : fichier illisible ({path} : {exc}).") from exc
    return rows
