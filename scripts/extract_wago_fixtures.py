"""Extrait hors ligne, des CSV du cache de `forever fetch`, les lignes utiles au décodage du Mage (fixtures de test).

    uv run python scripts/extract_wago_fixtures.py --version 1.60.1.70009

Filtre (fermeture transitive) :
- arbre de talents associé aux lignes de compétence de `decode_rules.json`, ses nœuds, entrées, définitions, points
  d'effet, courbes et arêtes ;
- sorts des talents, rangs des sorts suivis (toutes méthodes d'acquisition, pour garder les doublons écartés par le
  décodeur), sorts déclenchés (EffectTriggerSpell) et sorts cités par les infobulles ($<id>…), jusqu'à stabilité ;
- leurres : le premier nœud d'un autre arbre (avec sa définition et son sort) et des sorts homonymes des sorts
  suivis hors des lignes du Mage (PNJ), avec leurs lignes de SkillLineAbility ;
- tables de référence complètes quand elles sont petites (SpellCastTimes, SpellDuration, SkillLineXTraitTree).
Les lignes sont réécrites avec le module csv (mêmes colonnes, même ordre), fins de ligne LF."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import DATA_DIR, default_cache_dir
from forever.pipeline.fetch import wago_dir

FIXTURES = ROOT / "tests" / "fixtures" / "wago"
DECOY_NPC_PER_SPELL = 1
REF_RE = re.compile(r"\$\{?\$?(\d+)[a-zA-Z]")


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write(path: Path, header: list[str], rows: Iterable[dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True)
    parser.add_argument("--rules", help="decode_rules.json (défaut : version locale la plus récente qui en a un)")
    args = parser.parse_args()
    rules_path = Path(args.rules) if args.rules else max(DATA_DIR.glob("*/decode_rules.json"))
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    src = wago_dir(default_cache_dir(), args.version)
    dst = FIXTURES / args.version
    t: dict[str, tuple[list[str], list[dict[str, str]]]] = {
        name: read(src / "enUS" / f"{name}.csv") for name in rules["tables"]
    }
    rows = {name: r for name, (_, r) in t.items()}

    lines = {str(v) for v in rules["skill_lines"].values()}
    trees = {r["TraitTreeID"] for r in rows["SkillLineXTraitTree"] if r["SkillLineID"] in lines}
    nodes = {r["ID"] for r in rows["TraitNode"] if r["TraitTreeID"] in trees}
    other = sorted(
        (r for r in rows["TraitNode"] if r["TraitTreeID"] not in trees),
        key=lambda r: (int(r["TraitTreeID"]), int(r["ID"])),
    )
    decoy_node = other[0]["ID"]
    nodes.add(decoy_node)
    nxe = [r for r in rows["TraitNodeXTraitNodeEntry"] if r["TraitNodeID"] in nodes]
    entry_ids = {r["TraitNodeEntryID"] for r in nxe}
    entries = [r for r in rows["TraitNodeEntry"] if r["ID"] in entry_ids]
    def_ids = {r["TraitDefinitionID"] for r in entries}
    defs = [r for r in rows["TraitDefinition"] if r["ID"] in def_ids]
    points = [r for r in rows["TraitDefinitionEffectPoints"] if r["TraitDefinitionID"] in def_ids]
    curves = {r["CurveID"] for r in points}

    names = {r["ID"]: r["Name_lang"] for r in rows["SpellName"]}
    followed = set(rules["spells"].values())
    spells = {r["SpellID"] for r in defs}
    spells |= {
        r["Spell"] for r in rows["SkillLineAbility"] if r["SkillLine"] in lines and names.get(r["Spell"]) in followed
    }
    mage_ranks = set(spells)
    npc: list[str] = []
    for name in sorted(followed):
        homonyms = sorted((sid for sid, n in names.items() if n == name and sid not in mage_ranks), key=int)[
            :DECOY_NPC_PER_SPELL
        ]
        npc += homonyms
    spells |= set(npc)
    descriptions = {r["ID"]: r["Description_lang"] for r in rows["Spell"]}
    triggers: dict[str, set[str]] = {}
    for r in rows["SpellEffect"]:
        if r["EffectTriggerSpell"] != "0":
            triggers.setdefault(r["SpellID"], set()).add(r["EffectTriggerSpell"])
    frontier = set(spells)
    while frontier:
        found: set[str] = set()
        for sid in frontier:
            found |= triggers.get(sid, set())
            found |= set(REF_RE.findall(descriptions.get(sid, "")))
        frontier = {s for s in found if s in names} - spells
        spells |= frontier

    def by_spell(name: str, col: str = "SpellID") -> list[dict[str, str]]:
        return [r for r in rows[name] if r[col] in spells]

    out = {
        "SkillLineXTraitTree": rows["SkillLineXTraitTree"],
        "TraitNode": [r for r in rows["TraitNode"] if r["ID"] in nodes],
        "TraitNodeXTraitNodeEntry": nxe,
        "TraitNodeEntry": entries,
        "TraitDefinition": defs,
        "TraitDefinitionEffectPoints": points,
        "TraitEdge": [r for r in rows["TraitEdge"] if r["LeftTraitNodeID"] in nodes or r["RightTraitNodeID"] in nodes],
        "CurvePoint": [r for r in rows["CurvePoint"] if r["CurveID"] in curves],
        "SkillLineAbility": by_spell("SkillLineAbility", "Spell"),
        "Spell": by_spell("Spell", "ID"),
        "SpellName": by_spell("SpellName", "ID"),
        "SpellEffect": by_spell("SpellEffect"),
        "SpellLevels": by_spell("SpellLevels"),
        "SpellMisc": by_spell("SpellMisc"),
        "SpellCastTimes": rows["SpellCastTimes"],
        "SpellDuration": rows["SpellDuration"],
        "SpellPower": by_spell("SpellPower"),
        "SpellCooldowns": by_spell("SpellCooldowns"),
        "SpellAuraOptions": by_spell("SpellAuraOptions"),
    }
    for name in rules["tables"]:
        n = write(dst / "enUS" / f"{name}.csv", t[name][0], out[name])
        print(f"enUS/{name} : {n} lignes")
    for locale, tables in rules.get("localized_tables", {}).items():
        for name in tables:
            header, loc_rows = read(src / locale / f"{name}.csv")
            key = "ID" if "ID" in header else "SpellID"
            n = write(dst / locale / f"{name}.csv", header, (r for r in loc_rows if r[key] in spells))
            print(f"{locale}/{name} : {n} lignes")
    print(f"sorts : {len(spells)} (dont leurres PNJ {sorted(npc, key=int)}) ; nœud leurre {decoy_node}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
