"""Lecteur local de la base de l'addon Questie installé (aucun réseau, aucun Lua exécuté).

Sources lues (fichiers source de l'addon, jamais les SavedVariables compilées) : `Questie_Camelot.toc` (version,
interface), `Database/Classic/classicNpcDB.lua` (PNJ, chaîne `[[return {…}]]` décrite par `npcKeys`),
`Database/QuestXP/DB/xpDB-classic.lua` (XP de quête). Questie charge sur Forever la base **Classic Era sans
correction Forever** : chaque valeur est communautaire, certitude `suppose`. La base n'est jamais copiée dans le
dépôt (décision 3 du plan T04)."""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path
from typing import Literal, NamedTuple

from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.lua_table import parse_lua_value

TOC_NAME = "Questie_Camelot.toc"
NPC_DB = Path("Database/Classic/classicNpcDB.lua")
QUEST_DB = Path("Database/Classic/classicQuestDB.lua")
XP_DB = Path("Database/QuestXP/DB/xpDB-classic.lua")
# Champs lus dans `npcKeys` (noms du fichier de Questie).
NPC_FIELDS = ("name", "minLevelHealth", "maxLevelHealth", "minLevel", "maxLevel", "rank", "zoneID")
_ENTRY = re.compile(r"^\[\d+\] = \{", re.MULTILINE)


class QuestieInfo(NamedTuple):
    version: str
    title: str
    interface: int
    npc_count: int
    quest_count: int | None


class QuestieNpc(NamedTuple):
    id: int
    name: str
    min_level_health: int
    max_level_health: int
    min_level: int
    max_level: int
    rank: int
    zone_id: int

    def hp_at(self, level: int) -> int | None:
        """PV au niveau donné, interpolés linéairement entre le niveau minimal et maximal (arrondi au plus proche,
        demi supérieur) ; None hors de l'intervalle."""
        if not self.min_level <= level <= self.max_level:
            return None
        if self.max_level == self.min_level:
            return self.min_level_health
        share = (level - self.min_level) / (self.max_level - self.min_level)
        return int(self.min_level_health + (self.max_level_health - self.min_level_health) * share + 0.5)


class QuestieDB:
    """Base Questie d'un dossier d'addon ; PNJ et XP lus à la première demande."""

    certainty: Literal["suppose"] = "suppose"

    def __init__(self, addon_dir: Path, info: QuestieInfo) -> None:
        self.addon_dir = addon_dir
        self.info = info

    @property
    def source(self) -> str:
        return (
            f"communautaire (Classic Era, aucune correction Forever), Questie {self.info.version} "
            f"{self.info.title}".rstrip()
        )

    def _read(self, rel: Path) -> str:
        path = self.addon_dir / rel
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataSchemaError(f"Questie : {path} illisible ({exc.strerror or exc}).") from exc

    @cached_property
    def _npcs(self) -> dict[int, QuestieNpc]:
        text = self._read(NPC_DB)
        keys = _npc_keys(text)
        start, end = text.find("[[return"), text.rfind("]]")
        if start < 0 or end < start:
            raise DataSchemaError(f"Questie : {NPC_DB} sans chaîne « [[return {{…}}]] ».")
        try:
            raw = parse_lua_value(text[start + len("[[return") : end])
        except ValueError as exc:
            raise DataSchemaError(f"Questie : {NPC_DB} : {exc}.") from exc
        if not isinstance(raw, dict):
            raise DataSchemaError(f"Questie : {NPC_DB} : table de PNJ attendue.")
        out: dict[int, QuestieNpc] = {}
        for npc_id, row in raw.items():
            if not isinstance(npc_id, int) or not isinstance(row, list | dict):
                continue
            fields = row if isinstance(row, dict) else dict(enumerate(row, start=1))
            values = [fields.get(keys[f]) for f in NPC_FIELDS]
            name, *numbers = values
            if not isinstance(name, str) or not all(isinstance(v, int) for v in numbers):
                continue  # PNJ incomplet (PV ou niveaux absents) : ignoré
            out[npc_id] = QuestieNpc(npc_id, name, *numbers)  # type: ignore[arg-type]
        return out

    def npcs(self) -> dict[int, QuestieNpc]:
        return self._npcs

    def npc(self, npc_id: int) -> QuestieNpc | None:
        return self._npcs.get(npc_id)

    @cached_property
    def _xp(self) -> dict[int, tuple[int, int]]:
        text = self._read(XP_DB)
        start = text.find("QuestXP.db = ")
        if start < 0:
            raise DataSchemaError(f"Questie : {XP_DB} sans « QuestXP.db = ».")
        try:
            raw = parse_lua_value(text[start + len("QuestXP.db = ") :])
        except ValueError as exc:
            raise DataSchemaError(f"Questie : {XP_DB} : {exc}.") from exc
        out: dict[int, tuple[int, int]] = {}
        if isinstance(raw, dict):
            for quest, pair in raw.items():
                if isinstance(quest, int) and isinstance(pair, list) and len(pair) == 2:
                    level, xp = pair
                    if isinstance(level, int) and isinstance(xp, int):
                        out[quest] = (level, xp)
        return out

    def quest_xp(self, quest_id: int) -> tuple[int, int] | None:
        """(niveau de la quête, XP) selon la base Classic de Questie."""
        return self._xp.get(quest_id)


def _npc_keys(text: str) -> dict[str, int]:
    keys = {m[1]: int(m[2]) for m in re.finditer(r"\['(\w+)'\]\s*=\s*(\d+)", text[: text.find("npcData")])}
    missing = [f for f in NPC_FIELDS if f not in keys]
    if missing:
        raise DataSchemaError(f"Questie : npcKeys sans {', '.join(missing)}.")
    return keys


def read_questie(addon_dir: Path) -> QuestieDB:
    """Base Questie du dossier (PathNotFoundError si l'addon ou son `.toc` Camelot manque)."""
    toc = addon_dir / TOC_NAME
    if not toc.is_file():
        raise PathNotFoundError(
            "Addon Questie", str(addon_dir), "donner le dossier de l'addon (Interface/AddOns/Questie) avec --questie"
        )
    text = toc.read_text(encoding="utf-8")
    version = re.search(r"^## Version:\s*(\S+)\s*(.*)$", text, re.MULTILINE)
    interface = re.search(r"^## Interface:\s*(\d+)", text, re.MULTILINE)
    if version is None or interface is None:
        raise DataSchemaError(f"Questie : {toc} sans ## Version ou ## Interface.")
    npc_file, quest_file = addon_dir / NPC_DB, addon_dir / QUEST_DB
    npc_count = len(_ENTRY.findall(npc_file.read_text(encoding="utf-8"))) if npc_file.is_file() else 0
    quest_count = len(_ENTRY.findall(quest_file.read_text(encoding="utf-8"))) if quest_file.is_file() else None
    info = QuestieInfo(version[1], version[2].strip(), int(interface[1]), npc_count, quest_count)
    return QuestieDB(addon_dir, info)


def read_journey(sv: Path, guid: str) -> list[tuple[int, int]]:
    """(heure Unix, niveau atteint) des événements `Level` du carnet de Questie pour le personnage `guid`, triés ;
    tous les blocs `char` du GUID sont réunis (Questie peut en écrire plusieurs, dont un « Unknown »)."""
    raise NotImplementedError
