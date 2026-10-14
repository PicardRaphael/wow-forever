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
- Forever Guide (`ForeverGuide/DungeonData.lua`, `DalaranData.lua`, `ChainData.lua`) ; livres de Naowh Discovery
  (`Data/Books.lua`) et chaînes du Dungeon Journal de Naowh (`Data/QuestChains.lua`), RX1 ;
- ForeverDungeonJournal (`Data/QuestRewards.lua`, `Data/Dungeons.lua`) ;
- GearQuestForever (récompenses par objet, nom de quête sans identifiant : rapprochées par nom et zone dans
  `forever/quests.py`).

Aucun chiffre de jeu ici : les positions de champs sont celles du format de chaque fichier."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError
from forever.pipeline.lua_table import parse_lua_value, parse_lua_value_at
from forever.pipeline.questie import FACTION_MASKS, TOC_NAME

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
    "factoruide": "Factoruide (recoupement local, quêtes vues seulement chez lui)",
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


QUESTIE = "Questie"
QUESTIE_QUESTS = "Database/Classic/classicQuestDB.lua"
QUESTIE_NPCS = "Database/Classic/classicNpcDB.lua"
QUESTIE_XP = "Database/QuestXP/DB/xpDB-classic.lua"
QUESTIE_FIXES = "Database/Corrections/classicQuestFixes.lua"
QUESTIE_ZONES = "Database/Zones/data/areaIdToUiMapId.lua"
COMPLETO = ("NaowhForever_Discovery", "QuestList/Data/Quests.lua")
JOURNEYS = ("NaowhForever_Journeys", "Data/QuestSpots.lua")
NAOWH_DJ = ("NaowhForever_DungeonJournal", "Data/Quests.lua")
GUIDE = ("ForeverGuide", "DungeonData.lua")
GUIDE_DALARAN = "DalaranData.lua"  # DJ1 : quêtes de City of Dalaran, ajoutées après DungeonData.lua
GUIDE_CHAINS = "ChainData.lua"  # RX1 : chaînes importantes (sac de couchage, clés) et leurs quêtes
COMPLETO_BOOKS = "Data/Books.lua"  # RX1 : livres de la bibliothèque (Naowh Discovery)
NAOWH_DJ_CHAINS = "Data/QuestChains.lua"  # RX1 : chaînes, niveaux minimaux, noms (Dungeon Journal de Naowh)
FDJ_CHAINS = "Data/QuestChains.lua"  # RX1 : prérequis requis et leurs détails (ForeverDungeonJournal)
FDJ_MAPS = "Data/QuestMaps.lua"  # RX1 : positions des donneurs (ForeverDungeonJournal)
FDJ_UNIT_TO_PERCENT = 100.0  # format : coordonnées de ForeverDungeonJournal écrites de 0 à 1
FDJ_REWARDS = ("ForeverDungeonJournal", "Data/QuestRewards.lua")
FDJ_DUNGEONS = ("ForeverDungeonJournal", "Data/Dungeons.lua")
GEARQUEST_PREFIX = "GearQuestForever_"
QUESTIE_SV = "Questie.lua"
ADDON_CERTAINTY = "suppose"  # addon : relevé de la communauté ou de son auteur
RECORD_CERTAINTY = "probable"  # relevé en jeu du joueur (QuestieForeverDB)
# Champs de `questKeys` lus dans la base Classic de Questie (positions lues dans l'en-tête du fichier).
QUESTIE_FIELDS = (
    "name",
    "startedBy",
    "finishedBy",
    "requiredLevel",
    "questLevel",
    "requiredRaces",
    "requiredClasses",
    "objectives",
    "preQuestGroup",
    "preQuestSingle",
    "exclusiveTo",
    "zoneOrSort",
    "nextQuestInChain",
)
# Corrections de Questie appliquées : champs numériques ou listes de nombres seulement.
FIX_FIELDS = (
    "requiredLevel",
    "questLevel",
    "requiredRaces",
    "requiredClasses",
    "preQuestGroup",
    "preQuestSingle",
    "exclusiveTo",
    "zoneOrSort",
    "nextQuestInChain",
)
FACTION_LETTERS = {"H": "horde", "A": "alliance", "B": "both", "AH": "both", "HA": "both"}
COMPLETO_FACTIONS = {1: "alliance", 2: "horde", 3: "both"}
FDJ_FACTIONS = {"Both": "both", "Horde": "horde", "Alliance": "alliance"}
_XP_TEXT = re.compile(r"([\d,]+) XP")
_BARE_NAME = re.compile(r"=\s*[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\s*(?=[,}\n])")
_BARE_IDENT = re.compile(r"=\s*(?!nil\b|true\b|false\b)[A-Za-z_][A-Za-z0-9_]*\s*(?=[,}\n])")
_COMPLETE = re.compile(r'\["complete"\]\s*=\s*\{')
_ENTRY_LINE = re.compile(r"^\s*\[(\d+)\]\s*=\s*(\{.*\}),?\s*$")
_GUIDE_DQ_LINE = re.compile(r"^ns\.DQ\[(\d+)\]\s*=\s*(\{.*\})\s*$", re.MULTILINE)
_GUIDE_DUNGEON_Q = re.compile(r'd\.key\s*==\s*"([^"]+)"\s*then\s*d\.q\s*=\s*(\{[^}]*\})')


