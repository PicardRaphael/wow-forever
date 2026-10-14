"""Sondes de `forever doctor` (LN1, bloc D, décision 271) : sous-processus **locaux** seulement, jamais de réseau.

- `gh --version` et `gh auth token` (sortie jetée : seul le code dit qu'un jeton est présent ; `gh auth status`
  interroge GitHub et n'est jamais lancé) ;
- `claude auth status` (lit les identifiants locaux, relevé du 2026-10-14 derrière un proxy inexistant : réponse en
  0,2 s ; seuls `loggedIn` et `authMethod` sont gardés, l'e-mail et l'organisation sont jetés, jamais écrits ;
  `.credentials.json` n'est jamais lu) ;
- `uv sync --dry-run --offline --locked` (dit si `.venv` suit `uv.lock` sans rien télécharger ni installer) ;
- l'interpréteur réel du pont importe-t-il `forever.cli` (`spawn.probe_environment`, décision 241) ;
- `schtasks /Query /XML` des deux tâches (`autostart.schtasks`), surveillance et pont en marche."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from forever.doctor import Probes

_TIMEOUT_S = 30
_NO_WINDOW = 0x08000000


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(  # liste d'arguments, sans shell
            args,
            cwd=cwd,
            capture_output=True,
            timeout=_TIMEOUT_S,
            check=False,
            stdin=subprocess.DEVNULL,
            creationflags=_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def gh_version() -> str | None:
    done = _run(["gh", "--version"])
    if done is None or done.returncode != 0:
        return None
    lines = done.stdout.decode("utf-8", errors="replace").strip().splitlines()
    return lines[0] if lines else "gh"


def gh_token() -> bool | None:
    """Un jeton GitHub est-il enregistré ? (sortie jetée, jamais lue ni gardée)"""
    done = _run(["gh", "auth", "token"])
    return None if done is None else done.returncode == 0


def reduce_auth(raw: str) -> dict[str, Any] | None:
    """Sortie JSON de `claude auth status` réduite à `loggedIn` et `authMethod` (le reste est jeté)."""
    try:
        doc = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(doc, dict):
        return None
    return {"loggedIn": bool(doc.get("loggedIn")), "authMethod": doc.get("authMethod")}


def claude_auth() -> dict[str, Any] | None:
    exe = shutil.which("claude")
    if exe is None:
        return None
    done = _run([exe, "auth", "status"])
    if done is None:
        return None
    return reduce_auth(done.stdout.decode("utf-8", errors="replace"))


def uv_check(repo: Path) -> tuple[bool | None, str]:
    """`.venv` suit-il `uv.lock` ? (`uv sync --dry-run --offline --locked` : rien téléchargé ni installé)"""
    done = _run(["uv", "sync", "--dry-run", "--offline", "--locked"], cwd=repo)
    if done is None:
        return None, "uv introuvable"
    text = (done.stdout + done.stderr).decode("utf-8", errors="replace").strip()
    if done.returncode != 0:
        return None, text.splitlines()[-1] if text else f"code {done.returncode}"
    if "Would make no changes" in text:
        return True, "rien à changer"
    return False, "; ".join(line for line in text.splitlines() if line.startswith(("Would", " +", " -")))[:300]


def python_check() -> str | None:
    from forever import spawn

    exe, env = spawn.current_interpreter()
    return spawn.probe_environment(exe, env)


def task(name: str) -> dict[str, str | None] | None:
    from forever.bridge import autostart

    done = autostart.schtasks(["/Query", "/TN", name, "/XML", "ONE"])
    if done.returncode != 0:
        return None
    return autostart.parse_task(autostart._decode(done.stdout))


def supervisor_pid(cache_dir: Path) -> int | None:
    from forever.bridge import autostart

    return autostart.supervisor_pid(cache_dir)


def bridge_pid(cache_dir: Path) -> int | None:
    from forever.bridge.lock import lock_holder

    return lock_holder(cache_dir)


def default_probes() -> Probes:
    from forever.bridge.install import REPO_ROOT

    return Probes(
        windows=sys.platform == "win32",
        system_drive=os.environ.get("SystemDrive", "C:"),
        repo=REPO_ROOT,
        gh_version=gh_version,
        gh_token=gh_token,
        claude_path=lambda: shutil.which("claude"),
        claude_auth=claude_auth,
        uv_check=uv_check,
        python_check=python_check,
        task=task,
        supervisor_pid=supervisor_pid,
        bridge_pid=bridge_pid,
    )
