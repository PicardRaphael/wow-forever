"""Extrait hors ligne les fixtures des donjons de DJ1 (tables du client, cache de `forever fetch`).

    uv run python scripts/extract_dungeon_fixtures.py [--version 1.60.1.70338]

Écrit `tests/fixtures/wago/dungeons/enUS/<Table>.csv` : en-tête complet de chaque table et seulement les lignes des
cartes de `MAPS` (et celles qu'elles citent : entrées de recherche de groupe de `LFG`, niveaux, rencontres, zones).
Les cellules sont recopiées telles quelles ; seules les lignes sont filtrées. Aucun chiffre de jeu ici : les
identifiants désignent des lignes du client."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_cache_dir
from forever.pipeline.fetch import table_path

OUT = ROOT / "tests" / "fixtures" / "wago" / "dungeons" / "enUS"
# Donjons classiques (Ragefire Chasm, Deadmines, Scarlet Monastery, Gnomeregan avec ses rencontres d'autres
# difficultés), nouveaux (The Hall of Thanes, Excavation Site: Wetlands, Ruins of Lordaeron, City of Dalaran),
# un raid (Molten Core), un champ de bataille (Warsong Gulch), une instance sans entrée de recherche (Karazhan Crypts).
MAPS = {389, 36, 189, 90, 3065, 2998, 2999, 2959, 409, 489, 2875}
LFG = {3, 5, 13, 17, 47, 53, 3271, 3272, 3273, 3274}


def _rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader), list(reader)


def _write(table: str, header: list[str], rows: list[list[str]]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    (OUT / f"{table}.csv").write_bytes(buf.getvalue().encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default="1.60.1.70338")
    args = parser.parse_args()
    cache = default_cache_dir()
    OUT.mkdir(parents=True, exist_ok=True)

    def load(table: str) -> tuple[list[str], list[list[str]]]:
        return _rows(table_path(cache, args.version, "enUS", table))

    header, rows = load("Map")
    _write("Map", header, [r for r in rows if int(r[header.index("ID")]) in MAPS])
    header, rows = load("LFGDungeons")
    lfg = [r for r in rows if int(r[header.index("ID")]) in LFG]
    tunings = {r[header.index("ContentTuningID")] for r in lfg}
    _write("LFGDungeons", header, lfg)
    header, rows = load("ContentTuning")
    _write("ContentTuning", header, [r for r in rows if r[header.index("ID")] in tunings])
    header, rows = load("DungeonEncounter")
    _write("DungeonEncounter", header, [r for r in rows if int(r[header.index("MapID")]) in MAPS])
    header, rows = load("AreaTable")
    keep = [
        r for r in rows if int(r[header.index("ContinentID")]) in MAPS and int(r[header.index("ParentAreaID")]) == 0
    ]
    _write("AreaTable", header, keep)
    print(f"fixtures écrites dans {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
