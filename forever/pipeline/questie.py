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
from typing import Literal, NamedTuple, TypedDict

from forever.engine.leveling import USEFUL_COLORS, level_band, quest_color
from forever.engine.model import GameData
from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.lua_table import parse_lua_value

TOC_NAME = "Questie_Camelot.toc"
NPC_DB = Path("Database/Classic/classicNpcDB.lua")
QUEST_DB = Path("Database/Classic/classicQuestDB.lua")
XP_DB = Path("Database/QuestXP/DB/xpDB-classic.lua")
DUNGEON_DB = Path("Database/Zones/data/dungeons.lua")
ZONE_NAMES = Path("Localization/lookups/lookupZones.lua")
# Champs lus dans `questKeys` (noms du fichier de Questie).
QUEST_FIELDS = ("name", "requiredLevel", "questLevel", "requiredRaces", "requiredClasses", "zoneOrSort")
# Masques du format de Questie : bit (identifiant - 1) des races (ChrRaces) et des classes (ChrClasses).
FACTION_RACES = {"horde": (2, 5, 6, 8), "alliance": (1, 3, 4, 7)}
FACTION_MASKS = {faction: sum(1 << (race - 1) for race in races) for faction, races in FACTION_RACES.items()}
CLASS_IDS = {"mage": 8}
CLASS_MASKS = {name: 1 << (class_id - 1) for name, class_id in CLASS_IDS.items()}
# Champs lus dans `npcKeys` (noms du fichier de Questie).
NPC_FIELDS = ("name", "minLevelHealth", "maxLevelHealth", "minLevel", "maxLevel", "rank", "zoneID")
_ENTRY = re.compile(r"^\[\d+\] = \{", re.MULTILINE)
# Ligne de `dungeons.lua` : [zone] = {"nom", {alternatifs} ou nil, zone parente, …}
_DUNGEON = re.compile(
    r'^\s*\[(?P<id>\d+)\] = \{"(?P<name>[^"]+)",(?P<alt>nil|\{[\d, ]*\}),(?P<parent>\d+),', re.MULTILINE
)
NPC_LEVEL_QUANTILES = (0.1, 0.9)  # plage des niveaux des PNJ d'une zone : 10e et 90e percentiles (méthode)
NORMAL_RANK = 0


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


class QuestieQuest(NamedTuple):
    id: int
    name: str
    required_level: int
    quest_level: int
    required_races: int  # 0 : toutes les races
    required_classes: int  # 0 : toutes les classes
    zone_or_sort: int  # > 0 : zone (AreaTable), < 0 : catégorie (QuestSort)


