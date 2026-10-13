"""Extrait hors ligne les fixtures des quêtes de T04d (client et addons installés), sans données personnelles.

    uv run python scripts/extract_quest_fixtures.py questcache [--wow <dossier du client>]
    uv run python scripts/extract_quest_fixtures.py questxp [--version 1.60.1.70338]

`questcache` : en-tête de `Cache/WDB/enUS/questcache.wdb` et les enregistrements de `QUESTCACHE_IDS` recopiés octet
pour octet (texte des quêtes compris, c'est celui du client), puis le couple de fin (0, 0) ; écrit
`tests/fixtures/client/questcache_sample.wdb`.

`questxp` : table `QuestXP` du cache de `forever fetch` recopiée octet pour octet dans
`tests/fixtures/client/QuestXP.csv`."""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_cache_dir, default_wow_dir
from forever.pipeline.fetch import table_path
from forever.pipeline.questcache import ENTRY, HEADER, questcache_path

OUT = ROOT / "tests" / "fixtures" / "client"
# 479 (plan T04d) ; 421 retouchée (niveau requis) ; 5725 quête de donjon (multiplicateur relevé) ; quêtes de Durotar
# (14) et des Tarides (17) présentes dans la fixture de Questie ; quêtes propres à Forever (ID ≥ 90000).
QUESTCACHE_IDS = (479, 421, 5725, 825, 786, 823, 784, 851, 863, 6365, 97249, 96638)


def extract_questcache(wow: Path) -> Path:
    raw = questcache_path(wow).read_bytes()
    out = bytearray(raw[: HEADER.size])
    offset = HEADER.size
    kept: dict[int, bytes] = {}
    while offset + ENTRY.size <= len(raw):
        quest, length = ENTRY.unpack_from(raw, offset)
        if quest == 0 and length == 0:
            break
        if quest in QUESTCACHE_IDS:
            kept[quest] = raw[offset : offset + ENTRY.size + length]
        offset += ENTRY.size + length
    missing = [q for q in QUESTCACHE_IDS if q not in kept]
    if missing:
        raise SystemExit(f"quêtes absentes du cache : {missing}")
    for quest in QUESTCACHE_IDS:
        out += kept[quest]
    out += struct.pack("<II", 0, 0)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "questcache_sample.wdb"
    target.write_bytes(bytes(out))
    return target


def extract_questxp(version: str) -> Path:
    source = table_path(default_cache_dir(), version, "enUS", "QuestXP")
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "QuestXP.csv"
    target.write_bytes(source.read_bytes())
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="what", required=True)
    qc = sub.add_parser("questcache")
    qc.add_argument("--wow", type=Path, default=None)
    qx = sub.add_parser("questxp")
    qx.add_argument("--version", default="1.60.1.70338")
    args = parser.parse_args()
    if args.what == "questcache":
        print(extract_questcache(args.wow or default_wow_dir()))
    else:
        print(extract_questxp(args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
