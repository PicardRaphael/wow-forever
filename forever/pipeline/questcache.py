"""Lecture locale du cache des quêtes du client (`Cache/WDB/<locale>/questcache.wdb`, T04d, bloc B).

Le client écrit un enregistrement par quête **vue** (offerte, acceptée, rendue ou consultée) : en-tête du fichier
(signature `WQST` écrite à l'envers, build, locale à l'envers, deux champs de format), puis pour chaque quête son
identifiant, la longueur de l'enregistrement et l'enregistrement, jusqu'à un couple (0, 0). Seuls les champs
numériques du début sont lus (niveau, niveau requis, zone, quête suivante, difficulté et multiplicateur d'XP,
argent) ; les chaînes de texte qui suivent sont ignorées.

Disposition établie le 2026-10-13 sur les 203 quêtes du cache de 1.60.1.70338 : niveau, niveau requis et zone égaux
à `classicQuestDB.lua` de Questie pour 122 des 123 quêtes Classic vues (l'écart, 421, est une quête retouchée par
Forever), et XP = `QuestXP[niveau][difficulté]` × multiplicateur égale à `xpDB-classic.lua` pour 122 des 123 (l'écart,
5725, est une quête de donjon au multiplicateur relevé). Certitude `probable` jusqu'au recoupement par `xpReward` en
jeu (question LVL6). Les positions ci-dessous décrivent le format du fichier, pas des valeurs de jeu."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import NamedTuple

QUESTCACHE_PATH = ("Cache", "WDB", "{locale}", "questcache.wdb")
MAGIC = b"TSQW"  # « WQST » écrit à l'envers (entier de 4 octets en petit-boutiste)
HEADER = struct.Struct("<4sI4sIII")  # signature, build, locale à l'envers, taille et version du format, réservé
ENTRY = struct.Struct("<II")  # identifiant de la quête, longueur de l'enregistrement
# Position (en mots de 4 octets) de chaque champ lu au début d'un enregistrement ; « f » : nombre à virgule.
FIELDS: dict[str, tuple[int, str]] = {
    "id": (0, "i"),
    "type": (1, "i"),
    "level": (2, "i"),
    "min_level": (4, "i"),
    "sort_id": (6, "i"),
    "next_quest": (9, "i"),
    "xp_difficulty": (10, "i"),
    "xp_multiplier": (11, "f"),
    "money": (12, "i"),
    "money_difficulty": (13, "i"),
    "money_multiplier": (14, "f"),
}
MIN_RECORD = 4 * (max(index for index, _ in FIELDS.values()) + 1)
FLOAT_DIGITS = 6  # arrondi d'un nombre à virgule de 4 octets (2.0250000953… -> 2.025), paramètre de lecture


class QuestRecord(NamedTuple):
    id: int
    type: int
    level: int
    min_level: int
    sort_id: int  # > 0 : zone (AreaTable), < 0 : catégorie (QuestSort), comme `zoneOrSort` de Questie
    next_quest: int
    xp_difficulty: int  # colonne de la table QuestXP
    xp_multiplier: float
    money: int
    money_difficulty: int
    money_multiplier: float


class QuestCache(NamedTuple):
    build: int
    locale: str
    records: dict[int, QuestRecord]


def parse_questcache(raw: bytes) -> QuestCache:
    """Cache des quêtes lu depuis ses octets ; DataSchemaError si la signature, un enregistrement ou la fin manque."""
    raise NotImplementedError


def read_questcache(path: Path) -> QuestCache:
    """Cache des quêtes du fichier `path` (DataSchemaError s'il est illisible ou mal formé)."""
    raise NotImplementedError


def questcache_path(wow_dir: Path, locale: str = "enUS") -> Path:
    return wow_dir.joinpath(*(part.format(locale=locale) for part in QUESTCACHE_PATH))