class QuestieDungeon(NamedTuple):
    area_id: int
    name: str
    alternative_ids: tuple[int, ...]
    parent_zone: int


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

    @cached_property
    def _quests(self) -> dict[int, QuestieQuest]:
        text = self._read(QUEST_DB)
        keys = _keys(text, "questData", QUEST_FIELDS, "questKeys")
        start, end = text.find("[[return"), text.rfind("]]")
        if start < 0 or end < start:
            raise DataSchemaError(f"Questie : {QUEST_DB} sans chaîne « [[return {{…}}]] ».")
        try:
            raw = parse_lua_value(text[start + len("[[return") : end])
        except ValueError as exc:
            raise DataSchemaError(f"Questie : {QUEST_DB} : {exc}.") from exc
        if not isinstance(raw, dict):
            raise DataSchemaError(f"Questie : {QUEST_DB} : table de quêtes attendue.")
        out: dict[int, QuestieQuest] = {}
        for quest_id, row in raw.items():
            if not isinstance(quest_id, int) or not isinstance(row, list | dict):
                continue
            fields = row if isinstance(row, dict) else dict(enumerate(row, start=1))
            name, required, level, races, classes, zone = (fields.get(keys[f]) for f in QUEST_FIELDS)
            if not isinstance(name, str) or not all(isinstance(v, int) for v in (required, level, zone)):
                continue  # quête incomplète (niveau ou zone absents) : ignorée
            out[quest_id] = QuestieQuest(
                quest_id,
                name,
                required,  # type: ignore[arg-type]
                level,  # type: ignore[arg-type]
                races if isinstance(races, int) else 0,
                classes if isinstance(classes, int) else 0,
                zone,  # type: ignore[arg-type]
            )
        return out

    def quests(self) -> dict[int, QuestieQuest]:
        """Quêtes de `classicQuestDB.lua` (champs `QUEST_FIELDS`), lues à la première demande."""
        return self._quests

    @cached_property
    def _dungeons(self) -> dict[int, QuestieDungeon]:
        out: dict[int, QuestieDungeon] = {}
        for m in _DUNGEON.finditer(self._read(DUNGEON_DB)):
            alternatives = tuple(int(x) for x in re.findall(r"\d+", m["alt"])) if m["alt"] != "nil" else ()
            out[int(m["id"])] = QuestieDungeon(int(m["id"]), m["name"], alternatives, int(m["parent"]))
        return out

    def dungeons(self) -> dict[int, QuestieDungeon]:
        """Donjons de `dungeons.lua` : zone, nom, identifiants de zone alternatifs, zone parente."""
        return self._dungeons

    @cached_property
    def _zone_names(self) -> dict[int, str]:
        text = self._read(ZONE_NAMES)
        start = text.find("l10n.zoneLookup = {")
        if start < 0:
            raise DataSchemaError(f"Questie : {ZONE_NAMES} sans « l10n.zoneLookup ».")
        end = text.find("l10n.zoneCategoryLookup", start)
        section = text[start : end if end > 0 else len(text)]
        out: dict[int, str] = {}
        for m in re.finditer(r'\[(-?\d+)\]\s*=\s*"([^"]*)"', section):
            out.setdefault(int(m[1]), m[2])
        return out

    def battlegrounds(self) -> frozenset[int]:
        """Zones des champs de bataille (catégorie « Battlegrounds » de `lookupZones.lua`)."""
        raise NotImplementedError

    def zone_names(self) -> dict[int, str]:
        """Noms anglais des zones (`lookupZones.lua`, table `zoneLookup`)."""
        return self._zone_names

    def quest_xp(self, quest_id: int) -> tuple[int, int] | None:
        """(niveau de la quête, XP) selon la base Classic de Questie."""
        return self._xp.get(quest_id)


def _keys(text: str, data: str, fields: tuple[str, ...], name: str) -> dict[str, int]:
    """Positions des champs `fields` dans l'en-tête `name` (avant la table `data`)."""
    keys: dict[str, int] = {}
    for m in re.finditer(r"^\s*\['(\w+)'\]\s*=\s*(\d+)", text[: text.find(data)], re.MULTILINE):
        keys.setdefault(m[1], int(m[2]))  # sous-champs commentés (--) ignorés : ancrés en début de ligne
    missing = [f for f in fields if f not in keys]
    if missing:
        raise DataSchemaError(f"Questie : {name} sans {', '.join(missing)}.")
    return keys


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


# SavedVariable de Questie (`WTF/Account/<COMPTE>/SavedVariables/Questie.lua`) : données personnelles de
# l'utilisateur, lues localement (décision 3 du plan T04b). Le fichier contient des chaînes compressées (octets
# quelconques) : il est lu octet pour octet (latin-1) et parcouru table par table, sans analyser le reste.
JOURNEY_VARIABLE = "QuestieConfig"
_VARIABLE = re.compile(rf"^{JOURNEY_VARIABLE}\s*=\s*\{{", re.MULTILINE)
_KEY = re.compile(r'\[("(?:[^"\\]|\\.)*"|-?\d+)\]\s*=\s*')
_BARE_KEY = re.compile(r"[A-Za-z_]\w*\s*=\s*")  # clé nue (`foo = …`), valeur ignorée


def _string_end(text: str, i: int) -> int:
    """Indice qui suit la chaîne ouverte en `i` (guillemet), échappements compris."""
    i += 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        i += 1
    raise ValueError("chaîne non terminée")


