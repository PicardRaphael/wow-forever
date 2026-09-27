"""Registre des mécaniques (`docs/MECHANICS_REGISTRY.yaml`) : lecture, validation, couverture.

Une référence de test prend la forme `tests/…/fichier.py::test_nom` ; la fonction doit exister (analyse `ast`, sans
import). Les fonctions du moteur citent leurs identifiants dans leur docstring : « Registre : A3, A4 »."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from forever.config import PACKAGE_DIR, REGISTRY_PATH, REPO_ROOT

STATUSES = ("absent", "modelise", "teste", "valide-journal", "valide-jeu")
COVERED_STATUSES = frozenset({"teste", "valide-journal", "valide-jeu"})
CERTAINTIES = frozenset({"certain", "probable", "suppose"})
FOREVER_VALUES = frozenset({"oui", "modifie", "inconnu"})
REQUIRED_FIELDS = ("id", "categorie", "description", "forever", "statut", "certitude", "sources", "tests")
ENGINE_DIR = PACKAGE_DIR / "engine"


class RegistryError(ValueError):
    """Registre absent, illisible ou mal formé."""


@dataclass(frozen=True)
class Mechanic:
    id: str
    category: str
    description: str
    forever: str
    status: str
    certainty: str
    sources: tuple[str, ...]
    tests: tuple[str, ...]
    tolerance: object
    formula: str | None
    note: str | None


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    total: int = 0


def load(path: Path) -> list[Mechanic]:
    """Entrées du registre ; lève RegistryError s'il est absent ou illisible."""
    raise NotImplementedError


def implementations(dirs: Sequence[Path], repo_root: Path) -> dict[str, list[str]]:
    """Identifiant -> fonctions du moteur qui le citent (`forever/engine/crit.py::crit_chance`)."""
    raise NotImplementedError


def validate(
    path: Path, repo_root: Path, *, strict: bool, engine_dirs: Sequence[Path] = (ENGINE_DIR,)
) -> ValidationReport:
    """Contrôle complet du registre ; en mode strict, une entrée `modelise` sans test est une erreur."""
    raise NotImplementedError


def find_entry(mechanics: Sequence[Mechanic], mechanic_id: str) -> Mechanic:
    """Entrée par identifiant (casse ignorée) ; lève UnknownMechanicError avec des suggestions."""
    raise NotImplementedError


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


def main(argv: Sequence[str], path: Path = REGISTRY_PATH, repo_root: Path = REPO_ROOT) -> int:
    """Contrôle en ligne de commande (`scripts/check_registry.py [--strict]`) : 0 si le registre est valide."""
    raise NotImplementedError
