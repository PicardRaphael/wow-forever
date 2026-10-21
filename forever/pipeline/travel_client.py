"""Trajets décodés du client (`travel.json`, RX1, bloc B).

Points de vol (`TaxiNodes` : nom, continent, position monde, camp par les drapeaux), trajets (`TaxiPath` : départ,
arrivée, coût) et leur longueur (somme des segments de `TaxiPathNode`, segment de téléportation ou de changement de
continent exclu), passage carte ↔ monde (`UiMapAssignment` : bornes de la carte de zone dans son continent). Toutes
les constantes de lecture viennent de `decode_rules.json` (`travel`) ; aucun chiffre de jeu ici. Registre : I19."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CsvMissingError
from forever.pipeline.fetch import DEFAULT_LOCALE
from forever.pipeline.tables import Row, read_table

TRAVEL_FILE = "travel.json"
TRAVEL_FILES = (TRAVEL_FILE,)
SCHEMA_VERSION = 1

Tables = Mapping[str, Sequence[Row]]


def travel_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des trajets (`travel_tables`, téléchargées à part, facultatives) :
    présentes, le fichier est décodé ; absentes, il est hérité de la base."""
    return [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("travel_tables", [])]


def load_travel_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    files = travel_table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {name: list(read_table(csv_dir / rel, name)) for name, rel in files}


def _faction(flags: int, spec: Mapping[str, Any]) -> str | None:
    """Camp d'un point de vol par ses drapeaux (`travel.faction_flags`) : « both » pour les deux camps, None pour
    aucun (point caché)."""
    found = [name for name, bit in spec["faction_flags"].items() if flags & int(bit)]
    return found[0] if len(found) == 1 else ("both" if found else None)


def _territory(mask: int, masks: Mapping[str, Any]) -> str:
    """Camp d'une zone par `AreaTable.FactionGroupMask` : un seul camp, les deux (`both`) ou aucun (`contested`)."""
    found = [name for name, bit in masks.items() if mask & int(bit)]
    return found[0] if len(found) == 1 else ("both" if found else "contested")


def _path_length(points: Sequence[Row], teleport: int) -> float:
    """Somme des segments d'un trajet, dans l'ordre des points ; un segment qui part d'un point de téléportation ou
    change de continent n'est pas compté."""
    ordered = sorted(points, key=lambda r: int(r["NodeIndex"]))
    total = 0.0
    for a, b in itertools.pairwise(ordered):
        if int(a["Flags"]) & teleport or int(a["ContinentID"]) != int(b["ContinentID"]):
            continue
        total += math.dist(
            (float(a["Loc_0"]), float(a["Loc_1"]), float(a["Loc_2"])),
            (float(b["Loc_0"]), float(b["Loc_1"]), float(b["Loc_2"])),
        )
    return total


def decode_travel(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    spec = rules["travel"]
    teleport = int(spec["teleport_flag"])
    nodes = [
        {
            "id": int(r["ID"]),
            "name": str(r["Name_lang"]),
            "continent": int(r["ContinentID"]),
            "x": float(r["Pos_0"]),
            "y": float(r["Pos_1"]),
            "z": float(r["Pos_2"]),
            "faction": _faction(int(r["Flags"]), spec),
        }
        for r in sorted(tables["TaxiNodes"], key=lambda r: int(r["ID"]))
    ]
    by_path: dict[int, list[Row]] = {}
    for r in tables["TaxiPathNode"]:
        by_path.setdefault(int(r["PathID"]), []).append(r)
    known = {n["id"] for n in nodes}
    paths = []
    orphans = 0
    for r in sorted(tables["TaxiPath"], key=lambda r: int(r["ID"])):
        start, end = int(r["FromTaxiNode"]), int(r["ToTaxiNode"])
        if start not in known or end not in known:
            orphans += 1
            continue
        points = by_path.get(int(r["ID"]), [])
        paths.append(
            {
                "id": int(r["ID"]),
                "from": start,
                "to": end,
                "cost": int(r["Cost"]),
                "length": _path_length(points, teleport),
                "points": len(points),
            }
        )
    masks = spec.get("area_faction_masks") or {}
    area_mask = {int(r["ID"]): int(r["FactionGroupMask"]) for r in tables.get("AreaTable", ())} if masks else {}
    maps: list[dict[str, Any]] = [
        {
            "ui_map": int(r["UiMapID"]),
            "continent": int(r["MapID"]),
            "area": int(r["AreaID"]),
            "min_x": float(r["Region_0"]),
            "min_y": float(r["Region_1"]),
            "max_x": float(r["Region_3"]),
            "max_y": float(r["Region_4"]),
        }
        for r in sorted(tables["UiMapAssignment"], key=lambda r: (int(r["UiMapID"]), int(r["OrderIndex"])))
        if int(r["OrderIndex"]) == 0
    ]
    for m in maps:  # camp de la zone de la carte (AreaTable.FactionGroupMask, bits de travel.area_faction_masks)
        area = int(m["area"])
        if area in area_mask:
            m["territory"] = _territory(area_mask[area], masks)
    notes = [
        (
            f"{len(nodes)} point(s) de vol, {len(paths)} trajet(s) (longueur : somme des segments de TaxiPathNode, "
            f"téléportations exclues), {len(maps)} carte(s) de zone ; {orphans} trajet(s) vers un point absent écartés"
        ),
        (
            "camp d'un point de vol par ses drapeaux (decode_rules.json travel.faction_flags), sens probable ; "
            "conditions d'accès (ConditionID) non lues"
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "build": version,
        "nodes": nodes,
        "paths": paths,
        "maps": maps,
        "notes": notes,
        "source": f"Client {version} : tables TaxiNodes, TaxiPath, TaxiPathNode et UiMapAssignment "
        "(wago.tools, decode_rules.json travel)",
        "certainty": "certain",
    }


def travel_errors(doc: Any) -> list[str]:
    """Contrôle de forme du document."""
    if not isinstance(doc, dict):
        return [f"{TRAVEL_FILE} : objet attendu"]
    errors: list[str] = []
    for key, fields in (
        ("nodes", ("id", "name", "continent", "x", "y")),
        ("paths", ("id", "from", "to", "cost", "length")),
        ("maps", ("ui_map", "continent", "min_x", "min_y", "max_x", "max_y")),
    ):
        rows = doc.get(key)
        if not isinstance(rows, list):
            errors.append(f"{TRAVEL_FILE} : {key} : liste attendue")
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or any(f not in row for f in fields):
                errors.append(f"{TRAVEL_FILE} : {key}[{i}] : champs {', '.join(fields)} attendus")
                break
    if not errors:
        ids = {n["id"] for n in doc["nodes"]}
        bad = [p["id"] for p in doc["paths"] if p["from"] not in ids or p["to"] not in ids]
        if bad:
            errors.append(f"{TRAVEL_FILE} : trajet(s) vers un point absent : {bad[:5]}")
    return errors