def _table_end(text: str, i: int) -> int:
    """Indice qui suit la table ouverte en `i` (accolade), chaînes et commentaires sautés."""
    depth = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            i = _string_end(text, i)
            continue
        if text.startswith("--", i):
            i = text.find("\n", i)
            i = len(text) if i < 0 else i
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("table non terminée")


def _items(text: str, start: int, end: int) -> dict[str, tuple[int, int]]:
    """Clés en chaîne du premier niveau de la table `text[start:end]` (accolades comprises) -> étendue de la valeur."""
    out: dict[str, tuple[int, int]] = {}
    i = start + 1
    while i < end - 1:
        c = text[i]
        if c.isspace() or c == ",":
            i += 1
            continue
        if text.startswith("--", i):
            i = text.find("\n", i)
            i = end if i < 0 else i
            continue
        key = None
        m = _KEY.match(text, i)
        if m:
            key = m[1][1:-1] if m[1].startswith('"') else None
            i = m.end()
        elif bare := _BARE_KEY.match(text, i):
            i = bare.end()
        if text[i] == "{":
            j = _table_end(text, i)
        elif text[i] == '"':
            j = _string_end(text, i)
        else:
            j = i
            while j < end - 1 and text[j] not in ",\n}":
                j += 1
        if key is not None:
            out[key] = (i, j)
        i = max(j, i + 1)  # toujours avancer : un jeton inattendu ne bloque jamais la lecture
    return out


def read_journey(sv: Path, guid: str) -> list[tuple[int, int]]:
    """(heure Unix, niveau atteint) des événements `Level` du carnet de Questie pour le personnage `guid`, triés ;
    tous les blocs `char` du GUID sont réunis (Questie peut en écrire plusieurs, dont un « Unknown »).
    PathNotFoundError si le fichier manque ; DataSchemaError s'il ne contient pas `QuestieConfig`."""
    if not sv.is_file():
        raise PathNotFoundError(
            "SavedVariables de Questie",
            str(sv),
            "donner WTF/Account/<COMPTE>/SavedVariables/Questie.lua (écrit au /reload ou à la déconnexion)",
        )
    text = sv.read_bytes().decode("latin-1")
    found = _VARIABLE.search(text)
    if found is None:
        raise DataSchemaError(f"{sv.name} : variable {JOURNEY_VARIABLE} absente.")
    out: list[tuple[int, int]] = []
    try:
        root = found.end() - 1
        chars = _items(text, root, _table_end(text, root)).get("char")
        for start, end in _items(text, *chars).values() if chars and text[chars[0]] == "{" else []:
            if text[start] != "{":
                continue
            fields = _items(text, start, end)
            g, journey = fields.get("guid"), fields.get("journey")
            if g is None or journey is None or text[g[0] + 1 : g[1] - 1] != guid:
                continue
            events = parse_lua_value(text[journey[0] : journey[1]])
            for e in events if isinstance(events, list) else []:
                if not isinstance(e, dict) or e.get("Event") != "Level":
                    continue
                ts, level = e.get("Timestamp"), e.get("NewLevel")
                if isinstance(ts, int) and isinstance(level, int):
                    out.append((ts, level))
    except ValueError as exc:
        raise DataSchemaError(f"{sv.name} : {exc}.") from exc
    return sorted(out)


class ZoneEntry(TypedDict):
    area_id: int
    name: str
    kind: str  # zone ou dungeon
    useful_quests: int
    by_color: dict[str, int]
    quests: list[int]  # quêtes disponibles (faction, classe, niveau requis)
    quest_levels: list[int] | None  # [min, max] des quêtes de la zone pour la faction et la classe
    npc_levels: list[int] | None  # [10e, 90e percentile] des PNJ normaux de la zone


class ZoneAdvice(TypedDict):
    level: int
    faction: str | None
    band: list[int]
    zones: list[ZoneEntry]
    dungeons: list[ZoneEntry]
    certainty: str
    source: str
    notes: list[str]


def quest_available(quest: QuestieQuest, level: int, faction: str | None, player_class: str) -> bool:
    """Quête prenable : race de la faction (toutes si `faction` est None), classe, niveau requis atteint."""
    return _eligible(quest, faction, player_class) and quest.required_level <= level


