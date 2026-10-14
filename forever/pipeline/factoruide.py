"""Base de Factoruide en recoupement local (RX1, bloc A, décision 266).

Factoruide (`brouznouf/factoruide`, code MIT ; base `data/forever.sqlite.zst` sous GPL-2.0+ pour la part VMaNGOS,
données de Questie sans licence et de Wowhead Forever) est cloné hors du dépôt, épinglé à `FACTORUIDE_COMMIT`, et sa
base décompressée dans le cache (`<cache>/third_party/factoruide-db/forever.sqlite`). Elle sert seulement à mesurer
les écarts avec notre liste fusionnée (`forever quests diff --factoruide`) et à signaler une quête « vue seulement
chez Factoruide » (`suppose`, jamais placée dans une route) : rien n'en est recopié dans le dépôt ni livré dans un
guide. Lecture par `sqlite3` du stdlib, sans réseau ; base absente : statut `absent`, jamais téléchargée."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

FACTORUIDE_COMMIT = "f7da6da"  # commit épinglé du clone (décision 266)
DB_REL = Path("third_party") / "factoruide-db" / "forever.sqlite"
CLONE_REL = Path("third_party") / "factoruide"
SEEN_ONLY = "vue seulement chez Factoruide"
AVAILABLE = "available"
FACTORUIDE_STATUSES = ("available", "incomplete", "removed")


class FactoruideQuest(NamedTuple):
    id: int
    name: str | None
    level: int | None
    min_level: int | None
    status: str
    sources: tuple[str, ...]


class FactoruideDB(NamedTuple):
    status: str  # « present », « absent » ou « illisible »
    path: Path
    quests: dict[int, FactoruideQuest]
    provenance: dict[str, Any]  # commit, empreinte, date d'import
    notes: list[str]


def load_factoruide(cache_dir: Path) -> FactoruideDB:
    """Base de Factoruide du cache (`DB_REL`), lue en lecture seule."""
    raise NotImplementedError


def diff_factoruide(ours: set[int], db: FactoruideDB) -> dict[str, Any]:
    """Comptes par statut de Factoruide (connues des deux, de Factoruide seul, de nous seuls) et liste des quêtes
    `available` que seul Factoruide connaît."""
    raise NotImplementedError
