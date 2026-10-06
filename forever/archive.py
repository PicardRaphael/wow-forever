"""Archivage des fichiers du client par build (T08d, bloc A, décision 182), lecture locale seulement.

`Cache/ADB/<locale>/DBCache.bin` et `Logs/Hotfix.log` sont réécrits par le client : le `DBCache.bin` de 1.60.1.70205
a été remplacé par celui de 70235 avant d'être copié, et ses correctifs du serveur sont perdus. Ce module les copie
dans `<cache>/dbcache/<build>/` dès qu'ils changent, sans jamais écrire dans le dossier du client ni rien effacer :

- `DBCache.bin` est lu en entier et contrôlé par `dbcache.parse_dbcache` avant la copie (un fichier tronqué, copié
  pendant une écriture du client, n'est pas archivé et sera relu au passage suivant) ; il est rangé par le build de son
  en-tête ; un contenu différent pour le même build garde l'ancien sous `DBCache-<sha12>.bin` ;
- `Hotfix.log` grossit pendant une session du client et il est réécrit au démarrage suivant : une copie par session,
  reconnue à sa première ligne, remplacée tant que le fichier ne fait que grossir ; le build est celui du client au
  début de la session (journal des versions), sinon celui de `.build.info` au moment de la copie ;
- `index.json` de chaque build liste les copies (sha256, taille, dates, entrées, poussée maximale, source du build).

L'état du dernier passage (taille et date des fichiers vivants, échecs de lecture) est gardé dans
`<cache>/dbcache/state.json` : un fichier inchangé n'est pas relu. Aucun chiffre de jeu ici."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.errors import DataSchemaError
from forever.pipeline import dbcache, hotfixes
from forever.pipeline.client_builds import JOURNAL_NAME, load_builds, read_build_info, record_build, version_at
from forever.timefmt import format_utc

ARCHIVE_DIR = "dbcache"
STATE_NAME = "state.json"
INDEX_NAME = "index.json"
CURRENT = "DBCache.bin"
FAILURE_ALERT = 3  # passages illisibles d'affilée avant une ligne de démarrage (paramètre de l'outil)


class ArchivedCopy(NamedTuple):
    """Une copie faite (ou déjà présente) d'un fichier du client."""

    kind: str  # "dbcache" | "hotfix_log"
    build: str  # "70235" : en-tête de DBCache.bin, ou build du client au début de la session du journal
    path: Path
    sha256: str
    size: int
    file_mtime: str
    copied_at: str
    new: bool


class ArchiveResult(NamedTuple):
    """Résultat d'un passage : copies examinées (`new` : copie faite), erreurs (jamais levées), build du client
    inscrit au journal."""

    copies: list[ArchivedCopy]
    errors: list[str]
    client_build: str | None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_atomic(path: Path, data: bytes) -> None:
    """Écriture en octets par un fichier temporaire du même dossier, puis remplacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _write_json(path: Path, doc: Any) -> None:
    _write_atomic(path, (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _mtime(path: Path) -> str:
    return format_utc(datetime.fromtimestamp(path.stat().st_mtime, tz=UTC))


def _stamp(path: Path) -> dict[str, int]:
    st = path.stat()
    return {"size": st.st_size, "mtime": st.st_mtime_ns}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _message(exc: Exception) -> str:
    return exc.message if isinstance(exc, DataSchemaError) else str(exc)


def _dbcache_counts(cache: dbcache.DBCache) -> dict[str, Any]:
    pushes = [e.push_id for e in cache.entries if dbcache.entry_kind(e) == "push"]
    return {"entries": len(cache.entries), "max_push": max(pushes) if pushes else None}


class _Index:
    """`index.json` d'un build ; une copie de `DBCache.bin` posée sans index (décision 176) y est adoptée."""

    def __init__(self, folder: Path, now: str) -> None:
        self.path = folder / INDEX_NAME
        doc = _read_json(self.path)
        self.copies: list[dict[str, Any]] = [c for c in doc.get("copies", []) if isinstance(c, dict)]
        legacy = folder / CURRENT
        if legacy.is_file() and not any(c["kind"] == "dbcache" and c["file"] == CURRENT for c in self.copies):
            raw = legacy.read_bytes()
            entry: dict[str, Any] = {
                "kind": "dbcache",
                "file": CURRENT,
                "sha256": _sha(raw),
                "size": len(raw),
                "file_mtime": _mtime(legacy),
                "copied_at": None,
                "note": f"copie trouvée sans index, adoptée le {now}",
            }
            try:
                entry.update(_dbcache_counts(dbcache.parse_dbcache(raw)))
            except DataSchemaError:
                pass
            self.copies.append(entry)

    def of(self, kind: str) -> list[dict[str, Any]]:
        return [c for c in self.copies if c["kind"] == kind]

    def save(self) -> None:
        _write_json(self.path, {"schema_version": 1, "copies": self.copies})


