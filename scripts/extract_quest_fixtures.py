"""Extrait hors ligne les fixtures des quêtes de T04d (client et addons installés), sans données personnelles.

    uv run python scripts/extract_quest_fixtures.py questcache [--wow <dossier du client>]
    uv run python scripts/extract_quest_fixtures.py questxp [--version 1.60.1.70338]

`questcache` : en-tête de `Cache/WDB/enUS/questcache.wdb` et les enregistrements de `QUESTCACHE_IDS` recopiés octet
pour octet (texte des quêtes compris, c'est celui du client), puis le couple de fin (0, 0) ; écrit
`tests/fixtures/client/questcache_sample.wdb`.

`questxp` : table `QuestXP` du cache de `forever fetch` recopiée octet pour octet dans
`tests/fixtures/client/QuestXP.csv`.

`addons` : extraits des addons de quêtes installés (`Interface/AddOns`) dans `tests/fixtures/addons/quests/Interface/AddOns/`,
chemins conservés : en-têtes `## ` des `.toc`, lignes des quêtes de `ADDON_QUESTS` (une ligne par entrée, recopiée
telle quelle) et de leurs PNJ, blocs de donjon de Ragefire Chasm et de The Hall of Thanes ; plus un extrait de
`QuestieForeverDB` (SavedVariable de Questie, quêtes apprises en jeu) sans horodatage, dans
`tests/fixtures/addons/quests/WTF/Account/COMPTE/SavedVariables/Questie.lua`."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_cache_dir, default_wow_dir
from forever.pipeline.fetch import table_path
from forever.pipeline.lua_table import parse_lua_value, parse_lua_value_at
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


ADDONS_OUT = ROOT / "tests" / "fixtures" / "addons" / "quests"
# Quêtes du plan T04d (tests attendus) : 7 et 783 (prérequis), 15 (suite de 7), 92432 et 92434 (nouvelles), 825
# (vue par le client), Ragefire Chasm (5761, 5723, 5725, 5722, 5724, 5728), The Hall of Thanes (96403, 96395).
ADDON_QUESTS = (7, 15, 783, 92432, 92434, 825, 5761, 5723, 5725, 5722, 5724, 5728, 96403, 96395)
ELWYNN_AREA, ELWYNN_MAP = 12, 1429  # zone couverte par Completo : une quête Classic absente y est cherchée
QUESTIE = Path("Questie")
COMPLETO = Path("NaowhForever_Discovery/QuestList/Data/Quests.lua")
JOURNEYS = Path("NaowhForever_Journeys/Data/QuestSpots.lua")
NAOWH_DJ = Path("NaowhForever_DungeonJournal/Data/Quests.lua")
GUIDE = Path("ForeverGuide/DungeonData.lua")
FDJ_REWARDS = Path("ForeverDungeonJournal/Data/QuestRewards.lua")
FDJ_DUNGEONS = Path("ForeverDungeonJournal/Data/Dungeons.lua")
GEARQUEST = Path("GearQuestForever_MAGE/Data.Mage.Early.1to9.generated.lua")
GEARQUEST_NAMES = ("From The Wreckage....", "Sarkoth")  # un nom unique (825), un nom ambigu (790 et 804, Durotar)
GEARQUEST_AMBIGUOUS = (790, 804)
TOCS = (
    "Questie/Questie_Camelot.toc",
    "NaowhForever_Discovery/NaowhForever_Discovery.toc",
    "NaowhForever_Journeys/NaowhForever_Journeys.toc",
    "NaowhForever_DungeonJournal/NaowhForever_DungeonJournal.toc",
    "ForeverGuide/ForeverGuide.toc",
    "ForeverDungeonJournal/ForeverDungeonJournal.toc",
    "GearQuestForever/GearQuestForever.toc",
    "GearQuestForever_MAGE/GearQuestForever_MAGE.toc",
)
LINE_ENTRY = re.compile(r"^\s*\[(\d+)\]\s*=")


def _write(rel: Path | str, text: str) -> None:
    target = ADDONS_OUT / "Interface" / "AddOns" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))


def _lines(text: str, ids: set[int]) -> list[str]:
    return [line for line in text.splitlines() if (m := LINE_ENTRY.match(line)) and int(m[1]) in ids]


def _section(text: str, start: str) -> str:
    """Section `start = {` … `}` (fin : première ligne `}` en colonne 0)."""
    i = text.index(start)
    j = text.index("\n}", i)
    return text[i : j + 2]


def _questie(addons: Path, extra: set[int]) -> tuple[set[int], int]:
    root = addons / QUESTIE
    qtext = (root / "Database/Classic/classicQuestDB.lua").read_text(encoding="utf-8")
    keys = qtext[: qtext.index("QuestieDB.questData")]
    completo = (addons / COMPLETO).read_text(encoding="utf-8")
    elwynn = re.search(rf"map = {ELWYNN_MAP}, .*?quests = {{([^}}]*)}}", completo)
    assert elwynn is not None
    covered = {int(x) for x in elwynn[1].split(",")}
    listed = {int(x) for x in re.findall(r"^    \[(\d+)\] = ", _section(completo, "D.Quests = {"), re.MULTILINE)}
    absent = None
    for line in qtext.splitlines():
        m = LINE_ENTRY.match(line)
        if not m or int(m[1]) in covered or int(m[1]) in listed:
            continue
        row = parse_lua_value(line.split(" = ", 1)[1].rstrip().rstrip(","))
        fields = row if isinstance(row, dict) else dict(enumerate(row, start=1)) if isinstance(row, list) else {}
        if fields.get(17) == ELWYNN_AREA:
            absent = int(m[1])
            break
    assert absent is not None, "aucune quête Classic d'Elwynn absente de Completo"
    ids = set(ADDON_QUESTS) | extra | {absent}
    quests = _lines(qtext, ids)
    _write(
        QUESTIE / "Database/Classic/classicQuestDB.lua",
        f"{keys}QuestieDB.questData = [[return {{\n" + "\n".join(quests) + "\n}]]\n",
    )
    npcs: set[int] = set()
    for line in quests:
        npcs |= {int(x) for x in re.findall(r"\{\{(\d+)", line.split("{", 1)[1])[:2]}
        obj = re.search(r"\{\{\{(\d+)\},\{(\d+)\}\}\}", line)
        if obj:
            npcs |= {int(obj[1]), int(obj[2])}
    ntext = (root / "Database/Classic/classicNpcDB.lua").read_text(encoding="utf-8")
    nkeys = ntext[: ntext.index("QuestieDB.npcData")]
    _write(
        QUESTIE / "Database/Classic/classicNpcDB.lua",
        f"{nkeys}QuestieDB.npcData = [[return {{\n" + "\n".join(_lines(ntext, npcs)) + "\n}]]\n",
    )
    xp = (root / "Database/QuestXP/DB/xpDB-classic.lua").read_text(encoding="utf-8")
    head = xp[: xp.index("QuestXP.db = {")]
    _write(
        QUESTIE / "Database/QuestXP/DB/xpDB-classic.lua",
        f"{head}QuestXP.db = {{\n" + "\n".join(_lines(xp, ids)) + "\n}\n",
    )
    fixes = (root / "Database/Corrections/classicQuestFixes.lua").read_text(encoding="utf-8")
    blocks = re.findall(r"^        \[(\d+)\] = \{.*?^        \},\n", fixes, re.MULTILINE | re.DOTALL)
    kept = [
        m[0]
        for m in re.finditer(r"^        \[(\d+)\] = \{.*?^        \},\n", fixes, re.MULTILINE | re.DOTALL)
        if int(m[1]) in ids
    ]
    assert blocks
    _write(
        QUESTIE / "Database/Corrections/classicQuestFixes.lua",
        "function QuestieQuestFixes:Load()\n    local questKeys = QuestieDB.questKeys\n\n    return {\n"
        + "".join(kept)
        + "    }\nend\n",
    )
    zones = (root / "Database/Zones/data/areaIdToUiMapId.lua").read_text(encoding="utf-8")
    _write(QUESTIE / "Database/Zones/data/areaIdToUiMapId.lua", zones)
    return ids, absent


def extract_addons(wow: Path) -> Path:
    addons = wow / "Interface" / "AddOns"
    for toc in TOCS:
        text = (addons / toc).read_text(encoding="utf-8")
        header = [line for line in text.splitlines() if line.startswith("## ") and "Notes" not in line]
        _write(toc, "\n".join(header) + "\n")
    ids, absent = _questie(addons, set(GEARQUEST_AMBIGUOUS))
    completo = (addons / COMPLETO).read_text(encoding="utf-8")
    zones = [line for line in _section(completo, "D.Zones = {").splitlines() if f"map = {ELWYNN_MAP}," in line]
    zones += [line for line in _section(completo, "D.Zones = {").splitlines() if "map = 1416," in line]
    zones += [line for line in _section(completo, "D.Zones = {").splitlines() if "map = 1411," in line]
    chains = [line for line in _section(completo, "D.Chains = {").splitlines() if "{ { 783 }" in line]
    _write(
        COMPLETO,
        "local D = {}\n_G.NaowhForever.CompletoQuestData = D\n\nD.Zones = {\n"
        + "\n".join(zones)
        + "\n}\n\nD.Quests = {\n"
        + "\n".join(_lines(_section(completo, "D.Quests = {"), ids))
        + "\n}\n\nD.Repeatable = {\n}\n\nD.Requires = {\n"
        + "\n".join(_lines(_section(completo, "D.Requires = {"), ids))
        + "\n}\n\nD.Chains = {\n"
        + "\n".join(chains)
        + "\n}\n",
    )
    spots = (addons / JOURNEYS).read_text(encoding="utf-8")
    _write(
        JOURNEYS,
        "local ns = _G.NaowhForever\n\nns.JourneyQuestSpots = {\n" + "\n".join(_lines(spots, ids)) + "\n}\n",
    )
    dj = (addons / NAOWH_DJ).read_text(encoding="utf-8")
    blocks = re.findall(
        r"^    \{ name = \"(?:Ragefire Chasm|The Hall of Thanes)\".*?^    \} \},\n", dj, re.MULTILINE | re.DOTALL
    )
    _write(NAOWH_DJ, "local J = _G.NaowhForever.Journal\n\nJ.QuestData = {\n" + "".join(blocks) + "}\n")
    guide = (addons / GUIDE).read_text(encoding="utf-8")
    dungeons = [
        line
        for line in _section(guide, "ns.DUNGEONS = {").splitlines()
        if 'key="rfc"' in line or 'key="thanes"' in line
    ]
    dq = _lines(_section(guide, "ns.DQ = {"), ids)
    npc_ids: set[int] = set()
    for line in dq:
        for key in ("s", "f"):
            m = re.search(rf"[,{{]{key}={{([\d,]+)}}", line)
            if m:
                npc_ids |= {int(x) for x in m[1].split(",")}
    _write(
        GUIDE,
        "local _, ns = ...\n\nns.DUNGEONS = {\n"
        + "\n".join(dungeons)
        + "\n}\nns.DQ = {\n"
        + "\n".join(dq)
        + "\n}\nns.DNPC = {\n"
        + "\n".join(_lines(_section(guide, "ns.DNPC = {"), npc_ids))
        + "\n}\n",
    )
    rewards = (addons / FDJ_REWARDS).read_text(encoding="utf-8")
    fallback = _lines(_section(rewards, "FDJ.FOREVER_QUEST_XP_FALLBACK = {"), ids)
    _write(
        FDJ_REWARDS,
        "local ADDON_NAME, FDJ = ...\n\nFDJ.FOREVER_QUEST_XP_FALLBACK = {\n" + "\n".join(fallback) + "\n}\n",
    )
    fdj = (addons / FDJ_DUNGEONS).read_text(encoding="utf-8")
    start = fdj.index('    ["Hall of Thanes"] = {')
    end = fdj.index("\n    },\n", start) + len("\n    },\n")
    _write(
        FDJ_DUNGEONS,
        "local ADDON_NAME, FDJ = ...\nlocal ALBA_FAIRMOON_LOCATION = FDJ.Constants.ALBA_FAIRMOON_LOCATION\n\nFDJ.DB = {\n"
        + fdj[start:end]
        + "}\n",
    )
    items: list[str] = []
    for name in GEARQUEST_NAMES:
        for path in sorted((addons / GEARQUEST.parent).glob("*.lua")):
            found = [line for line in path.read_text(encoding="utf-8").splitlines() if f'questName="{name}"' in line]
            if found:
                items.append(found[0])
                break
    assert len(items) == len(GEARQUEST_NAMES), items
    _write(GEARQUEST, "GQ.Data.mageEarly1to9Facts = {\n" + "\n".join(items) + "\n}\n")
    sv = wow / "WTF" / "Account"
    path = next(sv.glob("*/SavedVariables/Questie.lua"))
    text = path.read_bytes().decode("latin-1")
    i = text.index("QuestieForeverDB = {")
    db, _ = parse_lua_value_at(text, i + len("QuestieForeverDB = "))
    assert isinstance(db, dict)
    entries = []
    for quest in (96607, 886):
        row = db["quests"][quest]
        body = "".join(
            f'["{k}"] = ' + (f'"{row[k]}"' if isinstance(row[k], str) else str(row[k])) + ",\n"
            for k in ("questId", "title", "level", "mapID")
            if k in row
        )
        entries.append(f"[{quest}] = {{\n{body}}},\n")
    target = ADDONS_OUT / "WTF" / "Account" / "COMPTE" / "SavedVariables" / "Questie.lua"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(
        ('QuestieForeverDB = {\n["version"] = 6,\n["quests"] = {\n' + "".join(entries) + "},\n}\n").encode("utf-8")
    )
    print(f"quête Classic d'Elwynn absente de Completo : {absent}")
    return ADDONS_OUT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="what", required=True)
    qc = sub.add_parser("questcache")
    qc.add_argument("--wow", type=Path, default=None)
    qx = sub.add_parser("questxp")
    qx.add_argument("--version", default="1.60.1.70338")
    ad = sub.add_parser("addons")
    ad.add_argument("--wow", type=Path, default=None)
    args = parser.parse_args()
    if args.what == "questcache":
        print(extract_questcache(args.wow or default_wow_dir()))
    elif args.what == "addons":
        print(extract_addons(args.wow or default_wow_dir()))
    else:
        print(extract_questxp(args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
