"""Git et `gh` dans le clone dédié de `forever update` (T08d, bloc F, décision 181).

Le passage automatique ne touche jamais l'arbre de travail de la session : il travaille dans un clone du dépôt rangé
dans le cache (`<cache>/update/repo`). Chemin d'une écriture : branche `data/<version>-r<N>`, commit, poussée, CI
attendue sous Ubuntu **et** Windows, puis `main` avancé sur `origin` en avance rapide (`git push origin
<branche>:main`, refusé par le serveur si `main` a bougé), clone local avancé, branche supprimée en local et à
distance. Garde-fous : `origin/main` relu d'abord ; refus si l'arbre est sale hors des chemins que le passage écrit,
ou hors de `main` ; **jamais de poussée forcée** (ni `--force`, ni `-f`, ni refspec en `+`). Un reste d'écriture
interrompue (passage tué pendant `verify` ou la CI) dans les seuls chemins du passage est remis dans l'état de `HEAD`
(correctif du 2026-10-06).

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
    dirty: tuple[str, ...] = ()  # chemins modifiés hors des chemins du passage (refus)
    discarded: tuple[str, ...] = ()  # reste d'un passage interrompu, retiré (dossier vide : chemin terminé par /)


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


def current_branch(runner: Runner, clone: Path) -> str:
    return _run(runner, ["git", "rev-parse", "--abbrev-ref", "HEAD"], clone).stdout.strip()


def head_sha(runner: Runner, clone: Path, ref: str = "HEAD") -> str:
    return _rev(runner, clone, ref)


def fetch(runner: Runner, clone: Path) -> None:
    _run(runner, ["git", "fetch", "--prune", "origin"], clone)


def remote_branch_sha(runner: Runner, clone: Path, branch: str) -> str | None:
    """Sha de `origin/<branch>` (après `fetch`), None si la branche n'existe pas à distance."""
    out = _run(runner, ["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"], clone, check=False)
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else None


def is_ancestor(runner: Runner, clone: Path, ancestor: str, descendant: str) -> bool:
    out = _run(runner, ["git", "merge-base", "--is-ancestor", ancestor, descendant], clone, check=False)
    return out.returncode == 0


def dirty_paths(runner: Runner, clone: Path) -> list[str]:
    return _dirty(runner, clone)


def leave_branch(runner: Runner, clone: Path, branch: str) -> None:
    """Clone remis sur `main` et branche locale `branch` retirée (abandonnée ou déjà fusionnée) ; la branche distante
    n'est pas touchée."""
    _run(runner, ["git", "switch", "main"], clone)
    _run(runner, ["git", "branch", "-D", branch], clone)


def drop_stale_branch(runner: Runner, clone: Path, branch: str) -> bool:
    """Retire une branche `branch` laissée par un essai abandonné (locale et distante) avant d'en pousser une
    nouvelle du même nom : sans cela, la poussée serait refusée (jamais de poussée forcée). Vrai si une existait."""
    found = False
    if _run(runner, ["git", "branch", "--list", branch], clone).stdout.strip():
        _run(runner, ["git", "branch", "-D", branch], clone)
        found = True
    if remote_branch_sha(runner, clone, branch) is not None:
        _run(runner, ["git", "push", "origin", "--delete", branch], clone)
        found = True
    return found


def ensure_clone(runner: Runner, url: str, path: Path) -> None:
    """Clone dédié créé au premier passage (chemins longs permis sous Windows) ; rien s'il existe."""
    if (path / ".git").exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(runner, ["git", "clone", "-c", "core.longpaths=true", url, str(path)], path.parent)


def _dirty(runner: Runner, clone: Path) -> list[str]:
    """Chemins modifiés ou non suivis, fichier par fichier (`--untracked-files=all`)."""
    listed = _run(runner, ["git", "status", "--porcelain", "-z", "--untracked-files=all"], clone).stdout
    fields = [f for f in listed.split("\0") if f]
    paths: list[str] = []
    i = 0
    while i < len(fields):
        status, path = fields[i][:2], fields[i][3:]
        paths.append(path)
        i += 2 if status[0] in "RC" else 1  # renommage ou copie : le chemin d'origine suit
    return sorted(paths)


