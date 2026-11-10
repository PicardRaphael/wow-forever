"""Tier list à la demande (demande du 2026-11-10 : « tout doit être calculable à la demande ») : toutes les
spécialisations de dégâts d'une faction classées par contexte. Aucun calcul de jeu ici : chaque chiffre vient de
wowsims par les calculs déjà là.

- `raid` : niveau 60, mêmes buffs pour tous, consommables de chacun, équipement GearQuest du 60
  (`compare_presets`) ; classé au DPS ;
- `donjon` : par tranche, buffs de groupe, `DUNGEON_TARGETS` cibles (`run_from_sources`) ; classé au DPS ;
- `leveling` : par tranche, seul, repos compris (objectif `leveling`) ; classé à l'XP par heure, DPS affiché.

Une race par classe : la première race jouable de la faction dans `races.json` (ou celle donnée). Gardée dans le
cache par version des données et commit de wowsims ; relue si elle existe."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError

FOLDER = "tierlist"
CONTEXTS = ("leveling", "donjon", "raid")
FACTIONS = ("horde", "alliance")
DUNGEON_TARGETS = 3  # cibles d'un paquet de donjon (réglage de l'outil, dit dans la provenance)
RAID_LEVEL = 60


def faction_races(deps: Deps, faction: str, overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Classe -> race (nom du client) : la première race jouable de la faction dans `races.json`, sauf `overrides`."""
    from forever.store import load_version

    if faction.lower() not in FACTIONS:
        raise InvalidArgumentError(f"Faction inconnue : « {faction} ».", "choisir " + ", ".join(FACTIONS))
    races = load_version(deps).read_json("races.json")["races"]
    out: dict[str, str] = {}
    for name, race in races.items():
        if str(race.get("faction", "")).lower() == faction.lower():
            for cls in race.get("classes", []):
                out.setdefault(str(cls), name)
    return {**out, **(overrides or {})}


def _version(deps: Deps) -> tuple[str, str]:
    from forever.sims.analysis import _version as analysis_version

    return analysis_version(deps)


def tier_list_path(deps: Deps, context: str, faction: str) -> Path:
    version, sims = _version(deps)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{context}-{faction}".lower())
    return deps.cache_dir / FOLDER / version / sims / f"{slug}.json"


