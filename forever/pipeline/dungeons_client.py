"""Donjons décodés du client (`dungeons.json`, DJ1, bloc A).

Instances de groupe (`Map`), entrées de l'outil de recherche de groupe (`LFGDungeons`) et leur niveau
(`ContentTuning`), rencontres (`DungeonEncounter`) et zones de l'instance (`AreaTable`). Le client ne relie pas une
entrée `LFGDungeons` à sa carte (colonne `MapID` vide) : le lien se fait par le nom, avec les alias déclarés dans
`decode_rules.json` (`dungeons.lfg_names`) ; une entrée non reliée est listée, jamais devinée. Les tables du journal
(`JournalInstance`, `JournalEncounter`, `JournalEncounterItem`) sont absentes de la version 1.60.1.70338 sur
wago.tools (question DON9) : aucun butin ne vient du client. Toutes les constantes de lecture viennent de
`decode_rules.json` ; aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CsvMissingError
from forever.pipeline.fetch import DEFAULT_LOCALE
from forever.pipeline.tables import Row, read_table

DUNGEON_FILE = "dungeons.json"
DUNGEON_FILES = (DUNGEON_FILE,)
SCHEMA_VERSION = 1

Tables = Mapping[str, Sequence[Row]]


def dungeon_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des donjons (`dungeon_tables`, téléchargées à part, facultatives) :
    présentes, le fichier est décodé ; absentes, il est hérité de la base."""
    return [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("dungeon_tables", [])]


def load_dungeon_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    files = dungeon_table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {name: list(read_table(csv_dir / rel, name)) for name, rel in files}


def normalize_name(name: str, prefixes: Sequence[str] = ("the ",)) -> str:
    """Nom comparable : minuscules, espaces réduits, préfixes retirés (« The Hall of Thanes » et « Hall of Thanes »
    se rejoignent)."""
    out = " ".join(name.lower().split())
    for prefix in prefixes:
        out = out.removeprefix(prefix)
    return out


def _level(value: int) -> int | None:
    return value or None


def _lfg_entry(row: Row, tun: Row | None, factions: Mapping[int, str]) -> dict[str, Any]:
    lo = int(tun["MinLevelSquish"]) if tun else 0
    hi = int(tun["MaxLevelSquish"]) if tun else 0
    return {
        "id": int(row["ID"]),
        "name": str(row["Name_lang"]),
        "level": lo if lo and lo == hi else None,
        "level_min": _level(lo),
        "level_max": _level(hi),
        "lfg_min": _level(int(tun["LfgMinLevel"])) if tun else None,
        "lfg_max": _level(int(tun["LfgMaxLevel"])) if tun else None,
        "faction": factions.get(int(row["Faction"])),
    }