def _read(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError as exc:
        raise DataSchemaError(f"{path} illisible ({exc.strerror or exc}).") from exc


def _version(addon: Path, toc: str | None = None) -> str | None:
    tocs = [addon / toc] if toc else sorted(addon.glob("*.toc"))
    for path in tocs:
        if path.is_file():
            m = re.search(r"^## Version:\s*(\S+)", _read(path), re.MULTILINE)
            if m:
                return m[1]
    return None


def _table_after(text: str, marker: str, where: Path) -> Any:
    i = text.find(marker)
    if i < 0:
        raise DataSchemaError(f"{where} : « {marker.strip()} » absent.")
    try:
        value, _ = parse_lua_value_at(text, i + len(marker))
    except ValueError as exc:
        raise DataSchemaError(f"{where} : {exc}.") from exc
    return value


def _fields(row: Any) -> dict[Any, Any]:
    if isinstance(row, dict):
        return row
    if isinstance(row, list):
        return dict(enumerate(row, start=1))
    return {}


def _ints(value: Any) -> list[int]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, int)]
    if isinstance(value, dict):
        return [v for k, v in sorted((k, v) for k, v in value.items() if isinstance(k, int)) if isinstance(v, int)]
    return []


def _place(name: str | None, map_id: Any, x: Any, y: Any, npc: int | None = None) -> dict[str, Any] | None:
    if not isinstance(map_id, int) or not isinstance(x, int | float) or not isinstance(y, int | float):
        return {"name": name, **({"npc": npc} if npc else {})} if name else None
    place: dict[str, Any] = {"map": map_id, "x": float(x), "y": float(y)}
    if name:
        place["name"] = name
    if npc:
        place["npc"] = npc
    return place


def _faction_of_races(races: int) -> str:
    horde, alliance = FACTION_MASKS["horde"], FACTION_MASKS["alliance"]
    if races and races & horde and not races & alliance:
        return "horde"
    if races and races & alliance and not races & horde:
        return "alliance"
    return "both"


def _info(
    key: str, addon: Path, version: str | None, files: list[Path], certainty: str = ADDON_CERTAINTY
) -> SourceInfo:
    return SourceInfo(key, addon.name, version, certainty, tuple(files))


def source_files(addons_dir: Path, wtf_dir: Path | None) -> list[Path]:
    """Fichiers que les lecteurs liraient (présents seulement), pour l'empreinte du cache."""
    q = addons_dir / QUESTIE
    candidates = [
        q / TOC_NAME,
        q / QUESTIE_QUESTS,
        q / QUESTIE_NPCS,
        q / QUESTIE_XP,
        q / QUESTIE_FIXES,
        q / QUESTIE_ZONES,
        *(addons_dir / a / f for a, f in (COMPLETO, JOURNEYS, NAOWH_DJ, GUIDE, FDJ_REWARDS, FDJ_DUNGEONS)),
        addons_dir / GUIDE[0] / GUIDE_DALARAN,
        addons_dir / GUIDE[0] / GUIDE_CHAINS,
        addons_dir / COMPLETO[0] / COMPLETO_BOOKS,
        addons_dir / NAOWH_DJ[0] / NAOWH_DJ_CHAINS,
        addons_dir / FDJ_REWARDS[0] / FDJ_CHAINS,
        addons_dir / FDJ_REWARDS[0] / FDJ_MAPS,
        *sorted(addons_dir.glob(f"{GEARQUEST_PREFIX}*/*.lua")),
    ]
    if wtf_dir is not None:
        candidates += sorted(wtf_dir.glob(f"Account/*/SavedVariables/{QUESTIE_SV}"))
    return [p for p in candidates if p.is_file()]


def _questie_keys(text: str, data: str, where: Path) -> dict[str, int]:
    keys: dict[str, int] = {}
    head = text[: text.find(data)]
    for m in re.finditer(r"^\s*\['(\w+)'\]\s*=\s*(\d+)", head, re.MULTILINE):
        keys.setdefault(m[1], int(m[2]))
    if "name" not in keys:
        raise DataSchemaError(f"{where} : en-tête des clés absent.")
    return keys


def _return_tables(text: str, where: Path) -> list[Any]:
    out = []
    for m in re.finditer(r"\[\[return\s*", text):
        end = text.find("]]", m.end())
        try:
            out.append(parse_lua_value(text[m.end() : end]))
        except ValueError as exc:
            raise DataSchemaError(f"{where} : {exc}.") from exc
    return out


def _questie_fixes(path: Path) -> dict[int, dict[str, Any]]:
    """Corrections de Questie (`classicQuestFixes.lua`) : champs de `FIX_FIELDS` dont la valeur est un nombre ou
    une liste de nombres ; les autres corrections (textes, positions, fonctions) sont ignorées."""
    out: dict[int, dict[str, Any]] = {}
    if not path.is_file():
        return out
    text = _read(path)
    for block in re.finditer(r"^\s{8}\[(\d+)\] = \{(.*?)^\s{8}\},", text, re.MULTILINE | re.DOTALL):
        fixes: dict[str, Any] = {}
        for m in re.finditer(r"\[questKeys\.(\w+)\]\s*=\s*([^\n]*?),\s*(?:--[^\n]*)?$", block[2], re.MULTILINE):
            if m[1] not in FIX_FIELDS:
                continue
            try:
                fixes[m[1]] = parse_lua_value(m[2])
            except ValueError:
                continue
        if fixes:
            out[int(block[1])] = fixes
    return out


