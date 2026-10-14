"""Sources locales des trajets et des maîtres de classe d'une feuille de route (RX1, bloc F, décision 133).

Lus en local dans les addons installés, jamais recopiés dans le dépôt :

- Naowh Forever Journeys (droits réservés) : bateaux, zeppelins, portails et tram (`Data/Network.lua`), vitesses
  et frais d'embarquement (`Constants.lua`), graphe de marche par continent (`NaowhForever_JourneysData/Data/
  Map<continent>.lua` : base64, deflate, CBOR ; nœuds en yards du monde, arêtes pondérées en yards de marche) ;
- Naowh Forever Training : niveaux où la classe apprend de nouveaux sorts (`Data/TrainingData.lua`) ;
- Questie : maîtres de classe (titre « <Classe> Trainer » de `classicNpcDB.lua`) et leurs positions.

Les vols restent ceux du client (`travel.json`, le client prime) ; les durées des transports sont `suppose`."""

from __future__ import annotations

import base64
import re
import zlib
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError
from forever.pipeline.cbor import CborError, decode
from forever.pipeline.quest_sources import _fields, _read, _table_after

JOURNEYS = "NaowhForever_Journeys"
JOURNEYS_DATA = "NaowhForever_JourneysData"
TRAINING = "NaowhForever_Training"
PROFESSIONS = "NaowhForever_Professions"
NETWORK = Path("Data") / "Network.lua"
CONSTANTS = Path("Constants.lua")


class Dock(NamedTuple):
    continent: int
    x: float
    y: float
    ui_map: int | None
    name: str
    wait: float  # secondes d'attente au quai (valeur de l'addon)
    length: float  # yards jusqu'au quai suivant


class Ship(NamedTuple):
    kind: str  # Boat | Zeppelin
    sides: str  # « A », « H » ou « AH »
    docks: tuple[Dock, ...]


class Link(NamedTuple):
    kind: str  # Portal | Tram
    sides: str
    seconds: float
    a: tuple[int, float, float, str]  # continent, x, y, nom
    b: tuple[int, float, float, str]


class JourneysNetwork(NamedTuple):
    ships: tuple[Ship, ...]
    links: tuple[Link, ...]
    speeds: dict[str, float]  # yards par seconde par sorte de navire
    board_s: float
    loading_s: float
    version: str | None


class TrainerNpc(NamedTuple):
    npc: int
    name: str
    title: str
    sides: str
    ui_map: int
    x: float  # pourcentage de la carte
    y: float


def _version(addon: Path) -> str | None:
    for toc in sorted(addon.glob("*.toc")):
        for line in toc.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("## Version:"):
                return line.split(":", 1)[1].strip()
    return None


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _dock(raw: Any) -> Dock | None:
    f = _fields(raw)
    c, x, y, wait, length = f.get(1), _num(f.get(2)), _num(f.get(3)), _num(f.get(6)), _num(f.get(7))
    if not isinstance(c, int) or x is None or y is None or wait is None or length is None:
        return None
    ui_map = f.get(4) if isinstance(f.get(4), int) else None
    return Dock(c, x, y, ui_map, str(f.get(5) or ""), wait, length)


def _end(raw: Any) -> tuple[int, float, float, str] | None:
    f = _fields(raw)
    c, x, y = f.get(1), _num(f.get(2)), _num(f.get(3))
    if not isinstance(c, int) or x is None or y is None:
        return None
    return c, x, y, str(f.get(4) or "")


def read_journeys_network(addons: Path) -> JourneysNetwork | None:
    """Transports de Journeys (None si l'addon manque ou ne se lit pas)."""
    addon = addons / JOURNEYS
    network, constants = addon / NETWORK, addon / CONSTANTS
    if not network.is_file() or not constants.is_file():
        return None
    try:
        raw = _fields(_table_after(_read(network), "ns.JourneyNetwork = ", network))
        const = _fields(_table_after(_read(constants), "ns.Journeys.C = ", constants))
    except DataSchemaError:
        return None
    speeds = {str(k): float(v) for k, v in _fields(const.get("SHIP_SPEED")).items() if _num(v)}
    board, loading = _num(const.get("BOARD")), _num(const.get("LOADING"))
    if not speeds or board is None or loading is None:
        return None
    ships: list[Ship] = []
    for row in _fields(raw.get("ships")).values():
        f = _fields(row)
        docks = [d for d in (_dock(f[i]) for i in sorted(k for k in f if isinstance(k, int) and k >= 3)) if d]
        if isinstance(f.get(1), str) and isinstance(f.get(2), str) and len(docks) >= 2:
            ships.append(Ship(f[1], f[2], tuple(docks)))
    links: list[Link] = []
    for row in _fields(raw.get("links")).values():
        f = _fields(row)
        a, b, seconds = _end(f.get(4)), _end(f.get(5)), _num(f.get(3))
        if isinstance(f.get(1), str) and isinstance(f.get(2), str) and a and b and seconds is not None:
            links.append(Link(f[1], f[2], seconds, a, b))
    return JourneysNetwork(tuple(ships), tuple(links), speeds, board, loading, _version(addon))


_GRAPH = re.compile(r'ns\.JourneyData\.graph\[(\d+)\]\s*=\s*"([^"]+)"')


def _unpack(text: str) -> Any:
    raw = base64.b64decode(text)
    try:
        data = zlib.decompress(raw, -zlib.MAX_WBITS)
    except zlib.error:
        data = zlib.decompress(raw)
    return decode(data)


