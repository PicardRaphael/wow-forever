"""Contrôle : pas de chiffres de jeu dans le plugin (skills, agents, commandes, prompts produit).
Signale les nombres suivis d'une unité de jeu (dégâts, mana, %, s, secondes, points, PV, DPS)."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ZONES = [ROOT / "plugin"]
MOTIF = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:%|s\b|sec|secondes|mana|dégâts|degats|damage|points|pv|hp|dps)\b", re.IGNORECASE)
AUTORISE = re.compile(r"<!--\s*chiffres-autorisés\s*-->")


def main() -> int:
    hits = []
    for zone in ZONES:
        if not zone.exists():
            continue
        for f in zone.rglob("*"):
            if f.suffix not in {".md", ".json", ".yaml", ".yml", ".txt"}:
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
