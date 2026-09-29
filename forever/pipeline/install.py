"""Installation d'une version candidate dans la version courante des données (T06b, décision D3) : squelette."""

from __future__ import annotations

from typing import Any

from forever.config import Deps
from forever.errors import ForeverError


class InstallRefusedError(ForeverError):
    def __init__(self, refused: list[Any]) -> None:
        super().__init__("install_refused", "Installation refusée.", "T06b")


def plan_install(deps: Deps, candidate: str) -> Any:
    raise NotImplementedError("T06b : forever install")


def apply_install(deps: Deps, candidate: str, *, motif: str, report: str | None = None, date: str | None = None) -> Any:
    raise NotImplementedError("T06b : forever install")


def render_install_report(plan: Any) -> str:
    raise NotImplementedError("T06b : forever install")
