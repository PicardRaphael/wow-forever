"""Base de Factoruide en recoupement local (RX1, bloc A, décision 266).

Factoruide (`brouznouf/factoruide`, code MIT ; base `data/forever.sqlite.zst` sous GPL-2.0+ pour la part VMaNGOS,
données de Questie sans licence et de Wowhead Forever) est cloné hors du dépôt, épinglé à `FACTORUIDE_COMMIT`, et sa
base décompressée dans le cache (`<cache>/third_party/factoruide-db/forever.sqlite`). Elle sert seulement à mesurer
les écarts avec notre liste fusionnée (`forever quests diff --factoruide`) et à signaler une quête « vue seulement
chez Factoruide » (`suppose`, jamais placée dans une route) : rien n'en est recopié dans le dépôt ni livré dans un
guide. Lecture par `sqlite3` du stdlib, sans réseau ; base absente : statut `absent`, jamais téléchargée."""

from __future__ import annotations

import hashlib
import sqlite3
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


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _int(v: Any) -> int | None:
    return v if isinstance(v, int) else None


def load_factoruide(cache_dir: Path) -> FactoruideDB:
    """Base de Factoruide du cache (`DB_REL`), lue en lecture seule."""
    path = cache_dir / DB_REL
    provenance: dict[str, Any] = {"commit": FACTORUIDE_COMMIT, "sha256": None, "imported_at": None}
    if not path.is_file():
        note = f"base de Factoruide absente ({path}) : aucun recoupement (jamais téléchargée)"
        return FactoruideDB("absent", path, {}, provenance, [note])
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT id, name, level, min_level, status, sources FROM m_quest").fetchall()
            runs = con.execute("SELECT max(imported_at) FROM import_run").fetchone()
        finally:
            con.close()
    except sqlite3.Error as exc:
        return FactoruideDB("illisible", path, {}, provenance, [f"base de Factoruide illisible ({path}) : {exc}"])
    quests: dict[int, FactoruideQuest] = {}
    for quest_id, name, level, min_level, status, sources in rows:
        if not isinstance(quest_id, int):
            continue
        quests[quest_id] = FactoruideQuest(
            quest_id,
            name if isinstance(name, str) else None,
            _int(level),
            _int(min_level),
            status if isinstance(status, str) else "",
            tuple(x for x in str(sources or "").split(",") if x),
        )
    provenance.update(sha256=_sha(path), imported_at=runs[0] if runs else None)
    return FactoruideDB("present", path, quests, provenance, [])


def diff_factoruide(ours: set[int], db: FactoruideDB) -> dict[str, Any]:
    """Comptes par statut de Factoruide (connues des deux, de Factoruide seul, de nous seuls) et liste des quêtes
    `available` que seul Factoruide connaît."""
    counts = {s: {"both": 0, "factoruide_only": 0} for s in FACTORUIDE_STATUSES}
    seen_only: list[dict[str, Any]] = []
    for quest_id, q in sorted(db.quests.items()):
        bucket = counts.setdefault(q.status, {"both": 0, "factoruide_only": 0})
        if quest_id in ours:
            bucket["both"] += 1
        else:
            bucket["factoruide_only"] += 1
            if q.status == AVAILABLE:
                seen_only.append({"id": quest_id, "name": q.name, "level": q.level, "sources": list(q.sources)})
    return {
        "status": db.status,
        "counts": counts if db.status == "present" else {},
        "ours_only": len(ours - set(db.quests)) if db.status == "present" else None,
        "seen_only": seen_only,
        "provenance": db.provenance,
        "notes": db.notes,
    }
