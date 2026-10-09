"""Journal du pont (P06a, bloc D, décision 212) : `<cache>/bridge/journal/<AAAA-MM-JJ>.jsonl`, un objet par ligne
(`at`, `event`, champs) ; jamais de pixel ni d'image."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from forever.timefmt import format_utc

_FORBIDDEN = frozenset({"pixels", "image", "bgra"})


class Journal:
    def __init__(self, directory: Path, now: Callable[[], datetime]) -> None:
        self.directory = directory
        self.now = now
        self._lock = threading.Lock()

    def write(self, event: str, **fields: Any) -> None:
        when = self.now()
        line = {"at": format_utc(when), "event": event}
        line.update({k: v for k, v in fields.items() if k not in _FORBIDDEN})
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{when:%Y-%m-%d}.jsonl"
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    def recent(self, event: str, days: int = 7) -> list[dict[str, Any]]:
        """Lignes `event` des `days` derniers fichiers du journal, de la plus ancienne à la plus récente."""
        files = sorted(self.directory.glob("*.jsonl"))[-days:] if self.directory.is_dir() else []
        out = []
        for path in files:
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get("event") == event:
                    out.append(entry)
        return out

    def tail(self, count: int = 5) -> list[dict[str, Any]]:
        """Dernières lignes du journal le plus récent."""
        files = sorted(self.directory.glob("*.jsonl")) if self.directory.is_dir() else []
        if not files:
            return []
        lines = files[-1].read_text(encoding="utf-8").splitlines()[-count:]
        return [json.loads(line) for line in lines if line.strip()]