def read_questie_quests(addons_dir: Path) -> tuple[SourceQuests, QuestieExtras] | None:
    root = addons_dir / QUESTIE
    qpath = root / QUESTIE_QUESTS
    if not (root / TOC_NAME).is_file() or not qpath.is_file():
        return None
    files = [
        p for p in (root / TOC_NAME, qpath, root / QUESTIE_NPCS, root / QUESTIE_XP, root / QUESTIE_FIXES) if p.is_file()
    ]
    area_to_map: dict[int, int] = {}
    zones = root / QUESTIE_ZONES
    if zones.is_file():
        files.append(zones)
        tables = _return_tables(_read(zones), zones)
        for table in reversed(tables):  # la table principale d'abord, la surcharge ensuite
            for k, v in _fields(table).items():
                if isinstance(k, int) and isinstance(v, int) and v:
                    area_to_map[k] = v
    text = _read(qpath)
    keys = _questie_keys(text, "questData", qpath)
    raw = _fields((_return_tables(text, qpath) or [{}])[0])
    npcs: dict[int, tuple[str, int | None, float | None, float | None]] = {}
    npath = root / QUESTIE_NPCS
    if npath.is_file():
        ntext = _read(npath)
        nkeys = _questie_keys(ntext, "npcData", npath)
        for npc_id, row in _fields((_return_tables(ntext, npath) or [{}])[0]).items():
            f = _fields(row)
            name = f.get(nkeys["name"])
            if not isinstance(npc_id, int) or not isinstance(name, str):
                continue
            spawn: tuple[int | None, float | None, float | None] = (None, None, None)
            spawns = _fields(f.get(nkeys.get("spawns", -1)))
            for zone, points in spawns.items():
                pts = points if isinstance(points, list) else list(_fields(points).values())
                first = pts[0] if pts else None
                if isinstance(zone, int) and isinstance(first, list) and len(first) >= 2:
                    spawn = (area_to_map.get(zone), first[0], first[1])
                    break
            npcs[npc_id] = (name, *spawn)
    xp: dict[int, int] = {}
    xpath = root / QUESTIE_XP
    if xpath.is_file():
        for quest, pair in _fields(_table_after(_read(xpath), "QuestXP.db = ", xpath)).items():
            if isinstance(quest, int) and isinstance(pair, list) and len(pair) == 2 and isinstance(pair[1], int):
                xp[quest] = pair[1]
    fixes = _questie_fixes(root / QUESTIE_FIXES)

    def npc_place(starts: Any) -> dict[str, Any] | None:
        creatures = _ints(_fields(starts).get(1))
        if not creatures:
            return None
        npc = creatures[0]
        name, map_id, x, y = npcs.get(npc, (None, None, None, None))
        return _place(name, map_id, x, y, npc) or {"npc": npc}

    quests: dict[int, Facts] = {}
    for quest_id, row in raw.items():
        if not isinstance(quest_id, int):
            continue
        f = _fields(row)
        v = {name: f.get(keys[name]) for name in QUESTIE_FIELDS if name in keys}
        v.update(fixes.get(quest_id, {}))
        facts: Facts = {}
        if isinstance(v.get("name"), str):
            facts["name"] = v["name"]
        level = v.get("questLevel")
        if isinstance(level, int) and level > 0:
            facts["level"] = level
        if isinstance(v.get("requiredLevel"), int):
            facts["min_level"] = v["requiredLevel"]
        races: int = v["requiredRaces"] if isinstance(v.get("requiredRaces"), int) else 0
        facts["races"] = races
        facts["faction"] = _faction_of_races(races)
        if isinstance(v.get("requiredClasses"), int):
            facts["classes"] = v["requiredClasses"]
        zone = v.get("zoneOrSort")
        if isinstance(zone, int) and zone > 0:
            facts["zone_area"] = zone
            if zone in area_to_map:
                facts["map"] = area_to_map[zone]
        giver, turn_in = npc_place(v.get("startedBy")), npc_place(v.get("finishedBy"))
        if giver:
            facts["giver"] = giver
        if turn_in:
            facts["turn_in"] = turn_in
        objectives = _fields(v.get("objectives"))
        if objectives:
            facts["objectives"] = {
                kind: [
                    o[0]
                    for o in (_fields(objectives.get(i)).values())
                    if isinstance(o, list) and o and isinstance(o[0], int)
                ]
                for i, kind in ((1, "creatures"), (2, "objects"), (3, "items"))
            }
        for src, dst in (
            ("preQuestGroup", "prereq_all"),
            ("preQuestSingle", "prereq_any"),
            ("exclusiveTo", "exclusive"),
        ):
            ids = _ints(v.get(src))
            if ids:
                facts[dst] = ids
        if isinstance(v.get("nextQuestInChain"), int) and v["nextQuestInChain"] > 0:
            facts["next"] = v["nextQuestInChain"]
        if quest_id in xp:
            facts["xp"] = xp[quest_id]
        quests[quest_id] = facts
    notes = [f"corrections de Questie appliquées à {len(fixes)} quête(s) (champs numériques)"] if fixes else []
    info = _info("questie", root, _version(root, TOC_NAME), files)
    return SourceQuests(info, quests, notes), QuestieExtras(area_to_map)