def _remove_empty_parents(clone: Path, rel: str) -> None:
    parent = (clone / rel).parent
    while parent != clone and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def prune_empty_dirs(clone: Path, owned: Sequence[str]) -> list[str]:
    """Retire les dossiers vides sous les dossiers du passage (préfixes `owned` terminés par `/`) : `git status` ne
    les voit pas ; rend leurs chemins, terminés par `/`."""
    removed: list[str] = []
    for prefix in owned:
        root = clone / prefix.rstrip("/")
        if not prefix.endswith("/") or not root.is_dir():
            continue
        for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(path.iterdir()):
                path.rmdir()
                removed.append(path.relative_to(clone).as_posix() + "/")
    return sorted(removed)


def sync_main(runner: Runner, clone: Path, owned: Sequence[str] = ()) -> SyncResult:
    """`fetch`, contrôle de l'arbre (sur `main`, propre hors des chemins `owned` que le passage écrit ; leur reste
    est remis dans l'état de `HEAD`), puis avance rapide sur `origin/main`."""
    _run(runner, ["git", "fetch", "--prune", "origin"], clone)
    origin_main = _rev(runner, clone, "origin/main")
    branch = _run(runner, ["git", "rev-parse", "--abbrev-ref", "HEAD"], clone).stdout.strip()
    if branch != "main":
        return SyncResult(False, f"branche courante {branch}, main attendue", origin_main, False)
    dirty = _dirty(runner, clone)
    outside = tuple(p for p in dirty if not any(p.startswith(prefix) for prefix in owned))
    if outside:
        return SyncResult(False, "arbre de travail modifié", origin_main, False, dirty=outside)
    discarded = discard_changes(runner, clone, dirty) if dirty else []
    left = tuple(_dirty(runner, clone)) if dirty else ()
    if left:
        return SyncResult(False, "arbre de travail modifié", origin_main, False, dirty=left)
    gone = tuple(sorted(set(discarded) | set(prune_empty_dirs(clone, owned))))
    if _rev(runner, clone, "HEAD") == origin_main:
        return SyncResult(True, None, origin_main, False, discarded=gone)
    merged = _run(runner, ["git", "merge", "--ff-only", "origin/main"], clone, check=False)
    if merged.returncode != 0:
        reason = "main local diverge de origin/main (avance rapide impossible)"
        return SyncResult(False, reason, origin_main, False, discarded=gone)
    return SyncResult(True, None, origin_main, True, discarded=gone)


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


def origin_url(runner: Runner, repo: Path) -> str:
    """URL d'`origin` du dépôt de la session (lue une fois, gardée dans `<cache>/update/config.json`)."""
    return _run(runner, ["git", "remote", "get-url", "origin"], repo).stdout.strip()


def discard_changes(runner: Runner, clone: Path, paths: Sequence[str] = (".",)) -> list[str]:
    """Remet `paths` du clone dans l'état de `HEAD` après une écriture abandonnée (verify rouge, passage interrompu) :
    fichiers suivis restaurés, fichiers non suivis retirés un par un (jamais `git clean -f`), puis leurs dossiers
    devenus vides ; rend les chemins non suivis retirés et les chemins suivis restaurés (hors `.`)."""
    listed = _run(runner, ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", *paths], clone).stdout
    removed = [p for p in listed.split("\0") if p]
    tracked = [p for p in paths if p not in removed]
    if tracked:
        _run(runner, ["git", "restore", "--staged", "--worktree", "--", *tracked], clone)
    for rel in removed:
        (clone / rel).unlink(missing_ok=True)
        _remove_empty_parents(clone, rel)
    return sorted(set(removed) | {p for p in tracked if p != "."})


def remote_ahead(runner: Runner, repo: Path, origin_main: str) -> bool:
    """Vrai si `origin_main` (sha relevé par le clone dédié) n'est pas déjà dans le `HEAD` du dépôt de la session :
    `git pull` y apporterait des données. Local, sans réseau ; un sha inconnu du dépôt compte comme en avance."""
    head = _run(runner, ["git", "rev-parse", "HEAD"], repo).stdout.strip()
    if head == origin_main:
        return False
    contained = runner(["git", "merge-base", "--is-ancestor", origin_main, head], repo, None)
    return contained.returncode != 0
