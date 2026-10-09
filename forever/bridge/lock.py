"""Verrou du pont (P06a, bloc D) : un pont à la fois, `<cache>/bridge/bridge.lock` (pid, lancement, dernier signe de
vie). Bibliothèque standard seulement : la surveillance du démarrage automatique (décision 226) le lit depuis
l'interpréteur de base."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from forever.timefmt import format_utc, parse_utc

REUSE_SLACK_S = 60.0


def lock_path(cache_dir: Path) -> Path:
    return cache_dir / "bridge" / "bridge.lock"


def lock_holder(cache_dir: Path, alive: Callable[[object], bool | None] | None = None) -> int | None:
    """pid du pont qui tient le verrou s'il tourne (ou si on ne peut pas savoir) ; None si libre ou mort."""
    if alive is None:
        from forever import spawn

        alive = spawn.pid_alive
    try:
        doc = json.loads(lock_path(cache_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    pid = doc.get("pid") if isinstance(doc, dict) else None
    if not isinstance(pid, int):
        return None
    return None if alive(pid) is False else pid


def pid_reused(doc: Any, created: Callable[[object], float | None] | None = None) -> bool:
    """Vrai si le pid de `doc` appartient aujourd'hui à un autre processus : créé après `doc["started_at"]`, ou
    inaccessible (processus du système ou d'un autre compte ; le pont et la surveillance tournent sous l'utilisateur
    et s'ouvrent toujours en lecture limitée). Cas : PC arrêté pendant que le pont tournait, verrou resté sur le
    disque, pid redonné à la session suivante. Faux si on ne peut pas le savoir (heure absente ou illisible)."""
    if not isinstance(doc, dict):
        return False
    try:
        started = parse_utc(str(doc["started_at"])).timestamp()
    except (KeyError, TypeError, ValueError):
        return False
    if created is None:
        from forever import spawn

        created = spawn.process_created
    try:
        born = created(doc.get("pid"))
    except PermissionError:
        return True
    return born is not None and born > started + REUSE_SLACK_S


def acquire_lock(
    cache_dir: Path, now: datetime, *, pid: int, alive: Callable[[object], bool | None] | None = None
) -> bool:
    """Prend le verrou du pont ; faux si un autre pont vivant le tient (un verrou mort est repris). Création
    exclusive : deux ponts lancés au même instant (surveillance et `forever bridge start`) ne le prennent pas tous
    les deux."""
    path = lock_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = format_utc(now)
    text = json.dumps({"pid": pid, "started_at": stamp, "seen_at": stamp})
    for _ in range(5):
        try:
            with path.open("x", encoding="utf-8") as f:
                f.write(text)
            return True
        except FileExistsError:
            pass
        doc = lock_info(cache_dir)
        if doc is None and _fresh(path):
            return False  # verrou en cours d'écriture par un autre pont
        holder = lock_holder(cache_dir, alive)
        reused = alive is None and pid_reused(doc)  # vérifié seulement avec les vrais processus
        if holder == pid:
            _write_atomic(path, text)
            return True
        if holder is not None and not reused:
            return False
        # verrou mort : renommé (un seul des ponts qui le reprennent y parvient), puis nouvelle création exclusive
        try:
            stale = path.with_name(f"{path.name}.{pid}.stale")
            os.replace(path, stale)
            stale.unlink(missing_ok=True)
        except OSError:
            pass
    return False


def _fresh(path: Path, seconds: float = 5.0) -> bool:
    try:
        return time.time() - path.stat().st_mtime < seconds
    except OSError:
        return False


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def touch_lock(cache_dir: Path, now: datetime, *, pid: int) -> None:
    """Dernier signe de vie (`seen_at`) du pont `pid` dans son verrou ; verrou d'un autre pont ou absent : rien."""
    path = lock_path(cache_dir)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(doc, dict) or doc.get("pid") != pid:
        return
    doc["seen_at"] = format_utc(now)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc), encoding="utf-8")
    os.replace(tmp, path)


def lock_info(cache_dir: Path) -> dict[str, Any] | None:
    """Contenu du verrou (pid, started_at, seen_at), ou None."""
    try:
        doc = json.loads(lock_path(cache_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def release_lock(cache_dir: Path, *, pid: int) -> None:
    path = lock_path(cache_dir)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if isinstance(doc, dict) and doc.get("pid") == pid:
        path.unlink(missing_ok=True)
