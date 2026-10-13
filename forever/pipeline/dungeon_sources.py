"""Lecteurs locaux des donjons des addons de Forever (DJ1, bloc B), sans réseau ni exécution de Lua.

Chaque lecteur rend les donjons d'un addon installé (`Interface/AddOns`) sous une forme commune, clé = identifiant
d'instance en texte (`"389"`) quand la source le donne, sinon `"name:<nom>"` (ou `"area:<AreaTable>"` pour Zone
Info: Forever) ; rattachement fait dans `forever/dungeons.py`. Champs présents dans la source seulement : `name`,
`map`, `levels` (`min`, `max`), `access_level`, `entrance` (`map` uiMapID, `x`, `y` en %), `new`, `closed`,
`bosses` (`name`, `npc`, `level`, `encounter`, `loot` : `item`, `rate` en fraction, `classic`), `quests`,
`trash_npcs`, `access`. Rien n'est deviné. Les SavedVariables de Naowh Forever (`journalRun`, `journalKills`,
`journalLoot`, `instanceTrackerChars`) sont lues sans jamais garder les noms de joueurs (`rolls`, `team`, `drops`,
`group`, `name`). AlexAtlasLoot n'est jamais lu (licence, décision 229). Aucun chiffre de jeu ici."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from forever.pipeline.quest_sources import Facts, SourceInfo

DUNGEON_SOURCE_LABELS = {
    "naowh_dj": "Naowh Forever, Dungeon Journal",
    "fojji": "FojjiCore, Dungeon Journal (recoupement)",
    "fdj": "ForeverDungeonJournal",
    "forever_guide": "Forever Guide",
    "atlasloot": "AtlasLoot Classic Forever",
    "companion": "Forever Companion",
    "zoneinfo": "Zone Info: Forever",
}


class SourceDungeons(NamedTuple):
    info: SourceInfo
    dungeons: dict[str, Facts]
    prereqs: dict[int, list[Any]]  # quête -> prérequis (une sous-liste : l'un des éléments suffit)
    min_levels: dict[int, int]  # quête -> niveau minimum de prise
    notes: list[str]


class NaowhRuns(NamedTuple):
    info: SourceInfo
    runs: list[dict[str, Any]]  # instance_id, name, entered, left, seconds, level, xp, deaths, source
    kills: dict[int, dict[str, Any]]  # rencontre -> took (durées), n
    loot: list[dict[str, Any]]  # item, dungeon, boss, at


def read_naowh_journal(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def read_naowh_runs(wtf_dir: Path) -> NaowhRuns | None:
    raise NotImplementedError


def read_fojji(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def read_fdj_dungeons(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def read_guide_dungeons(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def read_atlasloot(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def read_companion(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def read_zoneinfo(addons_dir: Path) -> SourceDungeons | None:
    raise NotImplementedError


def dungeon_source_files(addons_dir: Path, wtf_dir: Path | None) -> list[Path]:
    """Fichiers que les lecteurs liraient (présents seulement), pour l'empreinte du cache des donjons."""
    raise NotImplementedError
