"""Extrait hors ligne les fixtures des bonus d'XP de T04f (tables du client, cache de `forever fetch`).

    uv run python scripts/extract_xp_bonus_fixtures.py [--version 1.60.1.70338]

Écrit `tests/fixtures/wago/xp_bonuses/enUS/<Table>.csv` : en-tête complet de chaque table et seulement les lignes
des sorts, objets, traits et conditions de `SPELLS`, `ITEMS` et `CONDITIONS` (et celles qu'elles citent : durées,
cumuls, effets d'objet, courbes, nœuds). Les cellules sont recopiées telles quelles ; seules les lignes sont filtrées.
Aucun chiffre de jeu ici : les identifiants désignent des lignes du client."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_cache_dir
from forever.pipeline.fetch import table_path

OUT = ROOT / "tests" / "fixtures" / "wago" / "xp_bonuses" / "enUS"
# Auras d'XP du client (codes 200, 291, 386, 656, 447), chaîne du sac de couchage, éléments de camp, perks Legacy
# voisins (Gourmand, Field Guide), nourritures nutritives et ordinaires (leurre), sort sans rapport (leurre).
SPELLS = {
    335924, 362859, 429959, 430496, 436412, 1225478, 1243969, 1292997, 1293736,
    429961, 429960,
    1307230, 1229451, 1308027, 1229741, 1307227, 1307252, 1307237,
    1225499, 1225479,
    1248377, 1248378, 1249920, 434, 433,
    133,
}  # fmt: skip
ITEMS = {211527, 273049, 3663, 5474, 2680, 249865, 414}
CONDITIONS = {142418}


def _rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader), list(reader)


def _write(name: str, header: list[str], rows: list[list[str]]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.csv").write_bytes(buf.getvalue().encode("utf-8"))
    print(f"{name} : {len(rows)} ligne(s)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default="1.60.1.70338")
    args = parser.parse_args(argv)
    cache = default_cache_dir()
    tables: dict[str, tuple[list[str], list[list[str]]]] = {}

    def load(name: str) -> tuple[list[str], list[list[str]]]:
        if name not in tables:
            tables[name] = _rows(table_path(cache, args.version, "enUS", name))
        return tables[name]

    def pick(name: str, column: str, keep: set[int]) -> list[list[str]]:
        header, rows = load(name)
        i = header.index(column)
        return [r for r in rows if r[i].lstrip("-").isdigit() and int(r[i]) in keep]

    def col(name: str, rows: list[list[str]], column: str) -> set[int]:
        i = load(name)[0].index(column)
        return {int(r[i]) for r in rows}

    spells = set(SPELLS)
    # effets d'objet des objets retenus, et leurs sorts
    ixe = pick("ItemXItemEffect", "ItemID", ITEMS)
    ie = pick("ItemEffect", "ID", col("ItemXItemEffect", ixe, "ItemEffectID"))
    spells |= col("ItemEffect", ie, "SpellID")
    # sorts déclenchés par les sorts retenus (buffs Well Fed des nourritures)
    effects = pick("SpellEffect", "SpellID", spells)
    spells |= col("SpellEffect", effects, "EffectTriggerSpell") - {0}
    effects = pick("SpellEffect", "SpellID", spells)
    misc = pick("SpellMisc", "SpellID", spells)
    traits = pick("TraitDefinition", "SpellID", spells)
    points = pick("TraitDefinitionEffectPoints", "TraitDefinitionID", col("TraitDefinition", traits, "ID"))
    entries = pick("TraitNodeEntry", "TraitDefinitionID", col("TraitDefinition", traits, "ID"))
    links = pick("TraitNodeXTraitNodeEntry", "TraitNodeEntryID", col("TraitNodeEntry", entries, "ID"))
    out = {
        "SpellName": pick("SpellName", "ID", spells),
        "Spell": pick("Spell", "ID", spells),
        "SpellEffect": effects,
        "SpellMisc": misc,
        "SpellDuration": pick("SpellDuration", "ID", col("SpellMisc", misc, "DurationIndex")),
        "SpellAuraOptions": pick("SpellAuraOptions", "SpellID", spells),
        "ItemSparse": pick("ItemSparse", "ID", ITEMS),
        "ItemEffect": ie,
        "ItemXItemEffect": ixe,
        "TraitDefinition": traits,
        "TraitDefinitionEffectPoints": points,
        "CurvePoint": pick("CurvePoint", "CurveID", col("TraitDefinitionEffectPoints", points, "CurveID")),
        "TraitNodeEntry": entries,
        "TraitNodeXTraitNodeEntry": links,
        "TraitNode": pick("TraitNode", "ID", col("TraitNodeXTraitNodeEntry", links, "TraitNodeID")),
        "PlayerCondition": pick("PlayerCondition", "ID", CONDITIONS),
    }
    for name, rows in out.items():
        _write(name, load(name)[0], rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
