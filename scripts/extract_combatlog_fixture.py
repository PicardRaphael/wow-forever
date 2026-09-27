"""Anonymise hors ligne un journal de combat du client pour en faire une fixture de test (décision 8 du plan T04).

    uv run python scripts/extract_combatlog_fixture.py <WoWCombatLog-….txt> [--out tests/fixtures/combatlog/]
        [--useful] [--gzip]

- Le joueur « à moi » (drapeau d'affiliation 0x1 sur une unité) devient `Moi-Royaume`, GUID `Player-0000-00000000`.
- Les autres joueurs deviennent `Joueur1-Royaume`, `Joueur2-Royaume`… et `Player-0000-00000001`… dans l'ordre de
  première apparition ; chaque GUID est remplacé sur toute la ligne (il réapparaît dans le bloc avancé).
- Les familiers (GUID `Pet-…`, nom choisi par le joueur) deviennent `Familier1`, `Familier2`… ; GUID gardé.
- Créatures, objets, sorts et chiffres intacts ; nombre de lignes et d'événements conservés (contrôlé).
- `--useful` (décision 1 du plan T04b) : ne garde que les événements utiles aux mesures, avant l'anonymisation :
  tout événement dont la source ou la destination est le joueur « à moi » (incantations, ratés, baguette), tout
  événement de dégâts dont le bloc avancé décrit une créature (PV des monstres, quelle que soit la cible), les morts
  de créatures (`UNIT_DIED`, `PARTY_KILL`) et les changements de carte.
- `--gzip` : sortie `<nom>.anon.txt.gz`, compressée de façon déterministe (ni date ni nom de fichier dans l'en-tête).
Sortie `<nom>.anon.txt` en UTF-8, fins de ligne LF. Ne pas éditer à la main : relancer le script."""

from __future__ import annotations

import argparse
import csv
import gzip
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "combatlog"
MINE_FLAG = 0x1  # COMBATLOG_OBJECT_AFFILIATION_MINE (format du journal)
MINE_GUID = "Player-0000-00000000"
MINE_NAME = "Moi-Royaume"
DEATHS = frozenset({"UNIT_DIED", "PARTY_KILL"})
MAP_EVENTS = frozenset({"MAP_CHANGE", "ZONE_CHANGE"})


def fields(line: str) -> tuple[str, list[str]]:
    """(horodatage, champs CSV) d'une ligne du journal."""
    stamp, _, body = line.partition("  ")
    return stamp, next(csv.reader([body]))


def players(lines: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """(GUID -> GUID anonyme, nom -> nom anonyme) des joueurs, dans l'ordre de première apparition."""
    guids: dict[str, str] = {}
    names: dict[str, str] = {}
    n = pets = 0
    for line in lines[1:]:
        _, row = fields(line)
        for i in (1, 5):  # unités source et destination : GUID, nom, drapeaux, drapeaux de raid
            if len(row) < i + 3 or not row[i].startswith(("Player-", "Pet-")):
                continue
            guid, name, flags = row[i], row[i + 1], int(row[i + 2], 16)
            if guid.startswith("Pet-") and name not in names:
                pets += 1
                names[name] = f"Familier{pets}"
                continue
            if not guid.startswith("Player-") or guid in guids:
                continue
            if flags & MINE_FLAG:
                guids[guid], names[name] = MINE_GUID, MINE_NAME
            else:
                n += 1
                guids[guid], names[name] = f"Player-0000-{n:08d}", f"Joueur{n}-Royaume"
    return guids, names


def useful(text: str) -> str:
    """En-tête et événements utiles aux mesures (voir `--useful`), dans l'ordre du fichier."""
    from forever.pipeline.combatlog import _event, _split

    lines = text.splitlines()
    kept = [lines[0]]
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        time, row = _split(line)
        e = _event(number, time, row)
        units = [u for u in (e.source, e.dest) if u is not None]
        mine = any(u.is_mine and u.kind == "Player" for u in units)
        described = next((u for u in units if e.advanced is not None and u.guid == e.advanced.guid), None)
        damage = "_DAMAGE" in e.name and described is not None and described.kind == "Creature"
        death = e.name in DEATHS and e.dest is not None and e.dest.kind == "Creature"
        if mine or damage or death or e.name in MAP_EVENTS:
            kept.append(line)
    return "\n".join(kept) + "\n"


def anonymize(text: str) -> str:
    lines = text.splitlines()
    guids, names = players(lines)
    out = []
    for line in lines:
        for old, new in guids.items():
            line = line.replace(old, new)
        for old, new in names.items():
            line = line.replace(f'"{old}"', f'"{new}"')
        out.append(line)
    before = Counter(fields(x)[1][0] for x in lines)
    after = Counter(fields(x)[1][0] for x in out)
    if len(out) != len(lines) or before != after:
        raise SystemExit("anonymisation incohérente : lignes ou événements modifiés")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anonymise un journal de combat (fixture de test).")
    parser.add_argument("log", type=Path, help="journal WoWCombatLog-….txt du client")
    parser.add_argument("--out", type=Path, default=FIXTURES, help="dossier de sortie")
    parser.add_argument("--useful", action="store_true", help="ne garder que les événements utiles aux mesures")
    parser.add_argument("--gzip", action="store_true", help="compresser la sortie (.anon.txt.gz)")
    args = parser.parse_args(argv)
    text = args.log.read_text(encoding="utf-8")
    if not text.strip():
        print(f"Journal vide : {args.log}", file=sys.stderr)
        return 1
    if args.useful:
        text = useful(text)
    args.out.mkdir(parents=True, exist_ok=True)
    data = anonymize(text).encode("utf-8")
    dest = args.out / f"{args.log.stem}.anon.txt"
    if args.gzip:
        dest = dest.with_name(dest.name + ".gz")
        data = gzip.compress(data, compresslevel=9, mtime=0)
    dest.write_bytes(data)
    print(f"Fixture écrite : {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
