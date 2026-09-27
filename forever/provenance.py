"""Bloc provenance, présent dans chaque résultat d'outil (CLI et MCP)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypedDict

from forever.config import Deps
from forever.errors import ErrorInfo, ForeverError
from forever.freshness import Freshness

Certainty = Literal["certain", "probable", "suppose"]

LEGACY_CERTAINTY: dict[str, Certainty] = {"FC": "certain", "FS": "probable", "PC": "suppose", "EST": "suppose"}

PROVENANCE_KEYS = (
    "game_version",
    "data_sha",
    "generated_at",
    "freshness",
    "certainty",
    "assumptions",
    "registry_coverage",
)


class Provenance(TypedDict):
    game_version: str
    data_sha: str
    generated_at: str
    freshness: Freshness
    certainty: Certainty
    assumptions: list[str]
    registry_coverage: str


class ErrorPayload(TypedDict):
    error: ErrorInfo
    provenance: Provenance


def make_provenance(
    deps: Deps,
    *,
    game_version: str,
    data_sha: str,
    freshness: Freshness,
    certainty: Certainty,
    assumptions: Iterable[str],
) -> Provenance:
    raise NotImplementedError


def validate_provenance(obj: object) -> list[str]:
    """Liste des écarts au schéma (vide si le bloc est valide)."""
    raise NotImplementedError


def format_provenance_line(p: Provenance) -> str:
    raise NotImplementedError


def min_certainty(values: Iterable[Certainty]) -> Certainty:
    raise NotImplementedError


def error_payload(deps: Deps, err: ForeverError) -> ErrorPayload:
    """Erreur + provenance calculée sans contrôle d'intégrité ni réseau."""
    raise NotImplementedError
