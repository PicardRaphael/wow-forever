"""État du pont gardé entre deux lancements (P06a, bloc D) : messages déjà traités par session de l'addon, session de
la conversation « jeu », dernières réponses publiées. `<cache>/bridge/state.json`, écrit atomiquement."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPLIES_KEPT = 10
HANDLED_KEPT = 500


@dataclass
class BridgeState:
    path: Path
    handled: dict[str, list[int]] = field(default_factory=dict)
    session: str | None = None
    replies: list[dict[str, Any]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @classmethod
    def load(cls, path: Path) -> BridgeState:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = {}
        if not isinstance(doc, dict):
            doc = {}
        handled = {
            str(k): [int(i) for i in v if isinstance(i, int)]
            for k, v in (doc.get("handled") or {}).items()
            if isinstance(v, list)
        }
        replies = [r for r in doc.get("replies") or [] if isinstance(r, dict)]
        session = doc.get("session") if isinstance(doc.get("session"), str) else None
        return cls(path=path, handled=handled, session=session, replies=replies[-REPLIES_KEPT:])

    def seen(self, session: str, message_id: int) -> bool:
        return message_id in self.handled.get(session, [])

    def mark(self, session: str, message_id: int) -> None:
        with self._lock:
            ids = self.handled.setdefault(session, [])
            ids.append(message_id)
            del ids[:-HANDLED_KEPT]
            self.save()

    def put_reply(self, reply: dict[str, Any]) -> None:
        """Ajoute ou remplace la réponse (session, numéro) ; garde les dix dernières."""
        with self._lock:
            key = (reply.get("session"), reply.get("id"))
            self.replies = [r for r in self.replies if (r.get("session"), r.get("id")) != key] + [reply]
            self.replies = self.replies[-REPLIES_KEPT:]
            self.save()

    def set_session(self, session: str | None) -> None:
        with self._lock:
            self.session = session
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"handled": self.handled, "session": self.session, "replies": self.replies}
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
        os.replace(tmp, self.path)
