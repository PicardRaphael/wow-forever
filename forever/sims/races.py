"""Races jouables d'une classe comparées par tranche de niveaux (SIM2 §9, demande du 2026-11-08 : « toute race…
meilleur DPS »), calculées par wowsims/forever corrigé (`run_brackets`) : aucun calcul de jeu ici.

Pour chaque tranche, un combat par race jouable de la classe (`races.json` des données de Forever), mêmes talents,
même équipement, même graine (tirages appariés) ; races triées par dégâts par seconde, écart à la meilleure, et
« non départagé » quand l'écart est sous deux erreurs types de la différence (`forever.sims.builds.decide`)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.pipeline import gitops
from forever.pipeline.wowsims_build import wowsims_dir
from forever.provenance import local_provenance
from forever.sims import wowsims
from forever.sims.brackets import parse_brackets, resolve_sources, run_brackets
from forever.sims.builds import decide

RACE_NOTE = ("races : toutes les races jouables de la classe (races.json des données de Forever), sauf liste donnée ; "
             "mêmes talents, même équipement, même graine (tirages appariés) ; « non départagé » : écart sous deux "
             "erreurs types de la différence des moyennes")  # fmt: skip


def playable_race_names(deps: Deps, class_name: str) -> list[str]:
    """Races jouables de la classe (noms du client), lues dans `races.json`, dans l'ordre des noms."""
    from forever.store import load_version

    races = load_version(deps).read_json("races.json")["races"]
    return [name for name in sorted(races) if class_name in (races[name].get("classes") or [])]


def playable_races(deps: Deps, class_name: str) -> list[str]:
    """Races jouables de la classe (noms du proto de wowsims), lues dans `races.json`, dans l'ordre des noms."""
    return [wowsims.race_enum(name) for name in playable_race_names(deps, class_name)]


