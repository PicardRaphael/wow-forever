"""Extrait hors ligne, de l'addon Questie installé, une fixture minimale pour les tests (décision 3 du plan T04).

    uv run python scripts/extract_questie_fixture.py [--addon <dossier Questie>]
    uv run python scripts/extract_questie_fixture.py --journey <SavedVariables/Questie.lua> --guid <GUID du Mage>

Garde : les lignes `## ` du `.toc` Camelot (version, titre, interface), l'en-tête `npcKeys` et quelques PNJ de
`classicNpcDB.lua` (PNJ mesurés dans le journal de la fixture et leurres de rang élite ou rare), quelques entrées de
`xpDB-classic.lua` (commentaires compris). Jamais la base complète : Questie reste lu sur le disque de l'utilisateur.

`--journey` (décision 3 du plan T04b) : extrait du carnet (`journey`) de la SavedVariable de Questie, pour le
personnage `--guid` seulement : ses événements `Level` (horodatage, nouveau niveau), répartis comme dans le fichier
entre ses blocs `char` (Questie peut en écrire plusieurs pour un même GUID, dont un « Unknown »), plus le premier
événement de quête de chaque bloc (que le lecteur doit ignorer). Nom, royaume et GUID anonymisés (`Moi`, `Royaume`,
`Player-0000-00000000`, comme les journaux de combat) ; tout le reste de la SavedVariable est omis."""

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
MINE_GUID = "Player-0000-00000000"
JOURNEY_OUT = ROOT / "tests" / "fixtures" / "questie" / "journey" / "Questie.lua"
# Format de la SavedVariable (sans indentation) : clé de personnage « Nom - Royaume » en début de ligne.
CHAR_KEY = re.compile(r'^\["([^"\n]+) - ([^"\n]+)"\] = \{$', re.MULTILINE)
EVENT = re.compile(r"\{\n((?:\[\"\w+\"\] = [^\n{}]+,\n)+)\}")
FIELD = re.compile(r'\["(\w+)"\] = "?([^"\n]*?)"?,\n')


def entries(text: str, ids: tuple[int, ...]) -> list[str]:
    wanted = {str(i) for i in ids}
    return [line for line in text.splitlines() if (m := re.match(r"\s*\[(\d+)\] = ", line)) and m[1] in wanted]


def _event(fields: dict[str, str]) -> str:
    body = "".join(f'["{k}"] = {v if v.isdigit() else chr(34) + v + chr(34)},\n' for k, v in fields.items())
    return "{\n" + body + "},"


def journey(sv: Path, guid: str) -> str:
    """Extrait anonymisé du carnet du personnage `guid` (voir `--journey`)."""
    text = sv.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
    starts = list(CHAR_KEY.finditer(text))
    blocks = []
    for i, m in enumerate(starts):
        body = text[m.end() : starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        if f'["guid"] = "{guid}"' not in body:
            continue
        events = [dict(FIELD.findall(e[1] + "\n")) for e in EVENT.finditer(body)]
        quest = next((e for e in events if e.get("Event") == "Quest"), None)
        kept = ([quest] if quest else []) + [e for e in events if e.get("Event") == "Level"]
        name = "Unknown" if m[1] == "Unknown" else "Moi"
        blocks.append(
            f'["{name} - Royaume"] = {{\n["journey"] = {{\n'
            + "\n".join(_event(e) for e in kept)
            + f'\n}},\n["guid"] = "{MINE_GUID}",\n}},'
        )
    if not blocks:
        raise SystemExit(f"GUID {guid} absent du carnet de {sv}")
    return 'QuestieConfig = {\n["char"] = {\n' + "\n".join(blocks) + "\n},\n}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extrait une fixture minimale de Questie.")
    parser.add_argument("--addon", type=Path, default=default_wow_dir() / "Interface" / "AddOns" / "Questie")
    parser.add_argument("--journey", type=Path, help="SavedVariables/Questie.lua (extrait du carnet)")
    parser.add_argument("--guid", help="GUID du personnage dont on extrait le carnet")
    args = parser.parse_args(argv)
    if args.journey:
        if not args.guid:
            raise SystemExit("--journey exige --guid")
        JOURNEY_OUT.parent.mkdir(parents=True, exist_ok=True)
        JOURNEY_OUT.write_bytes(journey(args.journey, args.guid).encode("utf-8"))
        print(f"Fixture écrite : {JOURNEY_OUT}")
        return 0
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
