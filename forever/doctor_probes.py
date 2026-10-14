"""Sondes de `forever doctor` (LN1, bloc D) : sous-processus locaux seulement, jamais de réseau."""

from __future__ import annotations

from typing import Any

from forever.doctor import Probes


def reduce_auth(raw: str) -> dict[str, Any] | None:
    """Sortie JSON de `claude auth status` réduite à `loggedIn` et `authMethod` (le reste est jeté)."""
    raise NotImplementedError


def default_probes() -> Probes:
    raise NotImplementedError
