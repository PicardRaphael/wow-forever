"""Lecteurs locaux des donjons des addons de Forever (DJ1, bloc B), sans réseau ni exécution de Lua.

Chaque lecteur rend les donjons d'un addon installé (`Interface/AddOns`) sous une forme commune, clé = identifiant
d'instance en texte (`"389"`) quand la source le donne, sinon `"name:<nom>"` (ou `"area:<AreaTable>"` pour Zone
Info: Forever) ; rattachement fait dans `forever/dungeons.py`. Champs présents dans la source seulement : `name`,
`map`, `levels` (`min`, `max`), `access_level`, `entrance` (`map` uiMapID, `x`, `y` en %), `new`, `closed`,
`bosses` (`name`, `npc`, `level`, `encounter`, `loot` : `item`, `rate` en fraction, `classic`), `quests`,
`trash_npcs`, `access`. Rien n'est deviné. Les SavedVariables de Naowh Forever (`journalRun`, `journalKills`,
`journalLoot`, `instanceTrackerChars`) sont lues sans jamais garder les noms de joueurs (`rolls`, `team`, `drops`,
`group`, `name`). Registre : H12, I16. AlexAtlasLoot n'est jamais lu (licence, décision 229). Aucun chiffre de jeu ici : les conversions
(pourcentage -> fraction, coordonnées 0-1 -> %) sont celles du format de chaque fichier."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError
from forever.pipeline.lua_table import parse_lua_assignments, parse_lua_value_at
from forever.pipeline.quest_sources import (
    FDJ_DUNGEONS,
    Facts,
    SourceInfo,
    _fields,
    _info,
    _ints,
    _read,
    _table_after,
    _version,
    fdj_db_entries,
)

DUNGEON_SOURCE_LABELS = {
    "naowh_dj": "Naowh Forever, Dungeon Journal",
    "naowh_sv": "Naowh Forever, relevés du joueur (SavedVariables)",
    "fojji": "FojjiCore, Dungeon Journal (recoupement)",
    "fdj": "ForeverDungeonJournal",
    "forever_guide": "Forever Guide",
    "atlasloot": "AtlasLoot Classic Forever",
    "companion": "Forever Companion",
    "zoneinfo": "Zone Info: Forever",
}
PERCENT = 100.0  # format : taux écrits en pourcentage par Naowh, FojjiCore, Forever Guide et AtlasLoot
FRACTION = 1.0  # format : taux écrits en fraction par Forever Companion
UNIT_TO_PERCENT = 100.0  # format : coordonnées de ForeverDungeonJournal écrites de 0 à 1
RECORD_CERTAINTY = "certain"  # relevé du joueur (passages, butin) tenu par Naowh Forever

NAOWH_DJ = "NaowhForever_DungeonJournal"
NAOWH_SV = "NaowhForever.lua"
FOJJI = "FojjiCore_DungeonJournal"
FDJ = "ForeverDungeonJournal"
GUIDE = "ForeverGuide"
ATLAS = "AtlasLootClassic_DungeonsAndRaids"
ATLAS_TOC = "AtlasLootClassic_DungeonsAndRaids_Forever.toc"
COMPANION = "ForeverCompanion"
ZONEINFO = "ZoneInfoForever"

_ADD_DUNGEON = re.compile(r'AddDungeon\("([^"]+)",\s*')
_RANGE_TEXT = re.compile(r"\((\d+)\s*-\s*(\d+)\)")
_NAME_BEFORE_RANGE = re.compile(r"^\s*(.*?)\s*\(\d+\s*-\s*\d+\)\s*$")
_BARE_CONSTANT = re.compile(r"=\s*[A-Z][A-Z0-9_]+\s*(?=[,}\n])")
_BLOCK_COMMENT = re.compile(r"--\[\[.*?\]\]", re.DOTALL)
_ATLAS_BLOCK = re.compile(r'^data\["([^"]+)"\]\s*=\s*\{', re.MULTILINE)
_GUIDE_DALARAN_Q = re.compile(r'd\.key\s*==\s*"([^"]+)"\s*then\s*d\.q\s*=\s*(\{[^}]*\})')


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


def _key(map_id: Any, name: Any) -> str:
    return str(map_id) if isinstance(map_id, int) and map_id > 0 else f"name:{name}"


def _put(dungeons: dict[str, Facts], facts: Facts) -> None:
    """Range un donjon sous son instance ; deux donjons d'une même instance (ailes de Scarlet Monastery, de Dire
    Maul, de Blackrock Spire) passent tous deux sous « instance:nom »."""
    facts = _clean(facts)
    key = _key(facts.get("map"), facts.get("name"))
    if key.startswith("name:"):
        dungeons[key] = facts
        return
    if key in dungeons:
        first = dungeons.pop(key)
        dungeons[f"{key}:{first.get('name')}"] = {**first, "wing": True}
    if any(k.startswith(f"{key}:") for k in dungeons):
        dungeons[f"{key}:{facts.get('name')}"] = {**facts, "wing": True}
        return
    dungeons[key] = facts


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _levels(lo: Any, hi: Any) -> dict[str, int] | None:
    lo, hi = _int(lo), _int(hi)
    return {"min": lo, "max": hi} if lo is not None and hi is not None else None


def _rate(value: Any, scale: float = PERCENT) -> float | None:
    """Taux en fraction ; 0 ou absent : inconnu (Naowh écrit 0 sous son seuil de victoires)."""
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return None
    return float(value) / scale


def _loot(item: int, rate: float | None, classic: bool = False) -> dict[str, Any]:
    """Objet lâché : taux en fraction (None : inconnu) ; `classic` : taux repris de Classic."""
    out: dict[str, Any] = {"item": item, "rate": rate}
    if classic:
        out["classic"] = True
    return out


def _prereq_list(value: Any) -> list[Any]:
    out: list[Any] = []
    for v in value if isinstance(value, list) else _fields(value).values():
        if isinstance(v, int):
            out.append(v)
        elif isinstance(v, list | dict):
            sub = _ints(v)
            if sub:
                out.append(sub)
    return out


def _clean(facts: Facts) -> Facts:
    return {k: v for k, v in facts.items() if v is not None}


def _value_after(text: str, marker: str, where: Path) -> Any:
    try:
        return _table_after(text, marker, where)
    except DataSchemaError:
        return None


# --- Naowh Forever, Dungeon Journal --------------------------------------------------------------------------------


def read_naowh_journal(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / NAOWH_DJ
    data = addon / "Data"
    files = sorted((data / "Dungeons").glob("*.lua")) if (data / "Dungeons").is_dir() else []
    if not files:
        return None
    read: list[Path] = list(files)
    by_name: dict[str, dict[str, Any]] = {}
    quests_path = data / "Quests.lua"
    if quests_path.is_file():
        read.append(quests_path)
        for entry in _fields(_value_after(_read(quests_path), "J.QuestData = ", quests_path)).values():
            e = _fields(entry)
            if isinstance(e.get("name"), str):
                by_name[e["name"]] = e
    boss_info: dict[int, Any] = {}
    info_path = data / "BossInfo.lua"
    if info_path.is_file():
        read.append(info_path)
        boss_info = {
            k: _fields(v)
            for k, v in _fields(_value_after(_read(info_path), "ns.Journal.BossInfo = ", info_path)).items()
            if isinstance(k, int)
        }
    dungeons: dict[str, Facts] = {}
    notes: list[str] = []
    for path in files:
        text = _read(path)
        m = _ADD_DUNGEON.search(text)
        if not m:
            notes.append(f"{path.name} : AddDungeon absent, fichier ignoré")
            continue
        try:
            raw, _ = parse_lua_value_at(text, m.end())
        except ValueError as exc:
            raise DataSchemaError(f"{path} : {exc}.") from exc
        d = _fields(raw)
        name = d.get("name")
        q = by_name.get(name, {}) if isinstance(name, str) else {}
        levels = _fields(q.get("levels"))
        entrance = _fields(d.get("entrance"))
        bosses: list[dict[str, Any]] = []
        for wing in _fields(d.get("wings")).values():
            for b in _fields(_fields(wing).get("bosses")).values():
                bf = _fields(b)
                if bf.get("trash") or bf.get("chest") or not isinstance(bf.get("name"), str):
                    continue
                npc = _int(bf.get("npc"))
                info = boss_info.get(npc) if npc is not None else None
                level = _int(_fields(info).get(1)) if info else None
                items, chances = _ints(bf.get("loot")), list(_fields(bf.get("chance")).values())
                encounters = _ints(bf.get("encounters"))
                bosses.append(
                    _clean(
                        {
                            "name": bf["name"],
                            "npc": npc,
                            "level": level if level is not None and level > 0 else None,
                            "encounter": encounters[0] if encounters else None,
                            "loot": [
                                _loot(item, _rate(chances[i] if i < len(chances) else None))
                                for i, item in enumerate(items)
                            ],
                        }
                    )
                )
        facts: Facts = {
            "name": name,
            "map": _int(q.get("map")),
            "source_key": m[1],
            "levels": _levels(levels.get(1), levels.get(2)),
            "entrance": {"map": entrance["map"], "x": float(entrance["x"]), "y": float(entrance["y"])}
            if isinstance(entrance.get("map"), int)
            else None,
            "new": True if d.get("new") is True else None,
            "closed": True if d.get("closed") is True else None,
            "raid": True if d.get("raid") else None,  # raid rangé dans le journal : écarté du livre
            "bosses": bosses,
            "quests": [
                qid for qid in (_fields(r).get(1) for r in _fields(q.get("quests")).values()) if isinstance(qid, int)
            ],
        }
        _put(dungeons, facts)
    prereqs: dict[int, list[Any]] = {}
    min_levels: dict[int, int] = {}
    chains = data / "QuestChains.lua"
    if chains.is_file():
        read.append(chains)
        text = _read(chains)
        for quest_id, value in _fields(_value_after(text, "J.QuestPrereqs = ", chains)).items():
            if isinstance(quest_id, int) and _prereq_list(value):
                prereqs[quest_id] = _prereq_list(value)
        for quest_id, level in _fields(_value_after(text, "J.QuestMinLevel = ", chains)).items():
            if isinstance(quest_id, int) and isinstance(level, int):
                min_levels[quest_id] = level
    build = data / "Build.lua"
    version = _version(addon)
    if build.is_file():
        m = re.search(r'DATA_BUILD\s*=\s*"([^"]+)"', _read(build))
        if m:
            notes.append(f"données de l'addon datées du client {m[1]}")
    return SourceDungeons(_info("naowh_dj", addon, version, read), dungeons, prereqs, min_levels, notes)


def read_naowh_runs(wtf_dir: Path) -> NaowhRuns | None:
    """Passages et butin relevés par Naowh Forever (compte entier) ; noms de joueurs jamais gardés. Registre : I16"""
    paths = sorted(wtf_dir.glob(f"Account/*/SavedVariables/{NAOWH_SV}")) if wtf_dir.is_dir() else []
    if not paths:
        return None
    runs: list[dict[str, Any]] = []
    kills: dict[int, dict[str, Any]] = {}
    loot: list[dict[str, Any]] = []
    for path in paths:
        try:
            values = parse_lua_assignments(_read(path))
        except ValueError as exc:
            raise DataSchemaError(f"{path} : {exc}.") from exc
        account = _fields(_fields(values.get("NaowhForeverDB")).get("account"))
        for run in _fields(account.get("journalRun")).values():
            r = _fields(run)
            entered, left = _int(r.get("at")), _int(r.get("left"))
            if _int(r.get("map")) is None or entered is None:
                continue
            runs.append(
                {
                    "instance_id": _int(r.get("map")),
                    "entered": entered,
                    "left": left,
                    "seconds": left - entered if left is not None else None,
                    "source": "journal_run",
                }
            )
        for by_encounter in _fields(account.get("journalKills")).values():
            for encounter, k in _fields(by_encounter).items():
                kf = _fields(k)
                if isinstance(encounter, int):
                    slot = kills.setdefault(encounter, {"took": [], "n": 0})
                    slot["took"] += _ints(kf.get("took"))
                    slot["n"] += _int(kf.get("n")) or 0
        for entries in _fields(account.get("journalLoot")).values():
            for e in _fields(entries).values():
                ef = _fields(e)
                if _int(ef.get("id")) is not None:
                    loot.append(
                        _clean(
                            {
                                "item": _int(ef.get("id")),
                                "dungeon": ef.get("dungeon") if isinstance(ef.get("dungeon"), str) else None,
                                "boss": ef.get("boss") if isinstance(ef.get("boss"), str) else None,
                                "at": _int(ef.get("at")),
                            }
                        )
                    )
        for record in _fields(account.get("instanceTrackerChars")).values():
            for run in _fields(_fields(record).get("runs")).values():
                r = _fields(run)
                entered, left = _int(r.get("entered")), _int(r.get("left"))
                runs.append(
                    _clean(
                        {
                            "instance_id": _int(r.get("mapID")),
                            "instance": r.get("instance") if isinstance(r.get("instance"), str) else None,
                            "kind": r.get("kind") if isinstance(r.get("kind"), str) else None,
                            "entered": entered,
                            "left": left,
                            "seconds": left - entered if left is not None and entered is not None else None,
                            "level": _int(r.get("level")),
                            "xp": _int(r.get("xp")),
                            "deaths": _int(r.get("deaths")),
                            "source": "instance_tracker",
                        }
                    )
                )
    info = SourceInfo("naowh_sv", NAOWH_SV, None, RECORD_CERTAINTY, tuple(paths))
    return NaowhRuns(info, runs, kills, loot)


# --- FojjiCore, Dungeon Journal ------------------------------------------------------------------------------------


def read_fojji(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / FOJJI
    path = addon / "Data" / "Dungeons.lua"
    if not path.is_file():
        return None
    text = _read(path)
    access: dict[str, list[dict[str, Any]]] = {}
    for key, rows in _fields(_value_after(text, "FDJ.Access = ", path)).items():
        access[str(key)] = [
            _clean(
                {
                    "item": _int(_fields(r).get("item")),
                    "name": _fields(r).get("name") if isinstance(_fields(r).get("name"), str) else None,
                    "required": _fields(r).get("need") == "required",
                    "quests": _ints(_fields(r).get("have")),
                }
            )
            for r in _fields(rows).values()
        ]
    dungeons: dict[str, Facts] = {}
    for raw in _fields(_table_after(text, "FDJ.Dungeons = ", path)).values():
        d = _fields(raw)
        rng = _fields(d.get("range"))
        bosses = []
        for b in _fields(d.get("bosses")).values():
            bf = _fields(b)
            if not isinstance(bf.get("n"), str):
                continue
            items, odds = _ints(bf.get("loot")), list(_fields(bf.get("odds")).values())
            bosses.append(
                _clean(
                    {
                        "name": bf["n"],
                        "npc": _int(bf.get("npc")),
                        "level": _int(bf.get("lv")),
                        "loot": [
                            _loot(item, _rate(odds[i] if i < len(odds) else None)) for i, item in enumerate(items)
                        ],
                    }
                )
            )
        facts = {
            "name": d.get("name"),
            "map": _int(d.get("instance")),
            "source_key": d.get("key"),
            "levels": _levels(rng.get(1), rng.get(2)),
            "bosses": bosses,
            "quests": _ints(d.get("quests")),
            "access": access.get(str(d.get("key"))),
        }
        _put(dungeons, facts)
    files = [path]
    prereqs: dict[int, list[Any]] = {}
    chains = addon / "Data" / "Chains.lua"
    if chains.is_file():
        files.append(chains)
        for quest_id, value in _fields(_value_after(_read(chains), "FDJ.QuestChains = ", chains)).items():
            if isinstance(quest_id, int) and _prereq_list(value):
                prereqs[quest_id] = _prereq_list(value)
    notes = ["FojjiCore : recoupement seulement (réutilisation interdite, décision 265), origine des taux non déclarée"]
    return SourceDungeons(_info("fojji", addon, _version(addon), files), dungeons, prereqs, {}, notes)


# --- ForeverDungeonJournal -----------------------------------------------------------------------------------------


def _range_text(value: Any) -> dict[str, int] | None:
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", value)
    return {"min": int(m[1]), "max": int(m[2])} if m else None


def read_fdj_dungeons(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / FDJ
    path = addon / FDJ_DUNGEONS[1]
    if not path.is_file():
        return None
    files = [path]
    levels_by: dict[str, dict[str, Any]] = {}
    bosses_path = addon / "Data" / "Bosses.lua"
    if bosses_path.is_file():
        files.append(bosses_path)
        levels_by = {
            str(k): _fields(v)
            for k, v in _fields(_value_after(_read(bosses_path), "FDJ.BOSS_LEVELS = ", bosses_path)).items()
        }
    entrances: dict[str, dict[str, Any]] = {}
    entrances_path = addon / "Data" / "DungeonEntrances.lua"
    if entrances_path.is_file():
        files.append(entrances_path)
        entrances = {
            str(k): _fields(v)
            for k, v in _fields(_value_after(_read(entrances_path), "local entrances = ", entrances_path)).items()
        }
    dungeons: dict[str, Facts] = {}
    for name, raw in fdj_db_entries(_read(path), path):
        d = _fields(raw)
        boss_levels = levels_by.get(name, {})
        bosses = []
        for b in _fields(d.get("bosses")).values():
            bf = _fields(b)
            if not isinstance(bf.get("name"), str):
                continue
            bosses.append(
                _clean(
                    {
                        "name": bf["name"],
                        "npc": _int(bf.get("npcID")),
                        "level": _int(boss_levels.get(bf["name"])),
                        "loot": [
                            _loot(item, None)
                            for item in (_fields(x).get(1) for x in _fields(bf.get("loot")).values())
                            if isinstance(item, int)
                        ],
                    }
                )
            )
        e = entrances.get(name, {})
        entrance = (
            {"map": e["mapID"], "x": float(e["x"]) * UNIT_TO_PERCENT, "y": float(e["y"]) * UNIT_TO_PERCENT}
            if isinstance(e.get("mapID"), int) and isinstance(e.get("x"), int | float)
            else None
        )
        facts = {
            "name": name,
            "levels": _range_text(d.get("level")),
            "entrance": entrance,
            "bosses": bosses,
            "quests": [
                q for q in (_fields(r).get("id") for r in _fields(d.get("quests")).values()) if isinstance(q, int)
            ],
        }
        dungeons[_key(None, name)] = _clean(facts)
    prereqs: dict[int, list[Any]] = {}
    chains = addon / "Data" / "QuestChains.lua"
    if chains.is_file():
        files.append(chains)
        text = _BARE_CONSTANT.sub("= nil", _read(chains))  # constantes de l'addon (lieux) : non lues
        for quest_id, rows in _fields(_value_after(text, "FDJ.QUEST_PREREQ_CHAINS = ", chains)).items():
            ids = [i for i in (_fields(r).get("id") for r in _fields(rows).values()) if isinstance(i, int)]
            if isinstance(quest_id, int) and ids:
                prereqs[quest_id] = ids
    return SourceDungeons(_info("fdj", addon, _version(addon), files), dungeons, prereqs, {}, [])


# --- Forever Guide -------------------------------------------------------------------------------------------------


def read_guide_dungeons(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / GUIDE
    path = addon / "DungeonData.lua"
    if not path.is_file():
        return None
    files = [path]
    instance_of: dict[str, int] = {}
    trash: dict[str, int] = {}
    trash_path = addon / "DungeonTrash.lua"
    if trash_path.is_file():
        files.append(trash_path)
        text = _read(trash_path)
        for map_id, keys in _fields(_value_after(text, "ns.TRASH_MAP = ", trash_path)).items():
            for key in [keys] if isinstance(keys, str) else _fields(keys).values():
                if isinstance(map_id, int) and isinstance(key, str):
                    instance_of[key] = map_id
        for npc, key in _fields(_value_after(text, "ns.TRASH_NPC = ", trash_path)).items():
            if isinstance(npc, int) and isinstance(key, str):
                trash[key] = trash.get(key, 0) + 1
    loot_by: dict[str, Any] = {}
    loot_path = addon / "DungeonLoot.lua"
    if loot_path.is_file():
        files.append(loot_path)
        loot_by = {str(k): v for k, v in _fields(_value_after(_read(loot_path), "ns.LOOT = ", loot_path)).items()}
    quests_of: dict[str, list[int]] = {}
    dalaran = addon / "DalaranData.lua"
    if dalaran.is_file():
        files.append(dalaran)
        for m in _GUIDE_DALARAN_Q.finditer(_read(dalaran)):
            quests_of[m[1]] = [int(q) for q in re.findall(r"\d+", m[2])]
    dungeons: dict[str, Facts] = {}
    for raw in _fields(_table_after(_read(path), "ns.DUNGEONS = ", path)).values():
        d = _fields(raw)
        key = d.get("key")
        if not isinstance(key, str):
            continue
        bosses = []
        for b in _fields(loot_by.get(key)).values():
            bf = _fields(b)
            if not isinstance(bf.get("n"), str):
                continue
            new_boss = bf.get("new") is True
            bosses.append(
                _clean(
                    {
                        "name": bf["n"],
                        "npc": _int(bf.get("id")),
                        "level": _int(bf.get("lv")),
                        "loot": [
                            # taux de ForeverChanges (Classic) : un objet ou un boss nouveau n'en a pas
                            _loot(
                                _fields(i)["id"],
                                _rate(_fields(i).get("p")),
                                classic=not (new_boss or _fields(i).get("new") is True),
                            )
                            for i in _fields(bf.get("items")).values()
                            if isinstance(_fields(i).get("id"), int)
                        ],
                    }
                )
            )
        map_id = instance_of.get(key)
        facts = {
            "name": d.get("en"),
            "map": map_id,
            "source_key": key,
            "levels": _levels(d.get("min"), d.get("max")),
            "entrance": {"map": d["map"], "x": float(d["x"]), "y": float(d["y"])}
            if isinstance(d.get("map"), int) and isinstance(d.get("x"), int | float)
            else None,
            "new": True if d.get("new") is True else None,
            "bosses": bosses,
            "quests": quests_of.get(key) or _ints(d.get("q")),
            "trash_npcs": trash.get(key),
        }
        _put(dungeons, facts)
    notes = ["Forever Guide : taux des donjons classiques repris de ForeverChanges (Classic) ; nouveaux sans taux"]
    return SourceDungeons(_info("forever_guide", addon, _version(addon), files), dungeons, {}, {}, notes)


def _full_version(toc: Path) -> str | None:
    """Version complète d'un `.toc` (« Forever 1.60.1 » : avec espaces, contrairement à `_version`)."""
    if not toc.is_file():
        return None
    m = re.search(r"^## Version:\s*(.+?)\s*$", _read(toc), re.MULTILINE)
    return m[1] if m else None