def read_questie_forever(wtf_dir: Path) -> SourceQuests | None:
    paths = sorted(wtf_dir.glob(f"Account/*/SavedVariables/{QUESTIE_SV}"))
    quests: dict[int, Facts] = {}
    read: list[Path] = []
    for path in paths:
        text = path.read_bytes().decode("latin-1")
        marker, config = "QuestieForeverDB = ", "QuestieConfig = "
        if marker not in text and config not in text:
            continue
        read.append(path)
        if config in text:  # RX1 : quêtes faites de chaque personnage (aucun nom de personnage gardé)
            start = text.find(config)
            end = text.find(marker, start)
            for m in _COMPLETE.finditer(text, start, end if end > start else len(text)):
                try:  # seules les tables `complete` sont lues : la table entière est trop lente à analyser
                    done, _ = parse_lua_value_at(text, m.end() - 1)
                except ValueError as exc:
                    raise DataSchemaError(f"{path} : {exc}.") from exc
                for quest_id, flag in _fields(done).items():
                    if isinstance(quest_id, int) and flag is True:
                        quests.setdefault(quest_id, {})["completed"] = True
        if marker not in text:
            continue
        db = _fields(_table_after(text, marker, path))
        for quest_id, row in _fields(db.get("quests")).items():
            f = _fields(row)
            if not isinstance(quest_id, int):
                continue
            facts: Facts = {}
            if isinstance(f.get("title"), str):
                facts["name"] = f["title"]
            if isinstance(f.get("level"), int) and f["level"] > 0:
                facts["level"] = f["level"]
            if isinstance(f.get("mapID"), int) and f["mapID"] > 0:
                facts["map"] = f["mapID"]
            # RX1 : une entrée sans titre ni niveau (quête rendue, vue en jeu) prouve encore que la quête existe
            quests.setdefault(quest_id, {}).update(facts or {"seen": True})
    if not read:
        return None
    info = SourceInfo("questie_forever", "Questie (SavedVariables)", None, RECORD_CERTAINTY, tuple(read))
    return SourceQuests(info, quests, [])


class Completo(NamedTuple):
    source: SourceQuests
    zones: dict[int, list[int]]  # uiMapID -> quêtes de la zone
    zone_names: dict[int, str]  # uiMapID -> nom anglais de la zone
    chains: list[list[list[int]]]  # chaînes : étapes ordonnées de groupes d'ID


def read_completo(addons_dir: Path) -> Completo | None:
    """Quêtes de Completo, quêtes et noms de chaque zone, chaînes."""
    addon, rel = addons_dir / COMPLETO[0], COMPLETO[1]
    path = addon / rel
    if not path.is_file():
        return None
    text = _read(path)
    zones: dict[int, list[int]] = {}
    names: dict[int, str] = {}
    for zone in _fields(_table_after(text, "D.Zones = ", path)).values():
        z = _fields(zone)
        if isinstance(z.get("map"), int):
            zones[z["map"]] = _ints(z.get("quests"))
            if isinstance(z.get("name"), str):
                names[z["map"]] = z["name"]
    quests: dict[int, Facts] = {}
    for quest_id, row in _fields(_table_after(text, "D.Quests = ", path)).items():
        f = _fields(row)
        if not isinstance(quest_id, int) or not f:
            continue
        facts: Facts = {"name": f.get(1)}
        if isinstance(f.get(2), int):
            facts["level"] = f[2]
        if isinstance(f.get(3), int):
            facts["min_level"] = f[3]
        if f.get(4) in COMPLETO_FACTIONS:
            facts["faction"] = COMPLETO_FACTIONS[f[4]]
        if isinstance(f.get(5), int) and f[5]:
            facts["races"] = f[5]
        if isinstance(f.get(6), int) and f[6]:
            facts["classes"] = f[6]
        if isinstance(f.get(7), int):
            facts["map"] = f[7]
        giver = _place(f.get(10) if isinstance(f.get(10), str) else None, f.get(7), f.get(8), f.get(9))
        if giver:
            facts["giver"] = giver
        quests[quest_id] = {k: v for k, v in facts.items() if v is not None}
    for quest_id, required in _fields(_table_after(text, "D.Requires = ", path)).items():
        if isinstance(quest_id, int) and quest_id in quests and _ints(required):
            quests[quest_id]["prereq_any"] = _ints(required)
    chains: list[list[list[int]]] = []
    for chain in _fields(_table_after(text, "D.Chains = ", path)).values():
        steps = [_ints(step) for step in _fields(chain).values()]
        chains.append([s for s in steps if s])
    for index, chain in enumerate(chains):
        for k, step in enumerate(chain):
            for quest_id in step:
                if quest_id in quests:
                    quests[quest_id]["chain"] = {"index": index, "step": k, "after": chain[k - 1] if k else []}
    files = [path]
    books = addon / COMPLETO_BOOKS
    if books.is_file():
        files.append(books)
        _read_books(books, quests)
    version = _version(addon)
    return Completo(SourceQuests(_info("completo", addon, version, files), quests, []), zones, names, chains)


