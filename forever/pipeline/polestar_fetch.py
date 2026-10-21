"""Clone en cache des guides de Polestar (décision 289) : `forever route polestar` copie le dépôt public en lecture
seule (clone superficiel), puis le remet sur son dernier commit à chaque appel ; rien n'est jamais poussé, rien n'est
copié dans le dépôt de forever, l'addon n'est jamais installé. Le commit épinglé se lit dans le clone
(`forever.compare.polestar_commit`) et part dans l'attribution de chaque route livrée."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

REPO = "https://github.com/fitzforge/polestar.git"


def _run(args: Sequence[str], cwd: Path | None = None) -> Any:
    """git du réseau par le seul exécuteur de `forever.pipeline.gitops` (sans shell, sans invite, sans fenêtre)."""
    from forever.pipeline.gitops import _run as run_checked
    from forever.pipeline.gitops import subprocess_runner

    return run_checked(subprocess_runner, args, cwd or Path.cwd(), timeout=300)


def update_polestar(cache_dir: Path, *, run: Callable[..., Any] = _run) -> Path:
    """Clone (premier appel) ou mise à jour du clone sur le dernier commit de la branche par défaut ; rend son dossier."""
    from forever.compare import polestar_clone

    clone = polestar_clone(cache_dir)
    if not (clone / ".git").is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", REPO, str(clone)], cwd=clone.parent)
        return clone
    run(["git", "fetch", "--depth", "1", "origin"], cwd=clone)
    run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=clone)
    return clone
