"""Mémoire de traduction des guides RestedXP (FR1) : gabarit anglais -> gabarit français, avec origine et date.

Hors dépôt (décisions 268 et 277, question Q4) : `~/.forever/rxp_fr/memoire.json`, à côté du profil, sauvegardée par
`forever backup`. Origines, de la plus faible à la plus forte : `traduit` (traduit depuis l'anglais dans une session
Claude), `restedxp` (relevé dans un guide que RestedXP a traduit), `manuel` (corrigé par l'utilisateur, jamais
écrasé). Une traduction qui perd ou double un jeton `{n}` est refusée."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.rxp_fr.tokens import fill, placeholders

SCHEMA_VERSION = 1
RANK = {"traduit": 1, "restedxp": 2, "manuel": 3}
TITLE = "titre|"  # espace des noms de guide et de groupe (en-têtes), distinct des phrases d'étape
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


def memory_path(deps: Deps) -> Path:
    from forever.profile import resolve_path

    return resolve_path(deps).parent / "rxp_fr" / "memoire.json"


@dataclass(frozen=True)
class Entry:
    fr: str
    origin: str
    date: str


def same_slots(english: str, french: str) -> bool:
    """La traduction garde chaque jeton de l'anglais une fois, et se remplit sans erreur."""
    en, fr = placeholders(english.removeprefix(TITLE)), placeholders(french)
    if sorted(fr) != sorted(en) or len(set(fr)) != len(fr):
        return False
    try:
        fill(french, [""] * max(en, default=0))
    except ValueError:
        return False
    return True


class Memory:
    def __init__(self, entries: Mapping[str, Entry] | None = None) -> None:
        self.entries: dict[str, Entry] = dict(entries or {})

    def get(self, english: str) -> Entry | None:
        return self.entries.get(normalize(english))

    def put(self, english: str, french: str, origin: str, *, date: str) -> bool:
        """Range une traduction ; False si refusée (jeton perdu, entrée plus forte déjà là)."""
        key = normalize(english)
        if origin not in RANK or not french.strip() or not same_slots(key, french):
            return False
        old = self.entries.get(key)
        if old is not None and RANK[origin] < RANK.get(old.origin, 0):
            return False
        self.entries[key] = Entry(french, origin, date)
        return True

    def origins(self) -> Counter[str]:
        return Counter(e.origin for e in self.entries.values())

    @classmethod
    def load(cls, path: Path) -> Memory:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        raw = doc.get("entries") if isinstance(doc, dict) else None
        entries: dict[str, Entry] = {}
        for key, value in (raw or {}).items():
            if isinstance(value, dict) and isinstance(value.get("fr"), str) and value.get("origin") in RANK:
                entries[normalize(key)] = Entry(value["fr"], value["origin"], str(value.get("date") or ""))
        return cls(entries)

    def save(self, path: Path) -> None:
        doc: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "note": "Mémoire de traduction des guides RestedXP (usage personnel, hors dépôt, FR1).",
            "entries": {k: {"fr": e.fr, "origin": e.origin, "date": e.date} for k, e in sorted(self.entries.items())},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, path)