def _spot(row: Any) -> dict[str, Any] | None:
    """Position `{map, x, y, nom}` des fichiers de Naowh (liste positionnelle), ou None sans carte."""
    f = _fields(row)
    place = _place(f.get(4) if isinstance(f.get(4), str) else None, f.get(1), f.get(2), f.get(3))
    return place if place and "map" in place else None


def _read_books(path: Path, quests: dict[int, Facts]) -> None:
    """Livres de la bibliothèque de Naowh Discovery (RX1) : objectifs (`LibraryGoals`) et livres (`LibraryBooks`,
    ramassés à leur emplacement, rendus au lieu de `LibraryTurnIns`) ; une quête de `QuestList` n'est pas écrasée."""
    text = _read(path)
    turn_ins: dict[str, dict[str, Any]] = {}
    if "ns.LibraryTurnIns = " in text:
        for key, spots in _fields(_table_after(text, "ns.LibraryTurnIns = ", path)).items():
            place = _spot(_fields(spots).get(1))
            if isinstance(key, str) and place:
                turn_ins[key] = place
    found: dict[int, Facts] = {}
    if "ns.LibraryGoals = " in text:
        for row in _fields(_table_after(text, "ns.LibraryGoals = ", path)).values():
            f = _fields(row)
            if isinstance(f.get("quest"), int):
                facts: Facts = {"name": f.get("name")}
                if isinstance(f.get("level"), int):
                    facts["level"] = f["level"]
                found[f["quest"]] = facts
    for row in _fields(_table_after(text, "ns.LibraryBooks = ", path)).values():
        f = _fields(row)
        if not isinstance(f.get("quest"), int):
            continue
        facts = {"name": f.get("name"), "faction": FACTION_LETTERS.get(str(f.get("side")))}
        if isinstance(f.get("item"), int):
            facts["start_item"] = f["item"]
        giver = _spot(_fields(f.get("spots")).get(1))
        if giver:
            facts["giver"] = giver
        if f.get("turnIn") in turn_ins:
            facts["turn_in"] = turn_ins[f["turnIn"]]
        found[f["quest"]] = facts
    for quest_id, facts in found.items():
        if quest_id not in quests:
            quests[quest_id] = {k: v for k, v in facts.items() if v is not None}


def read_journeys(addons_dir: Path) -> SourceQuests | None:
    addon, rel = addons_dir / JOURNEYS[0], JOURNEYS[1]
    path = addon / rel
    if not path.is_file():
        return None
    quests: dict[int, Facts] = {}
    for quest_id, row in _fields(_table_after(_read(path), "ns.JourneyQuestSpots = ", path)).items():
        f = _fields(row)
        if not isinstance(quest_id, int):
            continue
        facts: Facts = {}
        turn_in = _fields(f.get(1))
        place = _place(None, turn_in.get(1), turn_in.get(2), turn_in.get(3))
        if place:
            facts["turn_in"] = place
        camps = [
            [c[1], float(c[2]), float(c[3])]
            for c in (_fields(x) for x in _fields(f.get(2)).values())
            if isinstance(c.get(1), int) and isinstance(c.get(2), int | float) and isinstance(c.get(3), int | float)
        ]
        if camps:
            facts["objectives"] = {"camps": camps}
        if facts:
            quests[quest_id] = facts
    return SourceQuests(_info("journeys", addon, _version(addon), [path]), quests, [])


def _giver_name(text: Any) -> str | None:
    """Nom du donneur dans le texte du Dungeon Journal de Naowh (« Lieu - Nom (x, y) »)."""
    if not isinstance(text, str) or " - " not in text:
        return None
    name = text.split(" - ", 1)[1]
    name = re.split(r" \(|;| Prerequisite", name, maxsplit=1)[0].strip()
    return name or None


def read_naowh_dj(addons_dir: Path) -> SourceQuests | None:
    addon, rel = addons_dir / NAOWH_DJ[0], NAOWH_DJ[1]
    path = addon / rel
    if not path.is_file():
        return None
    quests: dict[int, Facts] = {}
    for dungeon in _fields(_table_after(_read(path), "J.QuestData = ", path)).values():
        d = _fields(dungeon)
        name = d.get("name")
        for row in _fields(d.get("quests")).values():
            f = _fields(row)
            quest_id = f.get(1)
            if not isinstance(quest_id, int):
                continue
            facts: Facts = {"name": f.get(2), "dungeon": name}
            if isinstance(f.get(3), int):
                facts["level"] = f[3]
            if f.get(4) in FACTION_LETTERS:
                facts["faction"] = FACTION_LETTERS[f[4]]
            giver = _place(_giver_name(f.get(6)), f.get(7), f.get(8), f.get(9))
            if giver:
                facts["giver"] = giver
            steps = _ints(f.get("steps"))
            if steps:
                facts["next"] = steps[0]
            quests[quest_id] = {k: v for k, v in facts.items() if v is not None}
    files = [path]
    chains = addon / NAOWH_DJ_CHAINS
    if chains.is_file():
        files.append(chains)
        _read_naowh_chains(chains, quests)
    return SourceQuests(_info("naowh_dj", addon, _version(addon), files), quests, [])


