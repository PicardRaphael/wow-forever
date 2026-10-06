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

import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple, Protocol

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
    raise NotImplementedError


def ensure_clone(runner: Runner, url: str, path: Path) -> None:
    raise NotImplementedError


def sync_main(runner: Runner, clone: Path) -> SyncResult:
    raise NotImplementedError


def remote_has(runner: Runner, clone: Path, version: str, revision: int | None) -> bool:
    raise NotImplementedError


def commit_branch(runner: Runner, clone: Path, branch: str, paths: Sequence[str], message: str) -> str:
    raise NotImplementedError


def push(runner: Runner, clone: Path, branch: str) -> None:
    raise NotImplementedError


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
    raise NotImplementedError


def merge_ff_and_push(runner: Runner, clone: Path, branch: str) -> MergeResult:
    raise NotImplementedError


def delete_branch(runner: Runner, clone: Path, branch: str) -> None:
    raise NotImplementedError
