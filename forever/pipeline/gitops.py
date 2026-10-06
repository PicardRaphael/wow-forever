"""Git et `gh` dans le clone dédié de `forever update` (T08d, bloc F, décision 181).

Le passage automatique ne touche jamais l'arbre de travail de la session : il travaille dans un clone du dépôt rangé
dans le cache (`<cache>/update/repo`). Chemin d'une écriture : branche `data/<version>-r<N>`, commit, poussée, CI
attendue sous Ubuntu **et** Windows, puis `main` avancé sur `origin` en avance rapide (`git push origin
<branche>:main`, refusé par le serveur si `main` a bougé), clone local avancé, branche supprimée en local et à
distance. Garde-fous : `origin/main` relu d'abord ; refus si l'arbre est sale ou hors de `main` ; **jamais de poussée
forcée** (ni `--force`, ni `-f`, ni refspec en `+`).

C'est du réseau (fetch, push, API GitHub) : le module vit dans `pipeline/`. Les commandes passent par un `Runner`
injectable (liste d'arguments, jamais de shell) ; les tests le remplacent (git réel sur un dépôt nu local, `gh`
simulé)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple, Protocol

from forever.errors import EXIT_NETWORK, ForeverError

CI_WORKFLOW = "ci.yml"
CI_JOBS = ("ubuntu", "windows")  # sous-chaînes des noms des jobs exigés en succès


class Runner(Protocol):
    def __call__(
        self, args: Sequence[str], cwd: Path, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]: ...


class GitOpsError(ForeverError):
    """Commande git ou `gh` en échec (réseau, authentification, dépôt)."""

    exit_code = EXIT_NETWORK

    def __init__(self, message: str, action: str = "relancer `forever update` ; voir le journal du passage") -> None:
        super().__init__("git_failed", message, action)


class SyncResult(NamedTuple):
    ok: bool
    reason: str | None
    origin_main: str
    advanced: bool


class CiResult(NamedTuple):
    ok: bool
    status: str  # success | failure | timeout | not_found
    url: str | None
    jobs: dict[str, str]  # nom du job -> conclusion


class MergeResult(NamedTuple):
    ok: bool
    reason: str | None  # None | main_moved


def subprocess_runner(args: Sequence[str], cwd: Path, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Exécuteur de production : liste d'arguments, sans shell ni saisie (aucune invite d'authentification)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GH_PROMPT_DISABLED": "1", "GCM_INTERACTIVE": "never"}
    return subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=env,
    )


def _run(
    runner: Runner, args: Sequence[str], cwd: Path, *, timeout: float | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    out = runner(args, cwd, timeout)
    if check and out.returncode != 0:
        detail = (out.stderr or out.stdout or "").strip().splitlines()
        raise GitOpsError(
            f"`{' '.join(args)}` a échoué ({out.returncode}) : {detail[-1] if detail else 'sans message'}"
        )
    return out


def _rev(runner: Runner, clone: Path, ref: str) -> str:
    return _run(runner, ["git", "rev-parse", ref], clone).stdout.strip()


def ensure_clone(runner: Runner, url: str, path: Path) -> None:
    """Clone dédié créé au premier passage (chemins longs permis sous Windows) ; rien s'il existe."""
    if (path / ".git").exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(runner, ["git", "clone", "-c", "core.longpaths=true", url, str(path)], path.parent)


def sync_main(runner: Runner, clone: Path) -> SyncResult:
    """`fetch`, contrôle de l'arbre (propre, sur `main`), puis avance rapide sur `origin/main`."""
    _run(runner, ["git", "fetch", "--prune", "origin"], clone)
    origin_main = _rev(runner, clone, "origin/main")
    branch = _run(runner, ["git", "rev-parse", "--abbrev-ref", "HEAD"], clone).stdout.strip()
    if branch != "main":
        return SyncResult(False, f"branche courante {branch}, main attendue", origin_main, False)
    if _run(runner, ["git", "status", "--porcelain"], clone).stdout.strip():
        return SyncResult(False, "arbre de travail modifié", origin_main, False)
    if _rev(runner, clone, "HEAD") == origin_main:
        return SyncResult(True, None, origin_main, False)
    merged = _run(runner, ["git", "merge", "--ff-only", "origin/main"], clone, check=False)
    if merged.returncode != 0:
        return SyncResult(False, "main local diverge de origin/main (avance rapide impossible)", origin_main, False)
    return SyncResult(True, None, origin_main, True)