def _rank(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """Races triées par dégâts ; écart à la meilleure, seuil de bruit et verdict de chacune ; vrai si la meilleure est
    seule devant."""
    rows = sorted(rows, key=lambda r: -float(r["dps"]))
    if not rows:
        return [], False
    best = rows[0]
    ranked = [{**best, "gap_to_best": 0.0, "threshold": 0.0}]
    tied = False
    for row in rows[1:]:
        verdict = decide(row, best)  # gain de la meilleure sur cette race
        tie = verdict["verdict"] == "non départagé"
        tied = tied or tie
        ranked.append({**row, "gap_to_best": float(row["dps"]) - float(best["dps"]), "threshold": verdict["threshold"],
                       "verdict": "non départagé" if tie else "derrière"})  # fmt: skip
    ranked[0]["verdict"] = "non départagé" if tied else "meilleure"
    if len(ranked) > 1:
        ranked[0]["threshold"] = ranked[1]["threshold"]
    return ranked, not tied


def compare_races_brackets(
    deps: Deps,
    *,
    preset: str,
    brackets: str | None,
    races: Sequence[str] | None = None,
    steps: Sequence[Mapping[str, Any]] = (),
    picks_at: Callable[[int], Sequence[Mapping[str, Any]]] | None = None,
    iterations: int | None = None,
    runner: gitops.Runner | None = None,
    anchors: Sequence[Mapping[str, Any]] | None = None,
    conditions: str = "solo",
) -> dict[str, Any]:
    """Par tranche, les races (toutes les races jouables de la classe, ou `races`) classées par dégâts par seconde ;
    une race non jouable par la classe est refusée ; un build illégal à une tranche y est rendu une fois, sans combat."""
    from forever.sims.engines import class_of

    parse_brackets(brackets)  # tranches illisibles refusées avant tout combat
    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir forever_simulate(action='presets')")
    class_name = class_of(chosen)
    playable = playable_races(deps, class_name)
    asked = [r.strip() for r in races or [] if r.strip()]
    if asked:
        wanted = [wowsims.race_enum(r) for r in asked]
        refused = [r for r, token in zip(asked, wanted, strict=True) if token not in playable]
        if refused:
            raise InvalidArgumentError(f"Race non jouable par {class_name} : {', '.join(refused)}.",
                                       "choisir parmi " + ", ".join(t.removeprefix("Race") for t in playable))  # fmt: skip
        wanted = list(dict.fromkeys(wanted))
    else:
        wanted = playable
    if not wanted:
        raise InvalidArgumentError(f"Aucune race jouable pour {class_name} dans races.json.", "vérifier les données")
    runs = [run_brackets(deps, preset=preset, race=race, brackets=brackets, steps=steps, picks_at=picks_at,
                         iterations=iterations, runner=runner, anchors=anchors, conditions=conditions)
            for race in wanted]  # fmt: skip
    out_brackets: list[dict[str, Any]] = []
    for i, first in enumerate(runs[0]["rows"]):
        cells = [(race, run["rows"][i]) for race, run in zip(wanted, runs, strict=True)]
        entry: dict[str, Any] = {"bracket": first["bracket"], "level": first["level"], "talents": first["talents"]}
        errors = [(race, row["error"]) for race, row in cells if "error" in row]
        ok = [{"race": race, "dps": row["dps"], "stdev": row["stdev"], "iterations": row["iterations"],
               "rotation": row.get("rotation")} for race, row in cells if "error" not in row]  # fmt: skip
        if errors and len({e["message"] for _, e in errors}) == 1 and not ok:
            entry["error"] = errors[0][1]  # même erreur pour toutes les races (talents illégaux) : rendue une fois
        elif errors:
            entry["errors"] = [{"race": race, "error": err} for race, err in errors]
        ranking, decided = _rank(ok)
        entry["ranking"] = ranking
        entry["best"] = ranking[0]["race"] if ranking else None
        entry["decided"] = decided
        if ok:
            ref = cells[0][1] if "error" not in cells[0][1] else next(r for _, r in cells if "error" not in r)
            entry["talents_string"] = ref.get("talents_string")
            entry["equipment"] = ref.get("equipment")
        out_brackets.append(entry)
    notes = [*runs[0]["provenance"]["assumptions"], RACE_NOTE]
    return {"preset": chosen.key, "class": class_name, "conditions": conditions, "races": wanted,
            "brackets": out_brackets,
            "provenance": local_provenance(deps, certainty="suppose", assumptions=notes)}  # fmt: skip


def races_from_sources(
    deps: Deps,
    *,
    preset: str,
    brackets: str | None,
    races: Sequence[str] | None = None,
    path: str = "auto",
    gear: str = "gearquest",
    spec: str | None = None,
    iterations: int | None = None,
    conditions: str = "solo",
) -> dict[str, Any]:
    """`compare_races_brackets` avec les sources installées (parcours `path`, équipement `gear`, comme
    `run_from_sources`) ; équipement de GearQuest choisi une fois par tranche, pour la première race comparée."""
    from forever.sims.engines import class_of

    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir forever_simulate(action='presets')")
    # race du choix de GearQuest : nom du client (première race demandée, sinon première race jouable)
    gear_race = (next(iter(races), None) if races else None) or playable_race_names(deps, class_of(chosen))[0]
    steps, picks_at, anchors, notes = resolve_sources(deps, preset=preset, race=gear_race, path=path, gear=gear,
                                                      spec=spec)  # fmt: skip
    cache: dict[int, list[Mapping[str, Any]]] = {}

    def same_picks(level: int) -> Sequence[Mapping[str, Any]]:  # mêmes objets pour toutes les races
        if level not in cache and picks_at is not None:
            cache[level] = list(picks_at(level))
        return cache.get(level, [])

    out = compare_races_brackets(deps, preset=preset, brackets=brackets, races=races, steps=steps,
                                 picks_at=same_picks if picks_at else None, iterations=iterations, anchors=anchors,
                                 conditions=conditions)  # fmt: skip
    extra = [*notes]
    if picks_at is not None:
        extra.append(f"équipement de GearQuest choisi pour la race {gear_race}, le même pour toutes les races")
    out["provenance"]["assumptions"] = [*out["provenance"]["assumptions"], *extra]
    return out
