"""Analyse complète gardée par spécialisation et tranche (SIM2 bloc 15, demande du 2026-11-08 : « analyse tous les
équipements, BiS, talents dans l'ordre, tout, pour que je puisse te poser des questions »). Aucun calcul de jeu ici :
chaque chiffre vient de wowsims corrigé (`forever.sims.brackets`).

Pour un préréglage et une race, à chaque tranche : talents dans l'ordre de prise jusqu'au niveau, meilleure rotation,
dégâts par seconde (conditions solo), priorité des statistiques, meilleurs objets par emplacement. Gardée dans le
cache par version des données et commit de wowsims ; une analyse déjà faite est relue, pas recalculée."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from forever.config import Deps

FOLDER = "analysis"


def _version(deps: Deps) -> tuple[str, str]:
    from forever.pipeline.wowsims_build import pinned
    from forever.store import load_version

    pin = pinned(deps.cache_dir) or {}
    commit = str(pin.get("commit") or "sans-wowsims")[:12]
    patches = str((pin.get("patches") or {}).get("sha256") or "")[:8]
    return load_version(deps).game_version, f"{commit}-{patches}" if patches else commit


def analysis_path(deps: Deps, preset: str, race: str) -> Path:
    """Fichier de l'analyse : `<cache>/analysis/<version des données>/<commit et correctifs>/<préréglage>-<race>.json`."""
    from forever.sims.wowsims import race_enum

    version, sims = _version(deps)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", preset).strip("-")
    return deps.cache_dir / FOLDER / version / sims / f"{slug}-{race_enum(race)}.json"


def _default_run(deps: Deps) -> Callable[..., dict[str, Any]]:
    from forever.pipeline.wowsims_build import wowsims_dir
    from forever.sims import wowsims
    from forever.sims.brackets import run_from_sources

    known = wowsims.stat_names(wowsims_dir(deps.cache_dir) / "forever")
    stats = [s for s in wowsims.STAT_TO_GUIDE if s in known]

    def run(**kw: Any) -> dict[str, Any]:
        return run_from_sources(deps, preset=kw["preset"], race=kw["race"], brackets=kw.get("brackets"),
                                stats=stats, reference=None, iterations=kw.get("iterations"))  # fmt: skip

    return run


def _default_gear(deps: Deps) -> Callable[..., dict[str, Any]]:
    from forever.sims.brackets import optimise_from_sources

    def gear(**kw: Any) -> dict[str, Any]:
        return optimise_from_sources(deps, preset=kw["preset"], race=kw["race"], level=kw["level"], equipped={},
                                     iterations=kw.get("iterations"))  # fmt: skip

    return gear


def _default_steps(deps: Deps, preset: str) -> Callable[[], tuple[list[dict[str, Any]], str]]:
    from forever.errors import InvalidArgumentError
    from forever.pipeline.wowsims_build import wowsims_dir
    from forever.sims import brackets as br
    from forever.sims import wowsims
    from forever.sims.engines import class_of

    def steps() -> tuple[list[dict[str, Any]], str]:
        presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
        chosen = next(p for p in presets if p.key == preset)
        try:
            return br._plan_steps(deps, class_of(chosen), chosen, None)
        except InvalidArgumentError:
            return br._popular_steps(deps, class_of(chosen), chosen)

    return steps


def analyse_spec(
    deps: Deps,
    *,
    preset: str,
    race: str,
    brackets: str | None = None,
    iterations: int | None = None,
    run: Callable[..., dict[str, Any]] | None = None,
    gear: Callable[..., dict[str, Any]] | None = None,
    steps: Callable[[], tuple[list[dict[str, Any]], str]] | None = None,
) -> dict[str, Any]:
    """Analyse d'un préréglage et d'une race (voir le module) ; relue si elle existe déjà."""
    from forever.provenance import local_provenance

    path = analysis_path(deps, preset, race)
    if path.is_file():
        return dict(json.loads(path.read_text(encoding="utf-8")))
    out = (run or _default_run(deps))(preset=preset, race=race, brackets=brackets, iterations=iterations)
    order, order_source = (steps or _default_steps(deps, preset))()
    rows = []
    for row in out["rows"]:
        level = int(row["level"])
        entry: dict[str, Any] = {
            "bracket": row.get("bracket"),
            "level": level,
            "talent_order": [dict(s) for s in order if int(s["level"]) <= level],
        }
        if "error" in row:
            rows.append({**entry, "error": row["error"]})
            continue
        weights = row.get("weights") or {}
        entry.update(
            dps=row.get("dps"),
            stdev=row.get("stdev"),
            rotation=row.get("rotation"),
            rotations=row.get("rotations"),
            talents=row.get("talents"),
            stat_priority=weights.get("priority"),
            stat_weights=weights.get("normalised"),
        )
        try:
            entry["gear"] = (gear or _default_gear(deps))(preset=preset, race=race, level=level,
                                                         iterations=iterations).get("by_slot")  # fmt: skip
        except Exception as err:  # noqa: BLE001 : une tranche sans optimisation n'efface pas les autres
            entry["gear_error"] = str(err)
        rows.append(entry)
    notes = [*((out.get("provenance") or {}).get("assumptions") or []), f"ordre des talents : {order_source}"]
    doc = {
        "preset": preset,
        "race": out.get("race"),
        "brackets": rows,
        "provenance": local_provenance(deps, certainty="suppose", assumptions=notes),
    }
    doc = json.loads(json.dumps(doc, ensure_ascii=False, default=str))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return dict(doc)


def read_analysis(deps: Deps, preset: str, race: str) -> dict[str, Any] | None:
    """Analyse gardée d'un préréglage et d'une race (version courante des données et de wowsims) ; None si absente."""
    path = analysis_path(deps, preset, race)
    if path.is_file():
        return dict(json.loads(path.read_text(encoding="utf-8")))
    # nouvelle version des données ou de wowsims : la dernière analyse gardée, marquée périmée, en attendant le calcul
    older = sorted(deps.cache_dir.joinpath(FOLDER).glob(f"*/*/{path.name}"), key=lambda q: q.stat().st_mtime)
    if not older:
        return None
    doc = dict(json.loads(older[-1].read_text(encoding="utf-8")))
    doc["stale"] = {"data_version": older[-1].parent.parent.name, "wowsims": older[-1].parent.name,
                    "note": "analyse d'une version précédente : relancer `forever sims analyse` (ou attendre la veille)"}  # fmt: skip
    return doc


DPS_SPECS = ("druid/balance", "druid/feralcat", "hunter/dps", "mage/dps", "paladin/retribution", "priest/dps",
             "rogue/dps", "shaman/elemental", "shaman/enhancement", "warlock/dps", "warrior/dps")  # fmt: skip


def dps_presets(deps: Deps) -> list[tuple[str, str]]:
    """(préréglage, race) de chaque spécialisation de dégâts du dépôt épinglé, race jouable par défaut de la classe
    (lue dans les données de Forever)."""
    from forever.pipeline.wowsims_build import wowsims_dir
    from forever.sims import wowsims
    from forever.sims.engines import class_of
    from forever.update import _playable_races

    races = _playable_races(deps)
    out = []
    for p in wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever"):
        if p.key.rsplit("/", 1)[0] in DPS_SPECS and races.get(class_of(p)):
            out.append((p.key, races[class_of(p)].removeprefix("Race")))
    return out