def _eligible(quest: QuestieQuest, faction: str | None, player_class: str) -> bool:
    """Quête ouverte à la faction et à la classe, quel que soit le niveau."""
    if faction is not None and quest.required_races and not quest.required_races & FACTION_MASKS[faction]:
        return False
    return not quest.required_classes or bool(quest.required_classes & CLASS_MASKS[player_class])


def _nearest_rank(values: list[int], q: float) -> int:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * q)]


def zones_for_level(
    db: QuestieDB, gd: GameData, level: int, *, faction: str | None = None, player_class: str = "mage"
) -> ZoneAdvice:
    """Zones et donjons classés par nombre de quêtes utiles (vertes, jaunes, orange) au niveau `level`, avec les
    plages de niveau des quêtes (faction et classe) et des PNJ normaux de la zone. Certitude `suppose` : base Classic
    Era de Questie sans correction Forever, couleurs de la règle de Classic (`leveling.quest_band`).

    Registre : I7"""
    if faction is not None and faction not in FACTION_MASKS:
        raise ValueError(f"faction inconnue « {faction} » ({' ou '.join(FACTION_MASKS)} attendue)")
    if player_class not in CLASS_MASKS:
        raise ValueError(f"classe inconnue « {player_class} » ({', '.join(CLASS_MASKS)} attendue)")
    dungeons = db.dungeons()
    dungeon_of = {area: area for area in dungeons}
    for area, d in dungeons.items():
        dungeon_of.update({alt: area for alt in d.alternative_ids})
    names = db.zone_names()
    grouped: dict[int, list[QuestieQuest]] = {}
    for q in db.quests().values():
        if q.zone_or_sort <= 0 or not _eligible(q, faction, player_class):
            continue
        grouped.setdefault(dungeon_of.get(q.zone_or_sort, q.zone_or_sort), []).append(q)
    npc_levels: dict[int, list[int]] = {}
    for npc in db.npcs().values():
        if npc.rank == NORMAL_RANK:
            npc_levels.setdefault(npc.zone_id, []).extend((npc.min_level, npc.max_level))
    zones: list[ZoneEntry] = []
    instances: list[ZoneEntry] = []
    for area, quests in grouped.items():
        available = [q for q in quests if quest_available(q, level, faction, player_class)]
        colors = {c: 0 for c in ("gray", "green", "yellow", "orange", "red")}
        for q in available:
            colors[quest_color(gd, level, q.quest_level)] += 1
        levels = [q.quest_level for q in quests]
        npcs = npc_levels.get(area)
        is_dungeon = area in dungeons
        entry: ZoneEntry = {
            "area_id": area,
            "name": dungeons[area].name if is_dungeon else names.get(area, f"zone {area}"),
            "kind": "dungeon" if is_dungeon else "zone",
            "useful_quests": sum(colors[c] for c in USEFUL_COLORS),
            "by_color": colors,
            "quests": sorted(q.id for q in available),
            "quest_levels": [min(levels), max(levels)],
            "npc_levels": [_nearest_rank(npcs, p) for p in NPC_LEVEL_QUANTILES] if npcs else None,
        }
        (instances if is_dungeon else zones).append(entry)

    def rank(e: ZoneEntry) -> tuple[int, str]:
        return -e["useful_quests"], e["name"]

    return {
        "level": level,
        "faction": faction,
        "band": list(level_band(gd, level)),
        "zones": sorted((z for z in zones if z["quests"]), key=rank),
        "dungeons": sorted((d for d in instances if d["useful_quests"]), key=rank),
        "certainty": db.certainty,
        "source": db.source,
        "notes": [
            "noms de zones en anglais (Questie ne fournit pas de table française)",
            "quêtes et PNJ de la base Classic Era de Questie, sans correction Forever",
            "couleurs de quête : règle de Classic (leveling.quest_band, suppose) ; utiles = vertes, jaunes, orange",
            f"quêtes disponibles : faction {faction or 'toutes'}, classe {player_class}, niveau requis atteint",
        ],
    }
