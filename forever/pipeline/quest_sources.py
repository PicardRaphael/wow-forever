"""Lecteurs locaux des sources de quêtes de Forever (T04d, bloc D), sans réseau ni exécution de Lua.

Chaque lecteur rend les quêtes d'un addon installé (`Interface/AddOns`) sous une forme commune : identifiant ->
champs présents dans la source (`name`, `level`, `min_level`, `faction`, `races`, `classes`, `map`, `giver`,
`turn_in`, `objectives`, `prereq_all`, `prereq_any`, `next`, `exclusive`, `dungeon`, `xp`, `xp_text`, `rewards`,
`new`, `chain`). Une position est `{"map": uiMapID, "x": %, "y": %}` (plus `name` et `npc` quand la source les donne).
Rien n'est deviné : un champ absent de la source n'est pas rendu. Sources :

- Questie (`classicQuestDB.lua`, `classicNpcDB.lua`, `xpDB-classic.lua`, `areaIdToUiMapId.lua`, corrections
  `classicQuestFixes.lua` appliquées aux champs numériques), base Classic Era ;
- `QuestieForeverDB` (SavedVariable de Questie : quêtes apprises en jeu, relevé du joueur) ;
- Naowh Forever : Completo (`NaowhForever_Discovery/QuestList/Data/Quests.lua`), Journeys
  (`NaowhForever_Journeys/Data/QuestSpots.lua`), Dungeon Journal (`NaowhForever_DungeonJournal/Data/Quests.lua`) ;
- Forever Guide (`ForeverGuide/DungeonData.lua`) ;
- ForeverDungeonJournal (`Data/QuestRewards.lua`, `Data/Dungeons.lua`) ;
- GearQuestForever (récompenses par objet, nom de quête sans identifiant : rapprochées par nom et zone dans
  `forever/quests.py`).

Aucun chiffre de jeu ici : les positions de champs sont celles du format de chaque fichier."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

Facts = dict[str, Any]

SOURCE_LABELS = {
    "client": "client (questcache.wdb et QuestXP)",
    "questie_forever": "Questie, quêtes apprises en jeu (QuestieForeverDB)",
    "forever_guide": "Forever Guide",
    "completo": "Naowh Forever, Completo",
    "naowh_dj": "Naowh Forever, Dungeon Journal",
    "journeys": "Naowh Forever, Journeys",
    "fdj": "ForeverDungeonJournal",
    "gearquest": "GearQuestForever",
    "questie": "Questie (Classic Era, corrections comprises)",
}


class SourceInfo(NamedTuple):
    key: str  # clé de SOURCE_LABELS
    addon: str  # dossier de l'addon (ou fichier de SavedVariable)
    version: str | None
    certainty: str  # « suppose » pour un addon, « probable » pour un relevé du joueur
    files: tuple[Path, ...]  # fichiers lus (empreinte du cache des quêtes)


class SourceQuests(NamedTuple):
    info: SourceInfo
    quests: dict[int, Facts]
    notes: list[str]


class GearReward(NamedTuple):
    item: int
    item_name: str
    quest_name: str
    zone: str | None


class QuestieExtras(NamedTuple):
    """Données de Questie utiles à la fusion : zones (AreaTable -> uiMapID) et noms de zones."""

    area_to_map: dict[int, int]


def source_files(addons_dir: Path, wtf_dir: Path | None) -> list[Path]:
    """Fichiers que les lecteurs liraient (présents seulement), pour l'empreinte du cache."""
    raise NotImplementedError


def read_questie_quests(addons_dir: Path) -> tuple[SourceQuests, QuestieExtras] | None:
    raise NotImplementedError


def read_questie_forever(wtf_dir: Path) -> SourceQuests | None:
    raise NotImplementedError


def read_completo(addons_dir: Path) -> tuple[SourceQuests, dict[int, list[int]], list[list[list[int]]]] | None:
    """Quêtes de Completo, quêtes de chaque zone (uiMapID -> ID) et chaînes (étapes ordonnées de groupes d'ID)."""
    raise NotImplementedError


def read_journeys(addons_dir: Path) -> SourceQuests | None:
    raise NotImplementedError


def read_naowh_dj(addons_dir: Path) -> SourceQuests | None:
    raise NotImplementedError


def read_forever_guide(addons_dir: Path) -> SourceQuests | None:
    raise NotImplementedError


def read_fdj(addons_dir: Path) -> SourceQuests | None:
    raise NotImplementedError


def read_gearquest(addons_dir: Path) -> tuple[SourceInfo, list[GearReward]] | None:
    raise NotImplementedError
