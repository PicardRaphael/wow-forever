"""Comparaison de deux versions de données (dépôt ou candidate) : talents, sorts, fichiers.

Champs comparés : talents `name`, `tree`, `tier`, `col`, `max`, `prereq`, puis chaque rang (`ranks[i]`, à partir
de 1) ; sorts, chaque champ de `rank_format` de chaque rang (`ranks[i].mana`), un rang en plus ou en moins
(`ranks[i]`). Ne sont pas comparés : descriptions, identifiants de sorts, noms français, certitudes, notes."""

from __future__ import annotations

from typing import Literal, TypedDict

from forever.config import Deps
from forever.provenance import Provenance
from forever.store import VersionData

TALENT_FIELDS = ("name", "tree", "tier", "col", "max", "prereq")


class Change(TypedDict):
    kind: Literal["talent", "spell", "file"]
    key: str
    change: Literal["added", "removed", "modified"]
    field: str | None
    old: object
    new: object


class VersionDiff(TypedDict):
    a: str
    b: str
    changes: list[Change]
    counts: dict[str, int]
    provenance: Provenance


def compare_data(a: VersionData, b: VersionData) -> list[Change]:
    """Changements de `a` vers `b`, dans un ordre stable (fichiers, talents, sorts ; ordre des données)."""
    raise NotImplementedError


def diff_versions(deps: Deps, a: str, b: str) -> VersionDiff:
    """`a`, `b` : identifiant de version du dépôt ou chemin d'une candidate ; intégrité exigée des deux côtés."""
    raise NotImplementedError
