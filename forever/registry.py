"""Lecteur minimal du registre des mécaniques (validation complète en T02)."""

from __future__ import annotations

from pathlib import Path

import yaml

COVERED_STATUSES = frozenset({"teste", "valide-journal", "valide-jeu"})


def coverage(path: Path) -> str:
    """`<couvertes>/<total>` ; `0/0` si le registre est absent."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return "0/0"
    mechanics = data.get("mechanics") if isinstance(data, dict) else None
    if not isinstance(mechanics, list):
        return "0/0"
    covered = sum(1 for m in mechanics if isinstance(m, dict) and m.get("statut") in COVERED_STATUSES)
    return f"{covered}/{len(mechanics)}"
