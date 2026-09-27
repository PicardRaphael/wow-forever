"""Rapport Markdown d'un changement de données (futur corps de PR de T08), déterministe à horloge fixe."""

from __future__ import annotations

from forever.pipeline.diff import VersionDiff
from forever.pipeline.verify import VerifyReport


def render_report(diff: VersionDiff, verify: VerifyReport | None = None) -> str:
    """Titre « data: A → B », résumé chiffré, sections Talents / Sorts / Fichiers (tableaux), vérification,
    hypothèses, ligne de provenance en dernier."""
    raise NotImplementedError