def read_tier_list(deps: Deps, context: str, faction: str) -> dict[str, Any] | None:
    """Tier list gardée (version courante des données et de wowsims) ; None si absente."""
    path = tier_list_path(deps, context, faction)
    return dict(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None


def _dps_presets(deps: Deps) -> list[str]:
    from forever.sims.analysis import dps_presets

    return [key for key, _ in dps_presets(deps)]


def _default_brackets(deps: Deps) -> Callable[..., dict[str, Any]]:
    from forever.sims.brackets import run_from_sources

    def run(**kw: Any) -> dict[str, Any]:
        return run_from_sources(deps, **kw)

    return run


def _default_compare(deps: Deps) -> Callable[..., tuple[list[dict[str, Any]], list[str]]]:
    from forever.pipeline.wowsims_build import wowsims_dir
    from forever.sims import brackets as br
    from forever.sims import wowsims

    def run(cases: Sequence[tuple[str, str]], **kw: Any) -> tuple[list[dict[str, Any]], list[str]]:
        presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
        by_key = {p.key: p for p in presets}
        pairs = [(by_key[key], wowsims.race_enum(race)) for key, race in cases]
        notes: list[str] = []
        equipment: dict[str, dict[str, Any]] = {}
        for (preset, _), (_, race) in zip(pairs, cases, strict=True):
            equipment[preset.key], note = br.gearquest_equipment(deps, preset, race, RAID_LEVEL)
            notes.append(note)
        items, _, items_note = br.extra_items(deps.cache_dir)
        notes += [items_note] if items_note else []
        rows, _ = wowsims.compare_presets(deps.cache_dir, pairs, wowsims.reference_encounter(presets),
                                          consumables="own", equipment=equipment, items=items,
                                          iterations=kw.get("iterations") or wowsims.DEFAULT_ITERATIONS)  # fmt: skip
        return rows, notes

    return run


def _class(preset: str) -> str:
    return preset.split("/")[0].capitalize()


def tier_list(
    deps: Deps,
    *,
    context: str,
    faction: str,
    brackets: str | None = None,
    races: Mapping[str, str] | None = None,
    presets: Sequence[str] | None = None,
    iterations: int | None = None,
    run_brackets: Callable[..., dict[str, Any]] | None = None,
    run_compare: Callable[..., tuple[list[dict[str, Any]], list[str]]] | None = None,
) -> dict[str, Any]:
    """Tier list d'un contexte et d'une faction (voir le module) ; relue si elle existe déjà."""
    from forever.provenance import local_provenance

    if context not in CONTEXTS:
        raise InvalidArgumentError(f"Contexte inconnu : « {context} ».", "choisir " + ", ".join(CONTEXTS))
    chosen = faction_races(deps, faction, races)
    kept = read_tier_list(deps, context, faction)
    if kept is not None and brackets is None and not races:
        return kept
    keys = [k for k in (presets if presets is not None else _dps_presets(deps)) if _class(k) in chosen]
    cases = [(k, chosen[_class(k)]) for k in keys]
    listed = ", ".join(f"{c} {r}" for c, r in sorted({_class(k): r for k, r in cases}.items()))
    notes = [f"races : {listed} (première race jouable de la faction dans races.json, sauf race donnée)"]
    sections: list[dict[str, Any]] = []
    if context == "raid":
        rows, extra = (run_compare or _default_compare(deps))(cases, iterations=iterations)
        raid_note = (
            "raid : niveau 60, mêmes buffs et affaiblissements pour tous, consommables de chacun, "
            "équipement GearQuest du niveau 60"
        )
        notes += [raid_note, *extra]
        ranking = [{"preset": r["preset"], "race": r["race"], "dps": r["dps"], "stdev": r.get("stdev")} for r in rows]
        sections.append({"bracket": "60", "level": RAID_LEVEL, "ranking": ranking})
    else:
        run = run_brackets or _default_brackets(deps)
        kw: dict[str, Any] = {"brackets": brackets, "iterations": iterations}
        if context == "leveling":
            kw.update(conditions="solo", targets=1, objective="leveling")
            notes.append("leveling : seul, repos compris (mana, vie), classé à l'XP par heure")
        else:
            kw.update(conditions="group", targets=DUNGEON_TARGETS, objective="dps")
            notes.append(f"donjon : buffs de groupe, {DUNGEON_TARGETS} cibles identiques, classé au DPS")
        by_bracket: dict[str, dict[str, Any]] = {}
        for key, race in cases:
            try:
                out = run(preset=key, race=race, **kw)
            except Exception as err:  # noqa: BLE001 : une spécialisation en échec n'efface pas les autres
                notes.append(f"{key} : non calculé ({err})")
                continue
            for a in (out.get("provenance") or {}).get("assumptions") or []:
                if a not in notes:
                    notes.append(a)
            for row in out.get("rows") or []:
                if "error" in row or row.get("dps") is None:
                    continue
                section = by_bracket.setdefault(str(row["bracket"]), {"bracket": row["bracket"],
                                                                      "level": row["level"], "ranking": []})  # fmt: skip
                section["ranking"].append({"preset": key, "race": race, "dps": row["dps"], "stdev": row.get("stdev"),
                                           "xp_per_hour": row.get("xp_per_hour"),
                                           "rotation": row.get("rotation")})  # fmt: skip
        order = "xp_per_hour" if context == "leveling" else "dps"
        for section in sorted(by_bracket.values(), key=lambda s: int(s["level"])):
            section["ranking"].sort(key=lambda r: -float(r.get(order) or 0.0))
            sections.append(section)
    doc = {"context": context, "faction": faction.lower(), "order": "dps" if context != "leveling" else "xp_per_hour",
           "brackets": sections,
           "provenance": local_provenance(deps, certainty="suppose", assumptions=notes)}  # fmt: skip
    doc = json.loads(json.dumps(doc, ensure_ascii=False, default=str))
    if brackets is None and not races:  # toutes les tranches et races par défaut : gardée
        path = tier_list_path(deps, context, faction)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return dict(doc)