def _steps(chain: Any) -> list[list[int]]:
    """Étapes d'une chaîne : un identifiant, ou un groupe (`{a, b}`) dont une quête suffit."""
    out: list[list[int]] = []
    for step in _fields(chain).values():
        ids = [step] if isinstance(step, int) else _ints(step)
        if ids:
            out.append(ids)
    return out


def _read_naowh_chains(path: Path, quests: dict[int, Facts]) -> None:
    """Chaînes de quêtes du Dungeon Journal de Naowh (RX1) : ordre (étape précédente = `prereq_any`), noms,
    niveaux minimaux, donneur du début de chaîne ; ne remplace jamais un champ de `Data/Quests.lua`."""
    text = _read(path)

    def table(marker: str) -> dict[Any, Any]:
        return _fields(_table_after(text, marker, path)) if marker in text else {}

    for chain in table("J.QuestChains = ").values():
        steps = _steps(chain)
        for k, step in enumerate(steps):
            for quest_id in step:
                facts = quests.setdefault(quest_id, {})
                if k:
                    facts.setdefault("prereq_any", steps[k - 1])
    for quest_id, name in table("J.QuestChainNames = ").items():
        if isinstance(quest_id, int) and isinstance(name, str):
            quests.setdefault(quest_id, {}).setdefault("name", name)
    for quest_id, level in table("J.QuestMinLevel = ").items():
        if isinstance(quest_id, int) and isinstance(level, int):
            quests.setdefault(quest_id, {}).setdefault("min_level", level)
    for quest_id, row in table("J.QuestChainStarts = ").items():
        giver = _spot(row)
        if isinstance(quest_id, int) and giver:
            quests.setdefault(quest_id, {}).setdefault("giver", giver)
    for quest_id, where in table("J.QuestWhere = ").items():
        name = _giver_name(where)
        if isinstance(quest_id, int) and name:
            quests.setdefault(quest_id, {}).setdefault("giver", {"name": name})


def read_forever_guide(addons_dir: Path) -> SourceQuests | None:
    addon, rel = addons_dir / GUIDE[0], GUIDE[1]
    path = addon / rel
    if not path.is_file():
        return None
    text = _read(path)
    dungeon_of: dict[int, str] = {}
    for dungeon in _fields(_table_after(text, "ns.DUNGEONS = ", path)).values():
        d = _fields(dungeon)
        for quest_id in _ints(d.get("q")):
            if isinstance(d.get("en"), str):
                dungeon_of[quest_id] = d["en"]
    npcs: dict[int, dict[str, Any]] = {}
    if "ns.DNPC = " in text:
        for npc_id, row in _fields(_table_after(text, "ns.DNPC = ", path)).items():
            f = _fields(row)
            spawns = [_fields(s) for s in _fields(f.get("sp")).values()]
            first = spawns[0] if spawns else {}
            if isinstance(npc_id, int):
                npcs[npc_id] = _place(f.get("n"), first.get(1), first.get(2), first.get(3), npc_id) or {"npc": npc_id}

    def place(name: Any, xy: Any, ids: Any) -> dict[str, Any] | None:
        npc_ids = _ints(ids)
        npc = npcs.get(npc_ids[0]) if npc_ids else None
        xyf = _fields(xy)
        if xyf:
            return _place(
                name if isinstance(name, str) else (npc or {}).get("name"),
                xyf.get(1),
                xyf.get(2),
                xyf.get(3),
                npc_ids[0] if npc_ids else None,
            )
        if npc:
            return npc
        return {"name": name} if isinstance(name, str) else None

    rows = dict(_fields(_table_after(text, "ns.DQ = ", path)))
    files = [path]
    dalaran = addon / GUIDE_DALARAN
    if dalaran.is_file():  # DJ1 : quêtes ajoutées une à une (ns.DQ[id] = {…}) et quêtes du donjon (boucle)
        files.append(dalaran)
        extra = _read(dalaran)
        for m in _GUIDE_DQ_LINE.finditer(extra):
            try:
                rows[int(m[1])] = parse_lua_value(m[2])
            except ValueError as exc:
                raise DataSchemaError(f"{dalaran} : {exc}.") from exc
        names = {
            d.get("key"): d.get("en")
            for d in (_fields(x) for x in _fields(_table_after(text, "ns.DUNGEONS = ", path)).values())
        }
        for m in _GUIDE_DUNGEON_Q.finditer(extra):
            name = names.get(m[1])
            if isinstance(name, str):
                for quest_id in (int(q) for q in re.findall(r"\d+", m[2])):
                    dungeon_of[quest_id] = name
    quests: dict[int, Facts] = {}
    for quest_id, row in rows.items():
        f = _fields(row)
        if not isinstance(quest_id, int):
            continue
        facts: Facts = {"name": f.get("n")}
        if isinstance(f.get("lv"), int):
            facts["level"] = f["lv"]
        if isinstance(f.get("rl"), int):
            facts["min_level"] = f["rl"]
        if f.get("fa") in FACTION_LETTERS:
            facts["faction"] = FACTION_LETTERS[f["fa"]]
        giver = place(f.get("g"), f.get("gxy"), f.get("s"))
        if giver:
            facts["giver"] = giver
        turn_in = place(f.get("e"), f.get("exy"), f.get("f"))
        if turn_in:
            facts["turn_in"] = turn_in
        if _ints(f.get("ps")):
            facts["prereq_any"] = _ints(f.get("ps"))
        if isinstance(f.get("nx"), int):
            facts["next"] = f["nx"]
        if isinstance(f.get("z"), int):
            facts["zone_area"] = f["z"]
        if quest_id in dungeon_of:
            facts["dungeon"] = dungeon_of[quest_id]
        rewards = _fields(f.get("rw"))
        if rewards:
            facts["rewards"] = {
                "money": rewards.get("m"),
                "choices": [
                    c[1] for c in (_fields(x) for x in _fields(rewards.get("c")).values()) if isinstance(c.get(1), int)
                ],
                "reputation": _ints(rewards.get("rep")),
            }
        if f.get("new") is True:
            facts["new"] = True
        quests[quest_id] = {k: v for k, v in facts.items() if v is not None}
    chains = addon / GUIDE_CHAINS
    if chains.is_file():
        files.append(chains)
        _read_guide_chains(chains, quests)
    return SourceQuests(_info("forever_guide", addon, _version(addon), files), quests, [])


