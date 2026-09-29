"""Empreinte des fichiers du plugin (T06b, décision D8) : toute modification de `plugin/` doit s'accompagner d'une
nouvelle version dans `plugin/.claude-plugin/plugin.json` (sans quoi `claude plugin update` ne recopie rien).

    uv run python scripts/plugin_fingerprint.py          # réécrit fingerprint.json (version et empreinte)
    uv run python scripts/plugin_fingerprint.py --check  # code 1 si l'empreinte n'est plus à jour

Empreinte : sha256 des lignes « chemin relatif, sha256 du contenu » triées ; fins de ligne CRLF ramenées à LF (même
empreinte sous Windows et Linux) ; `evals/results/` (résultats non versionnés) et `fingerprint.json` exclus."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
FINGERPRINT = Path(".claude-plugin") / "fingerprint.json"
MANIFEST = Path(".claude-plugin") / "plugin.json"
EXCLUDED_DIRS = (("evals", "results"),)
IGNORED_NAMES = ("__pycache__",)


def files(plugin: Path) -> list[Path]:
    """Fichiers couverts par l'empreinte, relatifs à `plugin`, triés."""
    out = []
    for p in sorted(plugin.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(plugin)
        if rel == FINGERPRINT or any(rel.parts[: len(d)] == d for d in EXCLUDED_DIRS):
            continue
        if any(part in IGNORED_NAMES for part in rel.parts):
            continue
        out.append(rel)
    return out


def compute(plugin: Path) -> str:
    """sha256 hexadécimal des fichiers du plugin (contenus à fins de ligne LF)."""
    lines = []
    for rel in files(plugin):
        content = (plugin / rel).read_bytes().replace(b"\r\n", b"\n")
        lines.append(f"{rel.as_posix()} {hashlib.sha256(content).hexdigest()}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def main(argv: list[str]) -> int:
    version = json.loads((PLUGIN / MANIFEST).read_text(encoding="utf-8"))["version"]
    doc = {"version": version, "sha256": compute(PLUGIN)}
    path = PLUGIN / FINGERPRINT
    if "--check" in argv:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        if stored != doc:
            print("Empreinte du plugin périmée : relever la version de plugin.json puis relancer ce script.")
            return 1
        print(f"Empreinte du plugin à jour (version {version}).")
        return 0
    path.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    print(f"Écrit : {path} (version {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
