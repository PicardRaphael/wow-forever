"""Extrait hors ligne les fixtures des trajets de RX1 (tables du client, cache de `forever fetch`).

    uv run python scripts/extract_travel_fixtures.py [--version 1.60.1.70338]

Écrit `tests/fixtures/wago/travel/enUS/<Table>.csv` : en-tête complet de chaque table et seulement les lignes des
points de vol de `NODES`, des trajets de `PATHS` (et de leurs segments), des cartes de `UI_MAPS`. Les cellules sont
recopiées telles quelles ; seules les lignes sont filtrées. Aucun chiffre de jeu ici : les identifiants désignent des
lignes du client."""

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

OUT = ROOT / "tests" / "fixtures" / "wago" / "travel" / "enUS"
NODES = {2, 4, 12}  # Stormwind, Sentinel Hill, Darkshire
PATHS = {6, 23}  # Stormwind -> Sentinel Hill, Stormwind -> Darkshire
UI_MAPS = {1429, 1436, 1431}  # Elwynn Forest, Westfall, Duskwood


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

    header, rows = load("TaxiNodes")
    _write("TaxiNodes", header, [r for r in rows if int(r[header.index("ID")]) in NODES])
    header, rows = load("TaxiPath")
    _write("TaxiPath", header, [r for r in rows if int(r[header.index("ID")]) in PATHS])
    header, rows = load("TaxiPathNode")
    _write("TaxiPathNode", header, [r for r in rows if int(r[header.index("PathID")]) in PATHS])
    header, rows = load("UiMapAssignment")
    _write("UiMapAssignment", header, [r for r in rows if int(r[header.index("UiMapID")]) in UI_MAPS])
    print(f"fixtures écrites dans {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
