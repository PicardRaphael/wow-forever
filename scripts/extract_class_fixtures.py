"""Extrait hors ligne, des CSV du cache de `forever fetch`, la fixture des 9 classes (PV1, bloc B).

    uv run python scripts/extract_class_fixtures.py [--version 1.60.1.70124]

Écrit `tests/fixtures/wago/<version>/` (tables de `decode_rules.json` : `tables`, `class_tables` et leurs versions
localisées). Filtre (fermeture transitive) :
- les arbres de talents des 9 classes (`classes.<Classe>.skill_lines`) en entier : nœuds, entrées, définitions,
  points d'effet, courbes, arêtes ; plus un nœud leurre d'un autre arbre ;
- sorts : sorts des talents, rangs des sorts suivis du Mage (`spells`, `utility_spells`), sorts nommés dans
  `SAMPLE_SPELLS` (contrôles, défensifs, interruptions, dissipations, sorts de familier de chaque classe), sorts des
  lignes raciales (`RACIAL_LINES`), sorts d'utilisation des objets de `SAMPLE_ITEMS` ; puis sorts déclenchés
  (EffectTriggerSpell) et cités par les infobulles, jusqu'à stabilité ; leurres : un sort homonyme hors des lignes
  de classe (PNJ) par sort nommé ;
- tables petites recopiées en entier (`FULL_TABLES`) ; les autres réduites aux sorts ou objets retenus.
Lignes réécrites par le module csv (mêmes colonnes, même ordre), fins de ligne LF. Ne pas éditer la fixture à la
main : relancer le script."""

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
REF_RE = re.compile(r"\$\{?\$?(\d+)[a-zA-Z]")
FULL_TABLES = (
    "SkillLineXTraitTree",
    "SpellCastTimes",
    "SpellDuration",
    "ChrClasses",
    "SkillLine",
    "SpellRange",
    "SpellCategory",
    "SpellMechanic",
    "SpellDispelType",
    "ChrRaces",
    "CharBaseInfo",
    "SkillRaceClassInfo",
)
# Sorts nommés par classe (blocs B3 et D) : complétés au fil des blocs ; noms anglais du client.
SAMPLE_SPELLS: dict[str, tuple[str, ...]] = {}
# Lignes de compétence raciales (bloc B2) et objets (bloc B2 : bijoux PvP et leurre).
RACIAL_LINES: tuple[int, ...] = ()
SAMPLE_ITEMS: tuple[int, ...] = ()


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
    parser.add_argument("--version", default="1.60.1.70124")
    args = parser.parse_args()
    rules = json.loads((DATA_DIR / args.version / "decode_rules.json").read_text(encoding="utf-8"))
    src = wago_dir(default_cache_dir(), args.version)
    dst = FIXTURES / args.version
    names_all = [*rules["tables"], *rules["class_tables"]]
    t = {name: read(src / "enUS" / f"{name}.csv") for name in names_all}
    rows = {name: r for name, (_, r) in t.items()}

    class_lines = {str(i) for c in rules["classes"].values() for i in c["skill_lines"]}
    pet_lines = {str(i) for c in rules["classes"].values() for i in c.get("pet_skill_lines", [])}
    trees = {r["TraitTreeID"] for r in rows["SkillLineXTraitTree"] if r["SkillLineID"] in class_lines}
    nodes = {r["ID"] for r in rows["TraitNode"] if r["TraitTreeID"] in trees}
    other = sorted(
        (r for r in rows["TraitNode"] if r["TraitTreeID"] not in trees),
        key=lambda r: (int(r["TraitTreeID"]), int(r["ID"])),
    )
    nodes.add(other[0]["ID"])
    nxe = [r for r in rows["TraitNodeXTraitNodeEntry"] if r["TraitNodeID"] in nodes]
    entry_ids = {r["TraitNodeEntryID"] for r in nxe}
    entries = [r for r in rows["TraitNodeEntry"] if r["ID"] in entry_ids]
    def_ids = {r["TraitDefinitionID"] for r in entries}
    defs = [r for r in rows["TraitDefinition"] if r["ID"] in def_ids]
    points = [r for r in rows["TraitDefinitionEffectPoints"] if r["TraitDefinitionID"] in def_ids]
    curves = {r["CurveID"] for r in points}

    names = {r["ID"]: r["Name_lang"] for r in rows["SpellName"]}
    spells = {r["SpellID"] for r in defs}
    mage_lines = {str(v) for v in rules["skill_lines"].values()}
    followed = set(rules["spells"].values()) | set(rules.get("utility_spells", {}).get("spells", {}).values())
    spells |= {
        r["Spell"]
        for r in rows["SkillLineAbility"]
        if r["SkillLine"] in mage_lines and names.get(r["Spell"]) in followed
    }
    wanted = {n for group in SAMPLE_SPELLS.values() for n in group}
    lines = class_lines | pet_lines
    named = {
        r["Spell"] for r in rows["SkillLineAbility"] if r["SkillLine"] in lines and names.get(r["Spell"]) in wanted
    }
    spells |= named
    npc = []
    for name in sorted(wanted):
        homonyms = sorted((s for s, n in names.items() if n == name and s not in named), key=int)[:1]
        npc += homonyms
    spells |= set(npc)
    spells |= {r["Spell"] for r in rows["SkillLineAbility"] if int(r["SkillLine"]) in RACIAL_LINES}
    items = {str(i) for i in SAMPLE_ITEMS}
    item_links = [r for r in rows["ItemXItemEffect"] if r["ItemID"] in items]
    effect_ids = {r["ItemEffectID"] for r in item_links}
    item_effects = [r for r in rows["ItemEffect"] if r["ID"] in effect_ids]
    spells |= {r["SpellID"] for r in item_effects}

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

    def by(name: str, col: str, keep: set[str]) -> list[dict[str, str]]:
        return [r for r in rows[name] if r[col] in keep]

    out = {name: rows[name] for name in FULL_TABLES}
    out |= {
        "TraitNode": by("TraitNode", "ID", nodes),
        "TraitNodeXTraitNodeEntry": nxe,
        "TraitNodeEntry": entries,
        "TraitDefinition": defs,
        "TraitDefinitionEffectPoints": points,
        "TraitEdge": [r for r in rows["TraitEdge"] if r["LeftTraitNodeID"] in nodes or r["RightTraitNodeID"] in nodes],
        "CurvePoint": by("CurvePoint", "CurveID", curves),
        "SkillLineAbility": by("SkillLineAbility", "Spell", spells),
        "Spell": by("Spell", "ID", spells),
        "SpellName": by("SpellName", "ID", spells),
        "Item": by("Item", "ID", items),
        "ItemSparse": by("ItemSparse", "ID", items),
        "ItemEffect": item_effects,
        "ItemXItemEffect": item_links,
    }
    for name in names_all:
        if name not in out:
            out[name] = by(name, "SpellID", spells)
    for name in names_all:
        n = write(dst / "enUS" / f"{name}.csv", t[name][0], out[name])
        print(f"enUS/{name} : {n} lignes")
    localized: dict[str, list[str]] = {}
    for source in (rules.get("localized_tables", {}), rules.get("localized_class_tables", {})):
        for locale, tables in source.items():
            localized.setdefault(locale, []).extend(tables)
    for locale, tables in localized.items():
        for name in tables:
            header, loc_rows = read(src / locale / f"{name}.csv")
            keep = loc_rows if name in FULL_TABLES else [r for r in loc_rows if r["ID"] in spells]
            n = write(dst / locale / f"{name}.csv", header, keep)
            print(f"{locale}/{name} : {n} lignes")
    print(f"sorts : {len(spells)} ; leurres PNJ {sorted(npc, key=int)} ; objets {sorted(items, key=int)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