# --- AtlasLoot Classic Forever -------------------------------------------------------------------------------------


def _atlas_rates(path: Path) -> dict[int, dict[int, float]]:
    text = _read(path)
    i = text.find("local DropRateData = ")
    if i < 0:
        return {}
    value, _ = parse_lua_value_at(text, i + len("local DropRateData = "))
    return {
        npc: {item: float(p) for item, p in _fields(items).items() if isinstance(item, int)}
        for npc, items in _fields(value).items()
        if isinstance(npc, int)
    }


def read_atlasloot(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / ATLAS
    path = addon / "data.lua"
    if not path.is_file():
        return None
    files = [path]
    rates: dict[int, dict[int, float]] = {}
    drop = addon / "droprate.lua"
    if drop.is_file():
        files.append(drop)
        rates = _atlas_rates(drop)
    text = _read(path)
    starts = [m for m in _ATLAS_BLOCK.finditer(text)]
    dungeons: dict[str, Facts] = {}
    for n, m in enumerate(starts):
        block = text[m.start() : starts[n + 1].start() if n + 1 < len(starts) else len(text)]
        if "DUNGEON_CONTENT" not in block:
            continue
        lr = re.search(r"LevelRange\s*=\s*(?:GetForVersion\(\s*)?\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", block)
        if not lr:
            continue
        instance = re.search(r"\bInstanceID\s*=\s*(\d+)", block)
        head = block.split("items", 1)[0]
        name = re.search(r'name\s*=\s*AL\["([^"]+)"\]', head) or re.search(r'name\s*=\s*"([^"]+)"', head)
        bosses = []
        for bm in re.finditer(
            r'\{\s*(?:--[^\n]*\n\s*)?name\s*=\s*AL\["([^"]+)"\],(.*?)\[NORMAL_DIFF\]\s*=\s*\{(.*?)\n\t\t\t\}',
            block,
            re.DOTALL,
        ):
            npc = re.search(r"npcID\s*=\s*(\d+)", bm[2])
            level = re.search(r"\bLevel\s*=\s*(\d+)", bm[2])
            npc_id = int(npc[1]) if npc else None
            items = [int(x) for x in re.findall(r"\{\s*\d+\s*,\s*(\d+)", bm[3])]
            own = rates.get(npc_id, {}) if npc_id is not None else {}
            bosses.append(
                _clean(
                    {
                        "name": bm[1],
                        "npc": npc_id,
                        "level": int(level[1]) if level else None,
                        "loot": [_loot(i, _rate(own.get(i)), classic=i in own) for i in items],
                    }
                )
            )
        facts = {
            "name": name[1] if name else m[1],
            "map": int(instance[1]) if instance else None,
            "source_key": m[1],
            "access_level": int(lr[1]),
            "levels": {"min": int(lr[2]), "max": int(lr[3])},
            "bosses": bosses,
        }
        _put(dungeons, facts)
    notes = ["AtlasLoot : taux de droprate.lua repris de Classic (aucun PNJ de Forever), étiquetés classic"]
    return SourceDungeons(_info("atlasloot", addon, _full_version(addon / ATLAS_TOC), files), dungeons, {}, {}, notes)


# --- Forever Companion ---------------------------------------------------------------------------------------------


def read_companion(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / COMPANION
    path = addon / "Data" / "Loot.lua"
    if not path.is_file():
        return None
    value = _value_after(_read(path), "ForeverCompanionData.dungeons = ", path)
    if value is None:
        return None
    dungeons: dict[str, Facts] = {}
    for raw in _fields(value).values():
        d = _fields(raw)
        if d.get("raid") or not isinstance(d.get("n"), str):
            continue
        lv = _fields(d.get("lv"))
        bosses = [
            {
                "name": _fields(b).get("n"),
                "loot": [
                    _loot(_fields(i)["id"], _rate(_fields(i).get("d"), FRACTION), classic=True)
                    for i in _fields(_fields(b).get("i")).values()
                    if isinstance(_fields(i).get("id"), int)
                ],
            }
            for b in _fields(d.get("b")).values()
            if isinstance(_fields(b).get("n"), str)
        ]
        facts = {
            "name": d["n"],
            "source_key": d.get("id"),
            "levels": _levels(lv.get(1), lv.get(2)),
            "new": True if d.get("new") is True else None,
            "bosses": bosses,
        }
        dungeons[_key(None, d["n"])] = _clean(facts)
    notes = ["Forever Companion : taux d'origine Classic (fraction), étiquetés classic ; quêtes sans identifiant"]
    return SourceDungeons(_info("companion", addon, _version(addon), [path]), dungeons, {}, {}, notes)


# --- Zone Info: Forever --------------------------------------------------------------------------------------------


def read_zoneinfo(addons_dir: Path) -> SourceDungeons | None:
    addon = addons_dir / ZONEINFO
    path = addon / "ZoneInfoForever.lua"
    if not path.is_file():
        return None
    text = _BLOCK_COMMENT.sub("", _read(path))
    value = _value_after(text, "local mapTable = ", path)
    dungeons: dict[str, Facts] = {}
    for zone, row in _fields(value).items():
        for entry in _fields(_fields(row).get("dungeons")).values():
            e = _fields(entry)
            raw_text = e.get("text")
            label = raw_text if isinstance(raw_text, str) else ""
            m = _RANGE_TEXT.search(label)
            levels = {"min": int(m[1]), "max": int(m[2])} if m else None
            area = _int(e.get("id"))
            if area is not None:
                key = f"area:{area}"
                facts = {"area": area, "zone_map": zone, "levels": levels}
            else:
                nm = _NAME_BEFORE_RANGE.match(label)
                if not nm or not nm[1]:
                    continue
                key = f"name:{nm[1]}"
                facts = {"name": nm[1], "zone_map": zone, "levels": levels}
            dungeons[key] = _clean(facts)
    notes = ["Zone Info: Forever : plages de Classic (pas de Forever) sauf nouveaux donjons, au mieux suppose"]
    return SourceDungeons(_info("zoneinfo", addon, _version(addon), [path]), dungeons, {}, {}, notes)


def dungeon_source_files(addons_dir: Path, wtf_dir: Path | None) -> list[Path]:
    """Fichiers que les lecteurs liraient (présents seulement), pour l'empreinte du cache des donjons."""
    candidates = [
        *sorted((addons_dir / NAOWH_DJ / "Data" / "Dungeons").glob("*.lua")),
        *(addons_dir / NAOWH_DJ / "Data" / f for f in ("Quests.lua", "QuestChains.lua", "BossInfo.lua", "Build.lua")),
        *(addons_dir / FOJJI / "Data" / f for f in ("Dungeons.lua", "Chains.lua")),
        *(
            addons_dir / FDJ / "Data" / f
            for f in ("Dungeons.lua", "Bosses.lua", "DungeonEntrances.lua", "QuestChains.lua")
        ),
        *(
            addons_dir / GUIDE / f
            for f in ("DungeonData.lua", "DalaranData.lua", "DungeonLoot.lua", "DungeonTrash.lua")
        ),
        addons_dir / ATLAS / "data.lua",
        addons_dir / ATLAS / "droprate.lua",
        addons_dir / COMPANION / "Data" / "Loot.lua",
        addons_dir / ZONEINFO / "ZoneInfoForever.lua",
    ]
    for addon in (NAOWH_DJ, FOJJI, FDJ, GUIDE, ATLAS, COMPANION, ZONEINFO):  # versions rendues dans la provenance
        candidates += sorted((addons_dir / addon).glob("*.toc"))
    if wtf_dir is not None and wtf_dir.is_dir():
        candidates += sorted(wtf_dir.glob(f"Account/*/SavedVariables/{NAOWH_SV}"))
    return [p for p in candidates if p.is_file()]
