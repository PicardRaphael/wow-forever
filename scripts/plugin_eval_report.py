"""Rapport d'un passage de `claude plugin eval` sur plugin/evals/ (T06, décision D10) : seuils de la tranche et chiffres
signalés par le contrôle des chiffres, pour mesurer ses fausses alertes.

    uv run python scripts/plugin_eval_report.py <résultat JSON de claude plugin eval> [--evals plugin/evals]

Lecture locale seulement (résultat JSON et traces gardées par --keep-temp), aucun accès réseau."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

THRESHOLDS: dict[str, float] = {}


def load_cases(evals_dir: Path) -> dict[str, dict[str, str]]:
    """Cas de la suite : nom -> polarité (positif, negatif) et catégorie, lus dans les tags de prompt.md."""
    raise NotImplementedError


def metrics(result: dict[str, Any], cases: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Taux de réussite par critère de D10 sur tous les passages du bras « with »."""
    raise NotImplementedError


def flagged_numbers(result: dict[str, Any], base: Path) -> list[dict[str, Any]]:
    """Chiffres de jeu sans source relevés dans les traces gardées (même règle que le hook Stop) ; chemins relatifs
    résolus depuis `base`."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
