"""Contrôle : pas de chiffres de jeu dans le plugin (skills, agents, commandes, prompts produit) ni dans l'addon.
Signale les nombres suivis d'une unité de jeu (motif `GAME_NUMBER` de forever/hooks.py : dégâts, mana, %, s, min,
points, PV, DPS, XP, portée…)."""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.hooks import GAME_NUMBER

ZONES = [ROOT / "plugin", ROOT / "addon"]
# Résultats des passages de claude plugin eval : réponses du modèle et traces, non versionnés.
EXCLUDED = [ROOT / "plugin" / "evals" / "results"]
MOTIF = GAME_NUMBER  # même motif que le contrôle des réponses (forever/hooks.py)
AUTORISE = re.compile(r"<!--\s*chiffres-autorisés\s*-->")


def main() -> int:
    hits = []
    for zone in ZONES:
        if not zone.exists():
            continue
        for f in zone.rglob("*"):
            if any(f.is_relative_to(x) for x in EXCLUDED):
                continue
            if f.suffix not in {".md", ".json", ".yaml", ".yml", ".txt", ".lua", ".toc"}:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            if AUTORISE.search(text):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if MOTIF.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()[:100]}")
    for h in hits:
        print(f"  chiffre de jeu suspect : {h}")
    print(f"Contrôle des chiffres : {len(hits)} alerte(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
