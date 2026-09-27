"""Lecteur minimal du registre des mécaniques (validation complète en T02)."""

from __future__ import annotations

from pathlib import Path

COVERED_STATUSES = frozenset({"teste", "valide-journal", "valide-jeu"})


def coverage(path: Path) -> str:
    """`<couvertes>/<total>` ; `0/0` si le registre est absent."""
    raise NotImplementedError