def read_journeys_walks(addons: Path) -> dict[int, tuple[list[tuple[float, float]], list[tuple[int, int, float]]]]:
    """Graphe de marche par continent : (nœuds (x, y), arêtes (a, b, yards), indices de 0) ; vide sans l'addon."""
    out: dict[int, tuple[list[tuple[float, float]], list[tuple[int, int, float]]]] = {}
    data = addons / JOURNEYS_DATA / "Data"
    if not data.is_dir():
        return out
    for path in sorted(data.glob("Map*.lua")):
        for m in _GRAPH.finditer(_read(path)):
            try:
                doc = _fields(_unpack(m[2]))
            except (ValueError, zlib.error, CborError):
                continue
            c, e = doc.get("c"), doc.get("e")
            if not isinstance(c, list) or not isinstance(e, list):
                continue
            points = [(float(c[i]), float(c[i + 1])) for i in range(0, len(c) - 2, 3)]
            edges = [
                (min(int(e[i]), int(e[i + 1])) - 1, max(int(e[i]), int(e[i + 1])) - 1, float(e[i + 2]))
                for i in range(0, len(e) - 2, 3)
                if 1 <= int(e[i]) <= len(points) and 1 <= int(e[i + 1]) <= len(points)
            ]
            out[int(m[1])] = (points, edges)
    return out


def read_training_levels(addons: Path) -> dict[int, tuple[int, ...]]:
    """Niveaux où chaque classe (identifiant du client) apprend un sort chez son maître (sorts de quête exclus)."""
    path = addons / TRAINING / "Data" / "TrainingData.lua"
    if not path.is_file():
        return {}
    try:
        raw = _fields(_table_after(_read(path), "ns.TrainingData = ", path))
    except DataSchemaError:
        return {}
    out: dict[int, tuple[int, ...]] = {}
    for cls, rows in raw.items():
        if not isinstance(cls, int):
            continue
        levels = set()
        for row in _fields(rows).values():
            f = _fields(row)
            if isinstance(f.get(1), int) and not f.get("quest"):
                levels.add(f[1])
        out[cls] = tuple(sorted(levels))
    return out


def read_questie_trainers(addons: Path, title: str) -> list[TrainerNpc]:
    """PNJ de Questie dont le titre est exactement `title` (« Mage Trainer »), une position par point d'apparition."""
    from forever.pipeline.quest_sources import QUESTIE, QUESTIE_NPCS, QUESTIE_ZONES, _questie_keys, _return_tables

    root = addons / QUESTIE
    npcs, zones = root / QUESTIE_NPCS, root / QUESTIE_ZONES
    if not npcs.is_file():
        return []
    area_to_map: dict[int, int] = {}
    if zones.is_file():
        for table in reversed(_return_tables(_read(zones), zones)):
            for k, v in _fields(table).items():
                if isinstance(k, int) and isinstance(v, int) and v:
                    area_to_map[k] = v
    text = _read(npcs)
    keys = _questie_keys(text, "npcData", npcs)
    if "subName" not in keys or "spawns" not in keys:
        return []
    out: list[TrainerNpc] = []
    for npc_id, row in sorted(_fields((_return_tables(text, npcs) or [{}])[0]).items(), key=lambda kv: str(kv[0])):
        f = _fields(row)
        if not isinstance(npc_id, int) or f.get(keys["subName"]) != title:
            continue
        name = str(f.get(keys["name"]) or npc_id)
        sides = f.get(keys.get("friendlyToFaction", -1))
        for zone, points in sorted(_fields(f.get(keys["spawns"])).items(), key=lambda kv: str(kv[0])):
            ui_map = area_to_map.get(zone) if isinstance(zone, int) else None
            if ui_map is None:
                continue
            for point in _fields(points).values():
                p = _fields(point)
                x, y = _num(p.get(1)), _num(p.get(2))
                if x is not None and y is not None:
                    out.append(TrainerNpc(npc_id, name, title, str(sides or ""), ui_map, x, y))
    return out


class ProfessionRank(NamedTuple):
    cap: int  # rang maximal après l'apprentissage
    skill: int  # compétence requise
    level: int | None  # niveau requis (None : aucun)
    name: str


class ProfessionData(NamedTuple):
    skill_line: int
    name: str
    trainers: list[TrainerNpc]
    ranks: list[ProfessionRank]


def read_profession_data(addons: Path) -> dict[str, ProfessionData]:
    """Métiers de Naowh Forever Professions (`Data/RecipeData.lua`) : maîtres et leurs positions, rangs ; clé : nom
    anglais du métier (tiré du nom des rangs). Vide sans l'addon."""
    path = addons / PROFESSIONS / "Data" / "RecipeData.lua"
    if not path.is_file():
        return {}
    try:
        raw = _fields(_table_after(_read(path), "ns.RecipeData = ", path))
    except DataSchemaError:
        return {}
    out: dict[str, ProfessionData] = {}
    for line, entry in raw.items():
        f = _fields(entry)
        ranks: list[ProfessionRank] = []
        for row in _fields(f.get("ranks")).values():
            r = _fields(row)
            if isinstance(r.get("cap"), int) and isinstance(r.get("skill"), int):
                level = r.get("level") if isinstance(r.get("level"), int) else None
                ranks.append(ProfessionRank(r["cap"], r["skill"], level, str(r.get("name") or "")))
        named = next((r.name for r in ranks if " " in r.name), None)
        if not isinstance(line, int) or named is None:
            continue
        name = named.split(" ", 1)[1]
        trainers: list[TrainerNpc] = []
        for row in _fields(f.get("trainers")).values():
            t = _fields(row)
            x, y = _num(t.get(5)), _num(t.get(6))
            if isinstance(t.get(1), int) and isinstance(t.get(4), int) and x is not None and y is not None:
                trainers.append(
                    TrainerNpc(t[1], str(t.get(2) or ""), f"{name} Trainer", str(t.get(3) or ""), t[4], x, y)
                )
        out[name] = ProfessionData(line, name, trainers, ranks)
    return out
