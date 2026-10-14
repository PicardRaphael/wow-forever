"""`forever doctor` (LN1, bloc D, décision 271) : contrôle de toute l'installation, sans réseau, chaque problème avec
sa correction. Contrôles purs : tout ce qui touche au système (sous-processus, tâches planifiées, processus) passe par
des sondes injectées (`forever/doctor_probes.py`)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps

STATUSES = ("ok", "warn", "fail", "unknown", "info")


@dataclass(frozen=True)
class Check:
    """Un contrôle : identifiant stable, état, constat et correction (commande ou geste précis)."""

    id: str
    status: str
    finding: str
    fix: str | None = None

    def as_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class Probes:
    """Sondes du système, injectées (tests : simulées ; production : `doctor_probes.default_probes`)."""

    windows: bool
    system_drive: str
    repo: Path
    gh_version: Callable[[], str | None]
    gh_token: Callable[[], bool | None]
    claude_path: Callable[[], str | None]
    claude_auth: Callable[[], dict[str, Any] | None]
    uv_check: Callable[[Path], tuple[bool | None, str]]
    python_check: Callable[[], str | None]
    task: Callable[[str], dict[str, str | None] | None]
    supervisor_pid: Callable[[Path], int | None]
    bridge_pid: Callable[[Path], int | None]


def run_checks(deps: Deps, probes: Probes) -> list[Check]:
    raise NotImplementedError


def exit_code(checks: list[Check]) -> int:
    raise NotImplementedError