GUIDE_FACTIONS = {"Alliance": "alliance", "Horde": "horde"}


def _read_guide_chains(path: Path, quests: dict[int, Facts]) -> None:
    """Chaînes importantes de Forever Guide (RX1, `ChainData.lua`) : étapes (départ propre à chaque camp, puis
    `ids`), positions (`points`), noms et niveaux minimaux (`ChainExtraQuests`) ; ne remplace aucun champ de `ns.DQ`."""
    text = _read(path)
    extra = _fields(_table_after(text, "ns.ChainExtraQuests=", path)) if "ns.ChainExtraQuests=" in text else {}
    for chain in _fields(_table_after(text, "ns.ChainCatalog=", path)).values():
        c = _fields(chain)
        ids = _ints(c.get("ids"))
        if not ids:
            continue
        start_of = {
            q: GUIDE_FACTIONS[k]
            for k, q in _fields(c.get("factionStart")).items()
            if k in GUIDE_FACTIONS and isinstance(q, int)
        }
        starts = list(start_of) or ids[:1]
        steps = [starts] + [[q] for q in ids if q not in starts]
        points = _fields(c.get("points"))
        start_points = _fields(points.get(ids[0]))
        for k, step in enumerate(steps):
            for quest_id in step:
                facts = quests.setdefault(quest_id, {})
                facts.setdefault("chain", {"name": c.get("name"), "step": k, "after": steps[k - 1] if k else []})
                if k:
                    facts.setdefault("prereq_any", steps[k - 1])
                if quest_id in start_of:
                    facts.setdefault("faction", start_of[quest_id])
                    point = start_points.get({"alliance": "Alliance", "horde": "Horde"}[start_of[quest_id]])
                else:
                    point = points.get(quest_id)
                giver = _spot(point)
                if giver:
                    facts.setdefault("giver", giver)
                e = _fields(extra.get(quest_id))
                if isinstance(e.get("n"), str):
                    facts.setdefault("name", e["n"])
                if isinstance(e.get("rl"), int):
                    facts.setdefault("min_level", e["rl"])


_FDJ_ENTRY = re.compile(r'^(?:FDJ\.)?DB\["([^"]+)"\]\s*=\s*', re.MULTILINE)


def fdj_db_entries(text: str, where: Path) -> list[tuple[str, Any]]:
    """(nom, table) de chaque donjon de `Data/Dungeons.lua` de ForeverDungeonJournal, sous ses trois formes
    d'écriture : `FDJ.DB = { ["X"] = {…} }`, `DB["X"] = {…}` (après `local DB = FDJ.DB`), `FDJ.DB["X"] = {…}`
    (DJ1 : avant, seule la première était lue)."""
    text = _BARE_NAME.sub("= nil", text)  # constantes de l'addon (positions) : non lues
    out: list[tuple[str, Any]] = []
    if "FDJ.DB = " in text:
        out += [(str(k), v) for k, v in _fields(_table_after(text, "FDJ.DB = ", where)).items()]
    for m in _FDJ_ENTRY.finditer(text):
        try:
            value, _ = parse_lua_value_at(text, m.end())
        except ValueError as exc:
            raise DataSchemaError(f"{where} : {exc}.") from exc
        out.append((m[1], value))
    return out


