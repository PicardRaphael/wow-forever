"""Extrait hors ligne, de l'addon Questie installé, une fixture minimale pour les tests (décision 3 du plan T04).

    uv run python scripts/extract_questie_fixture.py [--addon <dossier Questie>]

Garde : les lignes `## ` du `.toc` Camelot (version, titre, interface), l'en-tête `npcKeys` et quelques PNJ de
`classicNpcDB.lua` (PNJ mesurés dans le journal de la fixture et leurres de rang élite ou rare), quelques entrées de
`xpDB-classic.lua` (commentaires compris). Jamais la base complète : Questie reste lu sur le disque de l'utilisateur."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_wow_dir

NPCS = (3099, 5951, 3111, 1531, 5945)  # mesurés dans le journal (3) ; leurres : 1531 rare (rang 4), 5945 élite (rang 1)
QUESTS = (787, 788, 789)
NPC_DB = Path("Database/Classic/classicNpcDB.lua")
XP_DB = Path("Database/QuestXP/DB/xpDB-classic.lua")
TOC = "Questie_Camelot.toc"


def entries(text: str, ids: tuple[int, ...]) -> list[str]:
    wanted = {str(i) for i in ids}
    return [line for line in text.splitlines() if (m := re.match(r"\s*\[(\d+)\] = ", line)) and m[1] in wanted]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extrait une fixture minimale de Questie.")
    parser.add_argument("--addon", type=Path, default=default_wow_dir() / "Interface" / "AddOns" / "Questie")
    args = parser.parse_args(argv)
    toc = (args.addon / TOC).read_text(encoding="utf-8")
    version = re.search(r"^## Version: (\S+)", toc, re.MULTILINE)
    if version is None:
        raise SystemExit(f"{TOC} sans ligne ## Version")
    out = ROOT / "tests" / "fixtures" / "questie" / version[1]
    (out / NPC_DB).parent.mkdir(parents=True, exist_ok=True)
    (out / XP_DB).parent.mkdir(parents=True, exist_ok=True)
    header = [line for line in toc.splitlines() if line.startswith("## ") and not line.startswith("## Notes-")]
    (out / TOC).write_bytes(("\n".join(header) + "\n").encode("utf-8"))

    npc = (args.addon / NPC_DB).read_text(encoding="utf-8")
    keys = npc[: npc.index("QuestieDB.npcData")]
    body = "\n".join(entries(npc, NPCS))
    (out / NPC_DB).write_bytes(f"{keys}QuestieDB.npcData = [[return {{\n{body}\n}}]]\n".encode())

    xp = (args.addon / XP_DB).read_text(encoding="utf-8")
    head = xp[: xp.index("QuestXP.db = {")]
    lines = "\n".join(entries(xp, QUESTS))
    (out / XP_DB).write_bytes(f"{head}QuestXP.db = {{\n{lines}\n}}\n".encode())
    print(f"Fixture écrite : {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
