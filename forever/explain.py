"""Explication d'une mécanique : entrée du registre, paramètres de la version courante, implémentation, provenance."""

from __future__ import annotations

from typing import TypedDict

from forever.config import Deps
from forever.provenance import Certainty, Provenance


class MechanicParameter(TypedDict):
    key: str
    value: object
    certainty: Certainty
    source: str


class MechanicExplanation(TypedDict):
    id: str
    category: str
    description: str
    forever: str
    status: str
    certainty: Certainty
    formula: str | None
    note: str | None
    parameters: list[MechanicParameter]
    implementations: list[str]
    sources: list[str]
    tests: list[str]
    provenance: Provenance


def explain_mechanic(deps: Deps, mechanic_id: str) -> MechanicExplanation:
    """Explication d'une mécanique du registre ; lève UnknownMechanicError, DataSchemaError ou DataIntegrityError."""
    raise NotImplementedError
