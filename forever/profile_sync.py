"""AMI1 : profil rempli depuis ForeverLogger (squelette)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from forever.config import Deps


def sync_from_logger(deps: Deps, *, set_char: Callable[..., Any] | None = None) -> list[dict[str, Any]]:
    raise NotImplementedError
