"""Rejeu des cas des builds du Mage pour `forever update` (décision 230, point 2) : avant et après un changement des
données, chaque cas est calculé par `forever.build.build_report` (mêmes paramètres que `scripts/replay_builds.py`).

Trois accélérations, sans rien changer au calcul :
- **cache** : chaque cas est écrit dans `<cache>/builds/<étiquette>/<cas>.json` (étiquette : version et empreinte
  réelle des données, `update.replay_label`) avec l'empreinte du code du calcul (`code_fingerprint`) et ses
  paramètres ; un cas déjà calculé sur les mêmes données par le même code n'est jamais recalculé (le côté « avant »
  d'une mesure ou d'une version est presque toujours déjà là) ;
- **cas en parallèle** : les cas à calculer sont répartis sur les cœurs, les plus longs d'abord, par un sous-processus
  dédié (`python -m forever.replay`) : les processus de calcul ne dépendent jamais du point d'entrée de l'appelant
  (CLI, `python -m forever`, pont, serveur MCP), que Windows réimporterait dans chaque processus ;
- **faisceaux du leveling en parallèle** : quand il reste des cœurs, les départs indépendants du leveling
  (`optimize.leveling.leveling_paths`) se calculent chacun dans un processus (mêmes graines, mêmes chemins).

Aucun chiffre de jeu ici : seulement l'orchestration des calculs."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any

from forever.errors import ForeverError

PACKAGE = Path(__file__).resolve().parent
# Paramètres du rejeu, communs à `scripts/replay_builds.py` (décision D9) : graine, race, préréglage de l'optimiseur.
SEED = 12345
RACE = "Orc"
PRESET = "complet"
MAX_BEAM_WORKERS = 4  # départs du leveling en mode forever : le faisceau libre et un par arbre
# Ordre de durée des contextes (relevé des passages des 2026-10-09 et 10 : le leveling domine, puis le donjon et le
# raid, le PvP est le plus court) : seul l'ordre compte, pour lancer les cas les plus longs d'abord.
_CONTEXT_WEIGHT = {"leveling": 4, "dungeon": 2, "raid": 2, "pvp-bg": 1, "pvp-world": 1}

class ReplayFailedError(ForeverError):
    """Le sous-processus du rejeu parallèle a échoué (sortie d'erreur rendue)."""

    def __init__(self, detail: str) -> None:
        super().__init__("replay_failed", f"Rejeu parallèle en échec : {detail}", "relancer `forever update`")


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


def beam_plan(cases: Sequence[str], cpus: int) -> list[int]:
    """Processus des faisceaux de chaque cas (dans l'ordre de `cases`, déjà trié du plus long au plus court) : un
    processus par cas, puis les cœurs restants aux cas de leveling, les plus longs d'abord (chemin critique du rejeu),
    jusqu'à `MAX_BEAM_WORKERS` chacun."""
    plan = [1] * len(cases)
    spare = max(0, cpus - min(len(cases), cpus))
    for i, case in enumerate(cases):
        if split_case(case)[0] != "leveling" or spare <= 0:
            continue
        extra = min(MAX_BEAM_WORKERS - 1, spare)
        plan[i] += extra
        spare -= extra
    return plan


def worker_budget(cases: Sequence[str], cpus: int) -> tuple[int, int]:
    """(processus pour les cas, plus grand nombre de processus de faisceaux d'un cas) : `beam_plan` résumé."""
    outer = max(1, min(len(cases), cpus))
    return outer, max(beam_plan(longest_first(cases), cpus), default=1)


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
    plan = beam_plan([c for c, _, _ in todo], cpus)
    if log is not None:
        cached = len(out)
        log(f"rejeu : {len(todo)} cas à calculer ({cached} repris du cache), {outer} processus, faisceaux du leveling sur {beams} au plus")
    if compute is not None or outer == 1:
        for case, data_dir, path in todo:
            start = time.perf_counter()
            report = (compute or build_case)(case, data_dir)
            duration = time.perf_counter() - start
            _write(path, report, duration)
            out[case, data_dir] = {"advice": advice(report), "duration_s": duration, "cached": False}
        return out
    request = {
        "workers": outer,
        "jobs": [[case, str(d), str(path), n] for (case, d, path), n in zip(todo, plan, strict=True)],
    }
    for line in _run_child(request, cache_dir):
        if log is not None:
            log(line)
    for case, data_dir, path in todo:
        doc = _cached(path)
        if doc is None:
            raise ReplayFailedError(f"{case} absent du cache après le calcul ({path})")
        out[case, data_dir] = {"advice": advice(doc["report"]), "duration_s": doc.get("duration_s"), "cached": False}
    return out


def _run_child(request: Mapping[str, Any], cache_dir: Path) -> list[str]:
    """Lance `python -m forever.replay <demande>` et rend ses lignes de sortie ; ReplayFailedError en cas d'échec."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=cache_dir, delete=False, encoding="utf-8") as handle:
        json.dump(request, handle)
        request_path = Path(handle.name)
    try:
        done = subprocess.run(
            [sys.executable, "-m", "forever.replay", str(request_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    finally:
        request_path.unlink(missing_ok=True)
    if done.returncode != 0:
        tail = (done.stderr or done.stdout).strip().splitlines()[-5:]
        raise ReplayFailedError(" | ".join(tail) or f"code {done.returncode}")
    return [line for line in done.stdout.splitlines() if line.strip()]


def _pool(jobs: Sequence[Sequence[Any]], workers: int) -> None:
    """Calcule les cas de `jobs` ([cas, données, chemin, faisceaux]) sur `workers` processus ; une ligne par cas."""
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {str(job[0]) + " " + str(job[1]): pool.submit(_worker, *job) for job in jobs}
        for name, future in futures.items():
            _, duration = future.result()
            case, data_dir = name.split(" ", 1)
            print(f"rejeu : {case} ({replay_label_short(Path(data_dir))}) en {duration:.0f} s", flush=True)


def main(argv: Sequence[str]) -> int:
    request = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    _pool(request["jobs"], int(request["workers"]))
    return 0


def replay_label_short(data_dir: Path) -> str:
    from forever.update import replay_label

    return replay_label(data_dir).removeprefix("update-")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
