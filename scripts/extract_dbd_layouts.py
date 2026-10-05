"""Écrit les dispositions dérivées de WoWDBDefs pour une version (fixture de test, T08c, bloc B), hors ligne.

    uv run python scripts/extract_dbd_layouts.py [--version 1.60.1.70170] [--dbcache tests/fixtures/hotfix/DBCache.bin]

Lit les `.dbd` du cache de `forever fetch --dbd` (commit de `<cache>/dbd/dbd.json`), garde pour chaque table de la
fixture `DBCache.bin` lue par le projet le bloc qui nomme le build, et écrit
`tests/fixtures/dbd/layouts-<version>.json` : structure seulement (noms, types, tailles, annotations), aucun texte du
dépôt. Fins de ligne LF ; ne pas éditer le fichier à la main."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import DATA_DIR, default_cache_dir
from forever.pipeline.dbcache import known_tables, read_dbcache, table_names
from forever.pipeline.dbd import layout_for, layouts_to_json, parse_dbd
from forever.pipeline.fetch import DBD_EXTRA_TABLES, dbd_dir, read_dbd_index

OUT = ROOT / "tests" / "fixtures" / "dbd"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default="1.60.1.70170")
    parser.add_argument("--dbcache", type=Path, default=ROOT / "tests" / "fixtures" / "hotfix" / "DBCache.bin")
    args = parser.parse_args(argv)
    index = read_dbd_index(default_cache_dir())
    if index is None:
        raise SystemExit("aucun relevé de WoWDBDefs dans le cache : lancer forever fetch --dbd")
    rules = json.loads((DATA_DIR / args.version / "decode_rules.json").read_text(encoding="utf-8"))
    names = table_names(known_tables(rules) | set(DBD_EXTRA_TABLES))
    tables = sorted({names[e.table_hash] for e in read_dbcache(args.dbcache).entries if e.table_hash in names})
    folder = dbd_dir(default_cache_dir()) / str(index["commit"])
    layouts = {}
    for table in tables:
        layout = layout_for(parse_dbd((folder / f"{table}.dbd").read_text(encoding="utf-8"), table), args.version)
        if layout is None:
            raise SystemExit(f"{table} : aucun bloc pour {args.version}")
        layouts[table] = layout
    doc = layouts_to_json(layouts, str(index["repo"]), str(index["commit"]), args.version)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"layouts-{args.version}.json"
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"{path.relative_to(ROOT)} : {len(layouts)} tables")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