def _copy(kind: str, build: str, path: Path, entry: dict[str, Any], new: bool) -> ArchivedCopy:
    return ArchivedCopy(
        kind, build, path, entry["sha256"], entry["size"], entry["file_mtime"], entry.get("copied_at") or "", new
    )


def _archive_dbcache(live: Path, root: Path, raw: bytes, cache: dbcache.DBCache, now: str) -> ArchivedCopy:
    build = str(cache.build)
    folder = root / build
    index = _Index(folder, now)
    sha = _sha(raw)
    for entry in index.of("dbcache"):
        if entry["sha256"] == sha:
            return _copy("dbcache", build, folder / entry["file"], entry, False)
    current = folder / CURRENT
    if current.is_file():
        old = next(c for c in index.of("dbcache") if c["file"] == CURRENT)
        kept = folder / f"DBCache-{old['sha256'][:12]}.bin"
        os.replace(current, kept)
        old["file"] = kept.name
    _write_atomic(current, raw)
    entry = {
        "kind": "dbcache",
        "file": CURRENT,
        "sha256": sha,
        "size": len(raw),
        "file_mtime": _mtime(live),
        "copied_at": now,
        **_dbcache_counts(cache),
    }
    index.copies.append(entry)
    index.save()
    return _copy("dbcache", build, current, entry, True)


def _session_start(raw: bytes, live: Path) -> datetime:
    """Début de la session du client : première ligne datée du journal (heure locale), sinon la date du fichier."""
    first = raw.split(b"\n", 1)[0].decode("utf-8", errors="replace")
    lines = hotfixes.parse_hotfix_log(first, hotfixes.log_year(live))
    if lines:
        return datetime.fromisoformat(lines[0].at).astimezone(UTC)
    return datetime.fromtimestamp(live.stat().st_mtime, tz=UTC)


def _archive_hotfix_log(deps: Deps, live: Path, root: Path, raw: bytes, client: str | None, now: str) -> ArchivedCopy:
    start = _session_start(raw, live)
    version = version_at(load_builds(deps.cache_dir), start)
    source = JOURNAL_NAME
    if version is None:
        version, source = client, ".build.info"
    if version is None:
        raise DataSchemaError("Hotfix.log : build du client inconnu (ni journal des versions ni .build.info).")
    build = version.rsplit(".", 1)[-1]
    folder = root / build
    index = _Index(folder, now)
    sha = _sha(raw)
    head_sha = _sha(raw.split(b"\n", 1)[0])
    logs = index.of("hotfix_log")
    for entry in logs:
        if entry["sha256"] == sha:
            return _copy("hotfix_log", build, folder / entry["file"], entry, False)
    target: dict[str, Any] | None = None
    for entry in logs:
        if entry.get("head_sha") != head_sha:
            continue
        archived = (folder / entry["file"]).read_bytes()
        if raw.startswith(archived):
            target = entry  # le journal a grossi : la copie de la session est remplacée
            break
        if archived.startswith(raw):
            return _copy("hotfix_log", build, folder / entry["file"], entry, False)
    if target is None:
        stem = f"Hotfix-{start:%Y%m%dT%H%M%SZ}"
        name, n = f"{stem}.log", 2
        taken = {c["file"] for c in logs}
        while name in taken or (folder / name).exists():
            name, n = f"{stem}-{n}.log", n + 1
        target = {"kind": "hotfix_log", "file": name, "head_sha": head_sha, "session_start": format_utc(start)}
        index.copies.append(target)
    target.update(
        {"sha256": sha, "size": len(raw), "file_mtime": _mtime(live), "copied_at": now, "build_source": source}
    )
    _write_atomic(folder / target["file"], raw)
    index.save()
    return _copy("hotfix_log", build, folder / target["file"], target, True)