def decode_dungeons(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Document `dungeons.json`."""
    spec = rules["dungeons"]
    prefixes = tuple(spec.get("strip_prefixes", []))
    party = int(spec["party_instance_type"])
    lfg_type = int(spec["lfg_dungeon_type"])
    difficulties = {int(d) for d in spec["difficulties"]}
    factions = {int(k): str(v) for k, v in spec.get("factions", {}).items()}
    aliases = {normalize_name(k, prefixes): normalize_name(v, prefixes) for k, v in spec.get("lfg_names", {}).items()}
    maps = sorted(tables["Map"], key=lambda r: int(r["ID"]))
    by_name: dict[str, list[Row]] = {}
    for m in maps:
        by_name.setdefault(normalize_name(str(m["MapName_lang"]), prefixes), []).append(m)
    tuning = {int(r["ID"]): r for r in tables["ContentTuning"]}
    lfg_by_map: dict[int, list[dict[str, Any]]] = {}
    unmatched: list[dict[str, Any]] = []
    for row in sorted(tables["LFGDungeons"], key=lambda r: int(r["ID"])):
        if int(row["TypeID"]) != lfg_type:
            continue
        key = normalize_name(str(row["Name_lang"]), prefixes)
        candidates = by_name.get(aliases.get(key, key), [])
        entry = _lfg_entry(row, tuning.get(int(row["ContentTuningID"])), factions)
        if len(candidates) != 1:
            unmatched.append({"id": entry["id"], "name": entry["name"], "maps": [int(m["ID"]) for m in candidates]})
            continue
        lfg_by_map.setdefault(int(candidates[0]["ID"]), []).append(entry)
    encounters: dict[int, list[Row]] = {}
    for e in tables["DungeonEncounter"]:
        if int(e["DifficultyID"]) in difficulties:
            encounters.setdefault(int(e["MapID"]), []).append(e)
    areas: dict[int, list[int]] = {}
    for a in sorted(tables["AreaTable"], key=lambda r: int(r["ID"])):
        if int(a["ParentAreaID"]) == 0:
            areas.setdefault(int(a["ContinentID"]), []).append(int(a["ID"]))
    area_names = {int(a["ID"]): normalize_name(str(a["AreaName_lang"]), prefixes) for a in tables["AreaTable"]}
    instances: dict[str, Any] = {}
    unlisted: list[dict[str, Any]] = []
    for m in maps:
        map_id = int(m["ID"])
        if int(m["InstanceType"]) != party:
            continue
        own = sorted(encounters.get(map_id, []), key=lambda r: (int(r["OrderIndex"]), int(r["ID"])))
        if map_id not in lfg_by_map:
            if own:
                unlisted.append({"map_id": map_id, "name": str(m["MapName_lang"]), "encounters": len(own)})
            continue
        name = normalize_name(str(m["MapName_lang"]), prefixes)
        zone = [a for a in areas.get(map_id, []) if area_names.get(a) == name]
        if int(m["AreaTableID"]) and int(m["AreaTableID"]) not in zone:
            zone.insert(0, int(m["AreaTableID"]))
        instances[str(map_id)] = {
            "name": str(m["MapName_lang"]),
            "areas": zone,
            "lfg": lfg_by_map[map_id],
            "encounters": [
                {
                    "id": int(e["ID"]),
                    "name": str(e["Name_lang"]),
                    "order": int(e["OrderIndex"]),
                    "flags": int(e["Flags"]),
                }
                for e in own
            ],
        }
    notes = [
        (
            f"{len(instances)} donjon(s) à 5 reliés à une entrée de recherche de groupe ; {len(unlisted)} instance(s) "
            f"de groupe avec rencontres sans entrée (unlisted) ; {len(unmatched)} entrée(s) non reliée(s) à une "
            "carte de groupe (unmatched_lfg)"
        ),
        (
            "niveau : ContentTuning (MinLevelSquish = MaxLevelSquish) de l'entrée de recherche de groupe, sens "
            "probable (niveau de contenu, DON9) ; lfg_min et lfg_max quand le client les renseigne"
        ),
        (
            "tables du journal (JournalInstance, JournalEncounter, JournalEncounterItem) absentes de la version sur "
            "wago.tools (DON9) : ni butin ni PNJ des boss dans ce fichier"
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "build": version,
        "instances": instances,
        "unlisted": unlisted,
        "unmatched_lfg": unmatched,
        "notes": notes,
        "source": f"Client {version} : tables Map, LFGDungeons, ContentTuning, DungeonEncounter et AreaTable "
        "(wago.tools, decode_rules.json dungeons)",
        "certainty": "certain",
    }


def dungeons_errors(doc: Any) -> list[str]:
    """Contrôle de forme du document."""
    if not isinstance(doc, dict):
        return [f"{DUNGEON_FILE} : objet attendu"]
    instances = doc.get("instances")
    if not isinstance(instances, dict):
        return [f"{DUNGEON_FILE} : instances : objet attendu"]
    errors: list[str] = []
    for key, inst in instances.items():
        if not key.isdigit() or not isinstance(inst, dict):
            errors.append(f"{DUNGEON_FILE} : instance {key!r} : clé numérique et objet attendus")
            continue
        if not isinstance(inst.get("name"), str) or not inst["name"]:
            errors.append(f"{DUNGEON_FILE} : instance {key} : nom attendu")
        if not isinstance(inst.get("lfg"), list) or not inst["lfg"]:
            errors.append(f"{DUNGEON_FILE} : instance {key} : entrée de recherche de groupe attendue")
        encounters = inst.get("encounters")
        if not isinstance(encounters, list) or any(
            not isinstance(e, dict) or not isinstance(e.get("id"), int) for e in encounters
        ):
            errors.append(f"{DUNGEON_FILE} : instance {key} : rencontres : liste d'objets avec id attendue")
    for name in ("unlisted", "unmatched_lfg", "notes"):
        if not isinstance(doc.get(name), list):
            errors.append(f"{DUNGEON_FILE} : {name} : liste attendue")
    return errors