def remote_has(runner: Runner, clone: Path, version: str, revision: int | None) -> bool:
    """Vrai si `origin/main` porte déjà la version (et la révision, si elle est donnée) ; lu sans checkout."""
    if revision is None:
        listed = _run(runner, ["git", "ls-tree", "--name-only", "origin/main", f"forever/data/{version}"], clone)
        return bool(listed.stdout.strip())
    shown = _run(runner, ["git", "show", f"origin/main:forever/data/{version}/revisions.json"], clone, check=False)
    if shown.returncode != 0:
        return False
    try:
        doc = json.loads(shown.stdout)
        numbers = [int(r["revision"]) for r in doc.get("revisions", [])]
    except (ValueError, KeyError, TypeError, AttributeError):
        return False
    return bool(numbers) and max(numbers) >= revision


def commit_branch(runner: Runner, clone: Path, branch: str, paths: Sequence[str], message: str) -> str:
    """Branche créée depuis `main`, chemins ajoutés, commit (identité git du poste) ; rend le sha."""
    _run(runner, ["git", "switch", "-c", branch], clone)
    _run(runner, ["git", "add", "--", *paths], clone)
    _run(runner, ["git", "commit", "-m", message], clone)
    return _rev(runner, clone, "HEAD")


def push(runner: Runner, clone: Path, branch: str) -> None:
    _run(runner, ["git", "push", "-u", "origin", branch], clone)


def wait_ci(
    runner: Runner,
    clone: Path,
    branch: str,
    sha: str,
    timeout_s: float,
    *,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    poll_s: float = 20.0,
) -> CiResult:
    """Exécution de `ci.yml` du sha poussé, attendue jusqu'à sa fin ; succès seulement si les jobs Ubuntu **et**
    Windows réussissent."""
    deadline = clock() + timeout_s
    run: dict[str, Any] | None = None
    while run is None:
        listed = _run(
            runner,
            ["gh", "run", "list", "--branch", branch, "--workflow", CI_WORKFLOW, "--json",
             "databaseId,headSha,status,conclusion,url"],
            clone,
        )  # fmt: skip
        try:
            runs = json.loads(listed.stdout or "[]")
        except ValueError:
            runs = []
        run = next((r for r in runs if isinstance(r, dict) and r.get("headSha") == sha), None)
        if run is None:
            if clock() >= deadline:
                return CiResult(False, "not_found", None, {})
            sleep(poll_s)
    run_id, url = str(run["databaseId"]), run.get("url")
    remaining = max(deadline - clock(), 1.0)
    try:
        _run(runner, ["gh", "run", "watch", run_id, "--exit-status"], clone, timeout=remaining, check=False)
    except subprocess.TimeoutExpired:
        return CiResult(False, "timeout", url, {})
    viewed = _run(runner, ["gh", "run", "view", run_id, "--json", "jobs"], clone)
    try:
        jobs = {str(j["name"]): str(j.get("conclusion")) for j in json.loads(viewed.stdout).get("jobs", [])}
    except (ValueError, KeyError, TypeError, AttributeError):
        jobs = {}
    ok = all(any(k in name.lower() and c == "success" for name, c in jobs.items()) for k in CI_JOBS)
    return CiResult(ok, "success" if ok else "failure", url, jobs)


def merge_ff_and_push(runner: Runner, clone: Path, branch: str) -> MergeResult:
    """`main` distant avancé sur la branche (refusé par le serveur si ce n'est pas une avance rapide), puis clone
    local remis sur `main` à jour."""
    pushed = _run(runner, ["git", "push", "origin", f"{branch}:main"], clone, check=False)
    if pushed.returncode != 0:
        return MergeResult(False, "main_moved")
    _run(runner, ["git", "switch", "main"], clone)
    _run(runner, ["git", "fetch", "origin"], clone)
    _run(runner, ["git", "merge", "--ff-only", "origin/main"], clone)
    return MergeResult(True, None)


def delete_branch(runner: Runner, clone: Path, branch: str) -> None:
    _run(runner, ["git", "push", "origin", "--delete", branch], clone)
    _run(runner, ["git", "branch", "-d", branch], clone)
