"""Extrait hors ligne une fixture de `DBCache.bin` du client (T08c, bloc A) et l'extrait du journal des correctifs.

    uv run python scripts/extract_dbcache_fixture.py <DBCache.bin> [--journal <cache>/hotfixes.json]
        [--out tests/fixtures/hotfix/]

Lecture locale seulement. Sorties (fins de ligne LF, octets écrits par `write_bytes`) :
- `DBCache.bin` : en-tête recopié (44 octets), puis les entrées choisies, dans l'ordre du fichier source :
  toutes les entrées des poussées `PUSHES` ; la première entrée de chaque poussée de `ONE_OF` (tables hors du
  projet) ; deux réponses `DBReply` de `DBREPLY` ; le groupe de réponses d'objets de `ITEM_REPLY` ; puis deux
  entrées **synthétiques** (même table, même enregistrement absent des tables, deux poussées positives, la plus haute
  placée avant) ; **aucune entrée `TactKey`** (clés de chiffrement : jamais lues ni recopiées, contrôlé) ;
- `hotfixes-70170.json` : entrées du journal du cache (`forever hotfixes`) des poussées `PUSHES`, gardées pour le build
  de l'en-tête (lignes de `Hotfix.log` du démarrage du client de ce build) ;
- section « Fixture `DBCache.bin` » de `README.md` (entre deux marqueurs), dont le bloc JSON des comptes que lisent
  les tests.
Format d'une entrée : `XFTH`, `int32` (sens non établi), `int32 push_id`, `uint32 unique_id`, `uint32 table_hash`,
`uint32 rec_id`, `uint32 data_size`, `uint8 status` + 3 octets, puis les données. Ne pas éditer la fixture à la
main : relancer le script."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures" / "hotfix"
HEADER = 44
ENTRY = struct.Struct("<4siiIIIIB3x")
SIGNATURE = b"XFTH"
PUSHES = (112323, 112347, 112349)  # TraitNode hors classe, refonte du Guerrier, correctif de sorts
ONE_OF = (112340, 112350)  # GlobalStrings, QuestV2CliTask (INVALID) : tables hors du projet (hachage inconnu)
DBREPLY = ("Spell", 15147, 2)  # réponse « enregistrement absent », deux copies
ITEM_REPLY = 720  # réponses d'objets : push_id == unique_id == 0x01000000 + identifiant de l'objet
ITEM_FLAG = 0x01000000
SYNTHETIC = ("SpellLevels", 999901, (100002, 100001))  # DELETE (poussée haute) puis VALID (poussée basse)
SYNTHETIC_UNIQUE = (900000002, 900000001)
README_START = "<!-- dbcache:début (écrit par scripts/extract_dbcache_fixture.py) -->"
README_END = "<!-- dbcache:fin -->"
_T = (
    0x486E26EE, 0xDCAA16B3, 0xE1918EEF, 0x202DAFDB, 0x341C7DC7, 0x1C365303, 0x40EF2D37, 0x65FD5E49,
    0xD6057177, 0x904ECE93, 0x1C38024F, 0x98FD323B, 0xE3061AE7, 0xA39B0FA1, 0x9797F25F, 0xE4444563,
)  # fmt: skip


def table_hash(name: str) -> int:
    """`SStrHash` de Storm (majuscules, graine 0x7FED7FED), hachage des noms de tables de `DBCache.bin`."""
    seed, shift = 0x7FED7FED, 0xEEEEEEEE
    for ch in name.upper():
        c = ord(ch)
        seed = ((_T[c >> 4] - _T[c & 0xF]) & 0xFFFFFFFF) ^ ((shift + seed) & 0xFFFFFFFF)
        shift = (c + seed + 33 * shift + 3) & 0xFFFFFFFF
    return seed or 1


def entries(raw: bytes) -> list[tuple[tuple[int, ...], bytes]]:
    out = []
    off = HEADER
    while off < len(raw):
        sig, region, push, unique, th, rec, size, status = ENTRY.unpack_from(raw, off)
        if sig != SIGNATURE:
            raise SystemExit(f"signature absente à l'octet {off}")
        end = off + ENTRY.size + size
        out.append(((region, push, unique, th, rec, size, status), raw[off:end]))
        off = end
    return out


def pack(fields: tuple[int, ...], data: bytes) -> bytes:
    region, push, unique, th, rec, _size, status = fields
    return ENTRY.pack(SIGNATURE, region, push, unique, th, rec, len(data), status) + data


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dbcache", type=Path)
    parser.add_argument("--journal", type=Path, default=Path.home() / ".cache" / "forever" / "hotfixes.json")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    raw = args.dbcache.read_bytes()
    if raw[:4] != SIGNATURE:
        raise SystemExit("en-tête XFTH absent")
    fmt, build = struct.unpack_from("<II", raw, 4)
    tact = table_hash("TactKey")
    spell, levels = table_hash(DBREPLY[0]), table_hash(SYNTHETIC[0])
    chosen: list[bytes] = []
    first_of: set[int] = set()
    replies = 0
    template: bytes | None = None
    for fields, blob in entries(raw):
        _region, push, unique, th, rec, _size, status = fields
        if th == tact:
            continue
        keep = push in PUSHES
        if push in ONE_OF and push not in first_of:
            first_of.add(push)
            keep = True
        if push == -1 and th == spell and rec == DBREPLY[1] and replies < DBREPLY[2]:
            replies += 1
            keep = True
        if push == ITEM_FLAG + ITEM_REPLY and unique == push and rec == ITEM_REPLY:
            keep = True
        if keep:
            chosen.append(blob)
        if template is None and push in PUSHES and th == levels and status == 1:
            template = blob[ENTRY.size :]
    if template is None:
        raise SystemExit(f"aucune entrée {SYNTHETIC[0]} VALID dans les poussées {PUSHES}")
    _, rec_id, (high, low) = SYNTHETIC
    region = ENTRY.unpack_from(chosen[0])[1]
    chosen.append(pack((region, high, SYNTHETIC_UNIQUE[0], levels, rec_id, 0, 2), b""))
    chosen.append(pack((region, low, SYNTHETIC_UNIQUE[1], levels, rec_id, 0, 1), template))
    body = raw[:HEADER] + b"".join(chosen)
    if any(ENTRY.unpack_from(b)[4] == tact for b in chosen):
        raise SystemExit("entrée TactKey dans la sélection")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "DBCache.bin").write_bytes(body)

    kept = entries(body)
    status_names = {1: "VALID", 2: "DELETE", 3: "INVALID", 4: "NOTPUBLIC"}
    counts = {
        "format": fmt,
        "build": build,
        "entries": len(kept),
        "size": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "by_status": dict(sorted(Counter(status_names[f[6]] for f, _ in kept).items())),
        "pushes": dict(sorted(Counter(str(f[1]) for f, _ in kept).items())),
        "synthetic": [
            {"table": SYNTHETIC[0], "rec_id": rec_id, "push_id": high, "status": "DELETE"},
            {"table": SYNTHETIC[0], "rec_id": rec_id, "push_id": low, "status": "VALID"},
        ],
    }

    journal = json.loads(args.journal.read_text(encoding="utf-8")).get("entries", [])
    wanted = {str(p) for p in PUSHES}
    lines = [e for e in journal if e.get("push") in wanted and str(e.get("client_build", "")).endswith(f".{build}")]
    doc = {"schema_version": 1, "entries": lines}
    (args.out / "hotfixes-70170.json").write_bytes(
        (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    )
    counts["journal_lines"] = len(lines)

    readme_path = args.out / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    if README_START in readme:
        readme = readme[: readme.index(README_START)].rstrip("\n") + "\n"
    section = [
        README_START,
        "",
        "## Fixture `DBCache.bin` (T08c, bloc A)",
        "",
        "- Extraite du `Cache/ADB/enUS/DBCache.bin` du poste de",
        f"  l'utilisateur (build {build}, {len(raw)} octets, sha256 `{hashlib.sha256(raw).hexdigest()[:16]}…`), lecture",
        "  locale par `scripts/extract_dbcache_fixture.py` ; en-tête recopié ; entrées réelles choisies : toutes celles",
        f"  des poussées {', '.join(map(str, PUSHES))}, la première entrée des poussées {', '.join(map(str, ONE_OF))} (tables",
        f"  hors du projet), deux réponses `DBReply` ({DBREPLY[0]} {DBREPLY[1]}), les réponses d'objets de l'objet",
        f"  {ITEM_REPLY} (poussée 0x01000000 + identifiant) ; aucune entrée `TactKey`.",
        f"- Entrées **synthétiques** (signalées) : `{SYNTHETIC[0]}` {rec_id}, absent des tables, `DELETE` en poussée",
        f"  {high} placée avant un `VALID` en poussée {low} (données recopiées d'une entrée réelle) : la poussée la plus",
        "  haute l'emporte, quel que soit l'ordre du fichier.",
        "- `hotfixes-70170.json` : entrées du journal du cache (`forever hotfixes`, lignes de `Hotfix.log` du",
        f"  démarrage du client {build} du 2026-10-02) des mêmes poussées, gardées pour ce build.",
        "- Comptes lus par les tests (ne pas éditer : relancer le script) :",
        "",
        "```json",
        json.dumps(counts, ensure_ascii=False, indent=1),
        "```",
        "",
        README_END,
        "",
    ]
    readme_path.write_bytes((readme + "\n" + "\n".join(section)).encode("utf-8"))
    print(json.dumps(counts, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
