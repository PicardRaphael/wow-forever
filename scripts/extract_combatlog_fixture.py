"""Anonymise hors ligne un journal de combat du client pour en faire une fixture de test (décision 8 du plan T04).

    uv run python scripts/extract_combatlog_fixture.py <WoWCombatLog-….txt> [--out tests/fixtures/combatlog/]

- Le joueur « à moi » (drapeau d'affiliation 0x1 sur une unité) devient `Moi-Royaume`, GUID `Player-0000-00000000`.
- Les autres joueurs deviennent `Joueur1-Royaume`, `Joueur2-Royaume`… et `Player-0000-00000001`… dans l'ordre de
  première apparition ; chaque GUID est remplacé sur toute la ligne (il réapparaît dans le bloc avancé).
- Créatures, objets, sorts et chiffres intacts ; nombre de lignes et d'événements conservés (contrôlé).
Sortie `<nom>.anon.txt` en UTF-8, fins de ligne LF. Ne pas éditer à la main : relancer le script."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "combatlog"
MINE_FLAG = 0x1  # COMBATLOG_OBJECT_AFFILIATION_MINE (format du journal)
MINE_GUID = "Player-0000-00000000"
MINE_NAME = "Moi-Royaume"


def fields(line: str) -> tuple[str, list[str]]:
    """(horodatage, champs CSV) d'une ligne du journal."""
    stamp, _, body = line.partition("  ")
    return stamp, next(csv.reader([body]))


def players(lines: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """(GUID -> GUID anonyme, nom -> nom anonyme) des joueurs, dans l'ordre de première apparition."""
    guids: dict[str, str] = {}
    names: dict[str, str] = {}
    n = 0
    for line in lines[1:]:
        _, row = fields(line)
        for i in (1, 5):  # unités source et destination : GUID, nom, drapeaux, drapeaux de raid
            if len(row) < i + 3 or not row[i].startswith("Player-"):
                continue
            guid, name, flags = row[i], row[i + 1], int(row[i + 2], 16)
            if guid in guids:
                continue
            if flags & MINE_FLAG:
                guids[guid], names[name] = MINE_GUID, MINE_NAME
            else:
                n += 1
                guids[guid], names[name] = f"Player-0000-{n:08d}", f"Joueur{n}-Royaume"
    return guids, names


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
    args = parser.parse_args(argv)
    text = args.log.read_text(encoding="utf-8")
    if not text.strip():
        print(f"Journal vide : {args.log}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / f"{args.log.stem}.anon.txt"
    dest.write_bytes(anonymize(text).encode("utf-8"))
    print(f"Fixture écrite : {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
