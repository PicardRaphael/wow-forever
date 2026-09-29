"""Profil joueur minimal, hors du dépôt (T06b, décision D5) : squelette."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forever.config import Deps


def profile_path(environ: Mapping[str, str] = os.environ) -> Path:
    raise NotImplementedError("T06b : profil")


def load_profile(path: Path) -> Any:
    raise NotImplementedError("T06b : profil")


def set_character(deps: Deps, name: str, **fields: Any) -> Any:
    raise NotImplementedError("T06b : profil")


def use(deps: Deps, name: str) -> Any:
    raise NotImplementedError("T06b : profil")


def remove(deps: Deps, name: str) -> Any:
    raise NotImplementedError("T06b : profil")


def read_profile(deps: Deps, name: str | None = None) -> Any:
    raise NotImplementedError("T06b : profil")
