"""Rejeu des cas des builds du Mage pour `forever update` (décision 230, point 2) : avant et après un changement des
données, chaque cas est calculé par `forever.build.build_report` (mêmes paramètres que `scripts/replay_builds.py`).

Trois accélérations, sans rien changer au calcul :
- **cache** : chaque cas est écrit dans `<cache>/builds/<étiquette>/<cas>.json` (étiquette : version et empreinte
  réelle des données, `update.replay_label`) avec l'empreinte du code du calcul (`code_fingerprint`) et ses
  paramètres ; un cas déjà calculé sur les mêmes données par le même code n'est jamais recalculé (le côté « avant »
  d'une mesure ou d'une version est presque toujours déjà là) ;
- **cas en parallèle** : les cas à calculer sont répartis sur les cœurs (processus séparés), les plus longs d'abord ;
- **faisceaux du leveling en parallèle** : quand il reste des cœurs, les départs indépendants du leveling
  (`optimize.leveling.leveling_paths`) se calculent chacun dans un processus (mêmes graines, mêmes chemins).

Aucun chiffre de jeu ici : seulement l'orchestration des calculs."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any

PACKAGE = Path(__file__).resolve().parent
# Paramètres du rejeu, communs à `scripts/replay_builds.py` (décision D9) : graine, race, préréglage de l'optimiseur.
SEED = 12345
RACE = "Orc"
PRESET = "complet"
MAX_BEAM_WORKERS = 4  # départs du leveling en mode forever : le faisceau libre et un par arbre
# Ordre de durée des contextes (relevé des passages des 2026-10-09 et 10 : le leveling domine, puis le donjon et le
# raid, le PvP est le plus court) : seul l'ordre compte, pour lancer les cas les plus longs d'abord.
_CONTEXT_WEIGHT = {"leveling": 4, "dungeon": 2, "raid": 2, "pvp-bg": 1, "pvp-world": 1}

Compute = Callable[[str, Path], Mapping[str, Any]]
"""(cas, dossier des données) -> rapport de `build_report` ; injecté par les tests (calcul simulé, en séquentiel)."""
Log = Callable[[str], None]


@lru_cache(maxsize=1)
def code_fingerprint() -> str:
    """Empreinte du code de `forever/` (fichiers `.py`, hors données) : un cas calculé par un autre code est recalculé."""
    digest = hashlib.sha256()
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(PACKAGE).as_posix()
        if rel.startswith("data/") or "__pycache__" in rel:
            continue
        digest.update(rel.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:16]


def params() -> dict[str, Any]:
    return {"race": RACE, "preset": PRESET, "seed": SEED}


def split_case(case: str) -> tuple[str, int]:
    """« leveling-20 » → (« leveling », 20) ; « pvp-bg-40 » → (« pvp-bg », 40)."""
    context, _, level = case.rpartition("-")
    return context, int(level)


def advice(report: Mapping[str, Any]) -> dict[str, Any]:
    """Conseil comparé avant et après : talents, choix et alternative (gagnant, départage, écart)."""
    alternative = report.get("alternative") or {}
    return {
        "talents": report.get("talents"),
        "choices": report.get("choices"),
        "alternative": {k: alternative.get(k) for k in ("better", "decided_by", "diff")},
    }


def case_path(cache_dir: Path, data_dir: Path, case: str) -> Path:
    from forever.update import replay_label

    return cache_dir / "builds" / replay_label(data_dir) / f"{case}.json"


def _cached(path: Path) -> dict[str, Any] | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or doc.get("code") != code_fingerprint() or doc.get("params") != params():
        return None
    return doc


def _write(path: Path, report: Mapping[str, Any], duration: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"report": report, "duration_s": duration, "ablated": [], "code": code_fingerprint(), "params": params()}
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def build_case(case: str, data_dir: Path) -> Mapping[str, Any]:
    """Rapport complet d'un cas, sur `data_dir` (mêmes paramètres que `scripts/replay_builds.py`)."""
    from forever.build import build_report
    from forever.config import default_deps

    context, level = split_case(case)
    deps = dataclasses.replace(default_deps(), data_dir=data_dir)
    return build_report(deps, context, level, race=RACE, preset=PRESET, seed=SEED)