def read_fdj(addons_dir: Path) -> SourceQuests | None:
    addon = addons_dir / FDJ_REWARDS[0]
    rewards, dungeons = addon / FDJ_REWARDS[1], addon / FDJ_DUNGEONS[1]
    chains, maps = addon / FDJ_CHAINS, addon / FDJ_MAPS
    if not any(p.is_file() for p in (rewards, dungeons, chains, maps)):
        return None
    quests: dict[int, Facts] = {}
    files: list[Path] = []
    if rewards.is_file():
        files.append(rewards)
        for quest_id, xp in _fields(_table_after(_read(rewards), "FDJ.FOREVER_QUEST_XP_FALLBACK = ", rewards)).items():
            if isinstance(quest_id, int) and isinstance(xp, int):
                quests.setdefault(quest_id, {})["xp"] = xp
    if dungeons.is_file():
        files.append(dungeons)
        for name, dungeon in fdj_db_entries(_read(dungeons), dungeons):
            for row in _fields(_fields(dungeon).get("quests")).values():
                f = _fields(row)
                quest_id = f.get("id")
                if not isinstance(quest_id, int):
                    continue
                facts = quests.setdefault(quest_id, {})
                facts["dungeon"] = name
                if isinstance(f.get("name"), str):
                    facts["name"] = f["name"]
                if isinstance(f.get("level"), int):
                    facts["level"] = f["level"]
                if isinstance(f.get("requires"), int):
                    facts["min_level"] = f["requires"]
                if f.get("faction") in FDJ_FACTIONS:
                    facts["faction"] = FDJ_FACTIONS[f["faction"]]
                if isinstance(f.get("liveXPFallback"), int):
                    facts.setdefault("xp", f["liveXPFallback"])
                m = _XP_TEXT.search(f.get("rewards") or "") if isinstance(f.get("rewards"), str) else None
                if m:
                    facts["xp_text"] = int(m[1].replace(",", ""))
    for path in (maps, chains):
        if path.is_file():
            files.append(path)
            _read_fdj_chains(path, quests)
    return SourceQuests(_info("fdj", addon, _version(addon), files), quests, [])


def _fdj_place(row: Any) -> dict[str, Any] | None:
    f = _fields(row)
    x, y = f.get("x"), f.get("y")
    if not isinstance(x, int | float) or not isinstance(y, int | float):
        return None
    name = f.get("targetName") if isinstance(f.get("targetName"), str) else None
    place = _place(name, f.get("mapID"), x * FDJ_UNIT_TO_PERCENT, y * FDJ_UNIT_TO_PERCENT)
    return place if place and "map" in place else None


def _read_fdj_chains(path: Path, quests: dict[int, Facts]) -> None:
    """ForeverDungeonJournal (RX1) : positions des donneurs (`QUEST_START_MAPS`, lues en premier), prérequis requis
    (`QUEST_PREREQ_CHAINS` : tous requis), niveau et niveau minimal (`QUEST_PREREQ_DETAILS`) ; constantes de l'addon
    ignorées ; un champ déjà lu n'est pas remplacé."""
    text = _BARE_IDENT.sub("= nil", _BARE_NAME.sub("= nil", _read(path)))

    def table(marker: str) -> dict[Any, Any]:
        return _fields(_table_after(text, marker, path)) if marker in text else {}

    for quest_id, row in table("FDJ.QUEST_START_MAPS = ").items():
        giver = _fdj_place(row)
        if isinstance(quest_id, int) and giver:
            quests.setdefault(quest_id, {}).setdefault("giver", giver)
    for quest_id, rows in table("FDJ.QUEST_PREREQ_CHAINS = ").items():
        if not isinstance(quest_id, int):
            continue
        required = []
        for row in _fields(rows).values():
            f = _fields(row)
            if isinstance(f.get("id"), int):
                required.append(f["id"])
                if isinstance(f.get("name"), str):
                    quests.setdefault(f["id"], {}).setdefault("name", f["name"])
        if required:
            quests.setdefault(quest_id, {}).setdefault("prereq_all", required)
    for quest_id, row in table("FDJ.QUEST_PREREQ_DETAILS = ").items():
        f = _fields(row)
        if not isinstance(quest_id, int):
            continue
        facts = quests.setdefault(quest_id, {})
        if isinstance(f.get("level"), int):
            facts.setdefault("level", f["level"])
        if isinstance(f.get("requires"), int):
            facts.setdefault("min_level", f["requires"])
        giver = _fdj_place(f.get("map"))
        if giver:
            facts.setdefault("giver", giver)


def read_gearquest(addons_dir: Path) -> tuple[SourceInfo, list[GearReward]] | None:
    files = sorted(addons_dir.glob(f"{GEARQUEST_PREFIX}*/*.lua"))
    rewards: dict[tuple[int, str], GearReward] = {}
    read: list[Path] = []
    for path in files:
        found = False
        for line in _read(path).splitlines():
            if "questName=" not in line:
                continue
            m = _ENTRY_LINE.match(line)
            if not m:
                continue
            try:
                row = _fields(parse_lua_value(m[2]))
            except ValueError:
                continue
            quest_name = row.get("questName")
            if not isinstance(quest_name, str):
                continue
            found = True
            zone = row.get("zone") if isinstance(row.get("zone"), str) else None
            rewards.setdefault((int(m[1]), quest_name), GearReward(int(m[1]), str(row.get("name")), quest_name, zone))
        if found:
            read.append(path)
    if not read:
        return None
    base = addons_dir / "GearQuestForever"
    return _info("gearquest", base, _version(base), read), list(rewards.values())