def archive_client_files(
    deps: Deps, *, locale: str = "enUS", read_bytes: Callable[[Path], bytes] = Path.read_bytes
) -> ArchiveResult:
    """Un passage d'archivage ; ne lève jamais (les erreurs sont dans le résultat)."""
    copies: list[ArchivedCopy] = []
    errors: list[str] = []
    wow = deps.wow_dir
    if wow is None or not wow.is_dir():
        return ArchiveResult(copies, errors, None)
    root = deps.cache_dir / ARCHIVE_DIR
    state_path = root / STATE_NAME
    state = _read_json(state_path)
    now = format_utc(deps.now())
    client: str | None = None
    try:
        seen = read_build_info(wow)
        if seen is not None:
            client = seen.build
            record_build(deps.cache_dir, seen)  # le build vu est inscrit même sans journal de combat
    except Exception as exc:  # noqa: BLE001 : l'archivage ne doit jamais échouer
        errors.append(f"journal des versions du client : {_message(exc)}")

    live = wow.joinpath(*(part.format(locale=locale) for part in dbcache.DBCACHE_PATH))
    try:
        if live.is_file():
            stamp = _stamp(live)
            if state.get("dbcache") != stamp:
                try:
                    raw = read_bytes(live)
                    parsed = dbcache.parse_dbcache(raw)
                except (OSError, DataSchemaError) as exc:
                    # jamais marqué lu : le fichier est relu au passage suivant, même inchangé
                    state["dbcache_failures"] = int(state.get("dbcache_failures", 0)) + 1
                    errors.append(f"DBCache.bin non archivé, relu au prochain passage : {_message(exc)}")
                else:
                    copies.append(_archive_dbcache(live, root, raw, parsed, now))
                    state["dbcache"] = stamp
                    state["dbcache_failures"] = 0
    except Exception as exc:  # noqa: BLE001
        errors.append(f"DBCache.bin : {_message(exc)}")

    log = wow.joinpath(*hotfixes.HOTFIX_LOG)
    try:
        if log.is_file():
            stamp = _stamp(log)
            if state.get("hotfix_log") != stamp:
                raw = read_bytes(log)
                if raw:
                    copies.append(_archive_hotfix_log(deps, log, root, raw, client, now))
                state["hotfix_log"] = stamp
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Hotfix.log non archivé : {_message(exc)}")

    try:
        _write_json(state_path, state)
    except OSError as exc:
        errors.append(f"état de l'archivage : {exc}")
    return ArchiveResult(copies, errors, client)


def archived_dbcache(cache_dir: Path, build: str) -> Path | None:
    """Copie la plus récente du `DBCache.bin` d'un build (`70235`), ou None."""
    path = cache_dir / ARCHIVE_DIR / build / CURRENT
    return path if path.is_file() else None


def archive_line(cache_dir: Path) -> str | None:
    """Ligne de démarrage quand `DBCache.bin` est illisible depuis `FAILURE_ALERT` passages ; None sinon."""
    try:
        failures = int(_read_json(cache_dir / ARCHIVE_DIR / STATE_NAME).get("dbcache_failures", 0))
    except (TypeError, ValueError):
        return None
    if failures < FAILURE_ALERT:
        return None
    return f"Archivage : DBCache.bin illisible depuis {failures} passages (`forever watch` pour le détail)"