def _worker(case: str, data_dir: str, path: str, beams: int) -> tuple[dict[str, Any], float]:
    """Calcul d'un cas dans un processus du rejeu : faisceaux du leveling sur `beams` processus, résultat écrit."""
    from forever.optimize.leveling import set_beam_workers

    set_beam_workers(beams)
    start = time.perf_counter()
    report = build_case(case, Path(data_dir))
    duration = time.perf_counter() - start
    _write(Path(path), report, duration)
    return advice(report), duration


def longest_first(cases: Sequence[str]) -> list[str]:
    """Cas triés du plus long au plus court (contexte, puis niveau) : le dernier cas lancé est un cas court."""
    return sorted(cases, key=lambda c: (_CONTEXT_WEIGHT.get(split_case(c)[0], 1), split_case(c)[1]), reverse=True)


def worker_budget(cases: Sequence[str], cpus: int) -> tuple[int, int]:
    """(processus pour les cas, processus par cas de leveling pour ses faisceaux) : un processus par cas tant qu'il
    y a des cœurs ; les cœurs restants vont aux faisceaux des cas de leveling, sans dépasser `MAX_BEAM_WORKERS`."""
    outer = max(1, min(len(cases), cpus))
    leveling = sum(1 for c in cases if split_case(c)[0] == "leveling")
    if not leveling:
        return outer, 1
    spare = max(0, cpus - outer)
    return outer, max(1, min(MAX_BEAM_WORKERS, 1 + spare // leveling))


def replay_cases(
    jobs: Sequence[tuple[str, Path]],
    cache_dir: Path,
    *,
    workers: int | None = None,
    compute: Compute | None = None,
    log: Log | None = None,
) -> dict[tuple[str, Path], dict[str, Any]]:
    """Conseil de chaque (cas, dossier des données) : lu dans le cache s'il a été calculé sur les mêmes données par le
    même code, sinon calculé (en parallèle sur `workers` processus, défaut : tous les cœurs ; `compute` : calcul
    simulé, en séquentiel) puis écrit. Rend {(cas, dossier): {"advice", "duration_s", "cached"}}."""
    out: dict[tuple[str, Path], dict[str, Any]] = {}
    todo: list[tuple[str, Path, Path]] = []
    for case, data_dir in dict.fromkeys(jobs):
        path = case_path(cache_dir, data_dir, case)
        doc = _cached(path)
        if doc is not None:
            out[case, data_dir] = {"advice": advice(doc["report"]), "duration_s": doc.get("duration_s"), "cached": True}
        else:
            todo.append((case, data_dir, path))
    if not todo:
        return out
    cpus = workers if workers is not None else (os.cpu_count() or 1)
    order = longest_first([c for c, _, _ in todo])
    todo.sort(key=lambda job: order.index(job[0]))
    outer, beams = worker_budget([c for c, _, _ in todo], cpus)
    if log is not None:
        cached = len(out)
        log(f"rejeu : {len(todo)} cas à calculer ({cached} repris du cache), {outer} processus, faisceaux sur {beams}")
    if compute is not None or outer == 1:
        for case, data_dir, path in todo:
            start = time.perf_counter()
            report = (compute or build_case)(case, data_dir)
            duration = time.perf_counter() - start
            _write(path, report, duration)
            out[case, data_dir] = {"advice": advice(report), "duration_s": duration, "cached": False}
        return out
    with ProcessPoolExecutor(max_workers=outer) as pool:
        futures = {
            (case, data_dir): pool.submit(
                _worker, case, str(data_dir), str(path), beams if split_case(case)[0] == "leveling" else 1
            )
            for case, data_dir, path in todo
        }
        for key, future in futures.items():
            result, duration = future.result()
            out[key] = {"advice": result, "duration_s": duration, "cached": False}
            if log is not None:
                log(f"rejeu : {key[0]} ({replay_label_short(key[1])}) en {duration:.0f} s")
    return out


def replay_label_short(data_dir: Path) -> str:
    from forever.update import replay_label

    return replay_label(data_dir).removeprefix("update-")
