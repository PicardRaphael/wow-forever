"""Sauvegarde et restauration de ce qui n'est pas sur GitHub (LN1, bloc E, décision 271).

Contenu : le profil joueur ; les SavedVariables (`WTF/Account/*/SavedVariables/*.lua` et
`WTF/Account/*/*/*/SavedVariables/*.lua`) et `WTF/Config.wtf` de l'installation lue (et de la bêta tant qu'elle
existe) ; les réglages du pont et le dossier de la conversation « addons » (son dépôt git local compris) ; les
attentes, l'état et la configuration de `forever update` ; le journal des versions du client ; le dernier instantané
des mesures. Jamais un jeton ni `.credentials.json`.

Forme : un dossier daté `<racine>/<AAAA-MM-JJTHHMMSS>/` (copie simple, lisible à la main) et son `manifest.json`
(chemin d'origine, empreinte, taille, produit et dossier de l'installation), écrit dans un dossier `.partiel` renommé
à la fin ; 14 gardées. Racine : `FOREVER_BACKUP_DIR`, sinon un disque fixe hors système (d'abord celui dont le nom
contient « sauvegarde » ou « backup »), sinon OneDrive connecté, sinon Documents avec un avertissement : jamais le
disque système par défaut (la remise à zéro du PC du 12 octobre a effacé tout C:).

Lecture et écriture sur disque seulement, jamais par le réseau."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError, PathNotFoundError
from forever.installs import ROLE_BETA, product_of, same_folder, survey
from forever.timefmt import format_utc

BACKUP_SUBDIR = Path("WoW Forever") / "sauvegardes"
KEEP = 14
MIN_FREE = 1 << 30  # 1 Go libre au moins sur un disque de sauvegarde
DAILY_EVERY = timedelta(hours=24)
STAMP_FORMAT = "%Y-%m-%dT%H%M%S"
MANIFEST = "manifest.json"
MANIFEST_NOTE = "Sauvegarde de forever (LN1)"
_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{6}(-\d+)?$")
PARTIAL_SUFFIX = ".partiel"
KINDS = ("profile", "wtf", "bridge", "update", "cache")
NEVER_COPIED = (".credentials.json",)
BACKUP_WORDS = ("sauvegarde", "backup")
SYSTEM_WARNING = (
    "sauvegardes sur le disque système (Documents) : aucun autre disque fixe ni OneDrive connecté ; une remise à "
    "zéro du PC les effacerait. Poser FOREVER_BACKUP_DIR vers un autre disque."
)


@dataclass(frozen=True)
class DriveInfo:
    """Disque fixe : racine, nom de volume, octets libres, disque système ou non."""

    root: Path
    label: str
    free: int
    system: bool


@dataclass(frozen=True)
class BackupInfo:
    stamp: str
    path: Path
    created_at: str
    reason: str
    files: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "stamp": self.stamp,
            "path": str(self.path),
            "created_at": self.created_at,
            "reason": self.reason,
            "files": self.files,
        }


@dataclass(frozen=True)
class RestorePlan:
    """Restauration prévue ou faite : fichiers écrits (origine), fichiers laissés de côté et pourquoi."""

    stamp: str
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    before: Path | None = None  # sauvegarde de l'état courant faite avant l'écrasement
    applied: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "stamp": self.stamp,
            "written": self.written,
            "skipped": self.skipped,
            "before": str(self.before) if self.before is not None else None,
            "applied": self.applied,
        }


@dataclass(frozen=True)
class _Item:
    kind: str
    origin: Path
    path: str  # chemin dans la sauvegarde (barres obliques)
    product: str | None = None
    folder: str | None = None
    rel: str | None = None  # chemin sous le dossier de l'installation (SavedVariables)


# --- Racine --------------------------------------------------------------------------------------------------------


def backup_root(
    environ: Mapping[str, str], drives: Sequence[DriveInfo], onedrive: Path | None, documents: Path
) -> tuple[Path, str | None]:
    """(racine des sauvegardes, avertissement ou None) : `FOREVER_BACKUP_DIR`, sinon un disque fixe hors système avec
    au moins 1 Go libre (d'abord celui dont le nom contient « sauvegarde » ou « backup », puis dans l'ordre des
    lettres), sinon OneDrive connecté, sinon Documents avec un avertissement."""
    configured = environ.get("FOREVER_BACKUP_DIR", "").strip()
    if configured:
        return Path(configured), None
    usable = sorted((d for d in drives if not d.system and d.free >= MIN_FREE), key=lambda d: str(d.root).upper())
    named = [d for d in usable if any(word in d.label.casefold() for word in BACKUP_WORDS)]
    for chosen in (*named, *usable):
        return chosen.root / BACKUP_SUBDIR, None
    if onedrive is not None:
        return onedrive / BACKUP_SUBDIR, None
    return documents / BACKUP_SUBDIR, SYSTEM_WARNING


def drive_infos(roots: Sequence[Path], environ: Mapping[str, str]) -> list[DriveInfo]:
    """Nom de volume, place libre et disque système de chaque disque fixe donné (Windows)."""
    system = environ.get("SystemDrive", "C:").rstrip("\\/").upper()
    found = []
    for root in roots:
        label = ""
        if sys.platform == "win32":
            import ctypes

            buffer = ctypes.create_unicode_buffer(261)
            if ctypes.windll.kernel32.GetVolumeInformationW(str(root), buffer, 261, None, None, None, None, 0):
                label = buffer.value
        try:
            free = shutil.disk_usage(root).free
        except OSError:
            continue
        found.append(DriveInfo(root, label, free, str(root).rstrip("\\/").upper() == system))
    return found


def onedrive_folder(environ: Mapping[str, str]) -> Path | None:
    """Dossier OneDrive d'un compte connecté (`HKCU\\Software\\Microsoft\\OneDrive\\Accounts\\*\\UserFolder`
    existant) ; None sinon. Rien n'est lu si la variable `OneDrive` est absente (tests, autre système)."""
    if sys.platform != "win32" or not environ.get("OneDrive"):
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\OneDrive\Accounts") as accounts:
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(accounts, index)
                except OSError:
                    return None
                index += 1
                try:
                    with winreg.OpenKey(accounts, name) as account:
                        folder = Path(winreg.QueryValueEx(account, "UserFolder")[0])
                except OSError:
                    continue
                if folder.is_dir():
                    return folder
    except OSError:
        return None


def default_root(deps: Deps) -> tuple[Path, str | None]:
    """Racine des sauvegardes pour ces dépendances (disques de `deps.drives`, OneDrive et Documents de
    `deps.environ`)."""
    environ = deps.environ
    profile = environ.get("USERPROFILE") or environ.get("HOME")
    documents = (Path(profile) if profile else deps.cache_dir.parent) / "Documents"
    return backup_root(environ, drive_infos(deps.drives(), environ), onedrive_folder(environ), documents)


# --- Contenu -------------------------------------------------------------------------------------------------------


def _files(folder: Path) -> Iterator[Path]:
    if folder.is_dir():
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.name not in NEVER_COPIED:
                yield path


def _install_folders(deps: Deps) -> list[Path]:
    """Installation lue, puis la bêta si elle est ailleurs (tant qu'elle existe)."""
    folders = [deps.wow_dir] if deps.wow_dir is not None and deps.wow_dir.is_dir() else []
    try:
        _, found = survey(deps.environ, drives=deps.drives, cache_dir=deps.cache_dir, data_dir=deps.data_dir)
    except Exception:  # noqa: BLE001 : la sauvegarde ne dépend pas de la découverte
        found = []
    for install in found:
        if install.role == ROLE_BETA and not any(same_folder(install.folder, f) for f in folders):
            folders.append(install.folder)
    return folders


def _profile_file(deps: Deps) -> Path:
    from forever.profile import resolve_path

    return resolve_path(deps)


def _bridge_project(cache_dir: Path) -> Path | None:
    try:
        doc = json.loads((cache_dir / "bridge" / "addons" / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    source = doc.get("source") if isinstance(doc, dict) else None
    return Path(source) if isinstance(source, str) and source else None


def collect(deps: Deps) -> list[_Item]:
    """Fichiers à sauvegarder (ceux qui existent)."""
    items: list[_Item] = []
    profile = _profile_file(deps)
    if profile.is_file():
        items.append(_Item("profile", profile, f"profil/{profile.name}"))
    for folder in _install_folders(deps):
        product = product_of(folder)[0]
        tag = product or folder.name
        wtf = folder / "WTF"
        found = [wtf / "Config.wtf"] if (wtf / "Config.wtf").is_file() else []
        found += sorted(wtf.glob("Account/*/SavedVariables/*.lua"))
        found += sorted(wtf.glob("Account/*/*/*/SavedVariables/*.lua"))
        for path in found:
            rel = path.relative_to(folder).as_posix()
            items.append(_Item("wtf", path, f"wtf/{tag}/{rel}", product, str(folder), rel))
    cache = deps.cache_dir
    for name in ("config.json", "addons/config.json"):
        path = cache / "bridge" / name
        if path.is_file():
            items.append(_Item("bridge", path, f"cache/bridge/{name}"))
    project = _bridge_project(cache)
    if project is not None:
        for path in _files(project):
            rel = path.relative_to(project).as_posix()
            items.append(_Item("bridge", path, f"conversation-addons/{project.name}/{rel}"))
    update = cache / "update"
    for path in [*_files(update / "pending"), update / "state.json", update / "config.json"]:
        if path.is_file():
            items.append(_Item("update", path, f"cache/{path.relative_to(cache).as_posix()}"))
    for rel in ("client_builds.json", "measures/last.json"):
        if (cache / rel).is_file():
            items.append(_Item("cache", cache / rel, f"cache/{rel}"))
    return items


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Sauvegarde ----------------------------------------------------------------------------------------------------


def _resolve_root(deps: Deps, root: Path | None) -> Path:
    return root if root is not None else default_root(deps)[0]


def make_backup(deps: Deps, now: datetime, *, reason: str, root: Path | None = None) -> Path:
    """Une sauvegarde complète, écrite dans un dossier `.partiel` renommé à la fin ; les plus anciennes au-delà de 14
    sont retirées. Rend son dossier."""
    base = _resolve_root(deps, root)
    stamp = now.astimezone(UTC).strftime(STAMP_FORMAT)  # heure UTC, comme created_at
    final = base / stamp
    n = 2
    while final.exists():
        final = base / f"{stamp}-{n}"
        n += 1
    partial = final.with_name(final.name + PARTIAL_SUFFIX)
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    files = []
    skipped: list[str] = []
    for item in collect(deps):
        target = partial / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(item.origin, target)
        except OSError as exc:
            skipped.append(f"{item.origin} : {exc}")  # signalé dans le manifeste, jamais omis sans trace
            continue
        entry: dict[str, Any] = {
            "kind": item.kind,
            "path": item.path,
            "origin": str(item.origin),
            "sha256": _sha(target),
            "size": target.stat().st_size,
        }
        if item.kind == "wtf":
            entry.update(product=item.product, folder=item.folder, rel=item.rel)
        files.append(entry)
    manifest = {
        "schema_version": 1,
        "created_at": format_utc(now),
        "reason": reason,
        "machine": platform.node(),
        "note": f"{MANIFEST_NOTE} : copie simple de ce qui n'est pas sur GitHub ; forever backup restore.",
        "files": files,
        "skipped": skipped,
    }
    (partial / MANIFEST).write_bytes((json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    partial.rename(final)
    prune(base)
    return final


def manifest_of(path: Path) -> dict[str, Any]:
    doc = json.loads((path / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise TypeError("manifeste de sauvegarde : objet JSON attendu")
    return doc


def list_backups(root: Path) -> list[BackupInfo]:
    """Sauvegardes complètes de la racine, de la plus ancienne à la plus récente (un dossier `.partiel` n'est pas
    une sauvegarde)."""
    found = []
    if not root.is_dir():
        return []
    # Seuls les dossiers datés dont le manifeste est celui de forever comptent : une racine partagée (FOREVER_BACKUP_DIR
    # sur un disque) peut contenir d'autres dossiers, jamais lus comme des sauvegardes ni supprimés par prune.
    for path in sorted(p for p in root.iterdir() if p.is_dir() and _STAMP.match(p.name)):
        try:
            doc = manifest_of(path)
            files = doc["files"]
            if not str(doc.get("note", "")).startswith(MANIFEST_NOTE) or not isinstance(files, list):
                continue
        except (OSError, ValueError, TypeError, KeyError):
            continue
        found.append(
            BackupInfo(path.name, path, str(doc.get("created_at", "")), str(doc.get("reason", "")), len(files))
        )
    return found


def prune(root: Path, keep: int = KEEP) -> list[Path]:
    """Retire les sauvegardes les plus anciennes au-delà de `keep` ; rend les dossiers retirés."""
    found = list_backups(root)
    removed = [b.path for b in found[: max(0, len(found) - keep)]]
    for path in removed:
        shutil.rmtree(path, ignore_errors=True)
    return removed


def daily(deps: Deps, now: datetime, *, root: Path | None = None) -> Path | None:
    """Sauvegarde du jour (passage de `forever update --auto`) si aucune n'a moins de 24 h et si le jeu est fermé
    (état inconnu = ouvert : reportée au passage suivant) ; None sinon."""
    if deps.game_running() is not False:
        return None
    base = _resolve_root(deps, root)
    found = list_backups(base)
    if found:
        try:
            last = datetime.fromisoformat(found[-1].created_at)
        except ValueError:
            last = None
        if last is not None and now - last < DAILY_EVERY:
            return None
    return make_backup(deps, now, reason="sauvegarde du jour", root=base)


# --- Restauration --------------------------------------------------------------------------------------------------


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".restauration")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _target(deps: Deps, entry: Mapping[str, Any]) -> tuple[Path | None, str]:
    """Où restaurer un fichier (None : laissé de côté, avec la raison)."""
    kind, origin = entry["kind"], Path(entry["origin"])
    if kind == "profile":
        return _profile_file(deps), ""
    if kind == "wtf":
        wow = deps.wow_dir
        if wow is None:
            return None, "aucune installation lue"
        if same_folder(Path(entry["folder"]), wow):
            return wow / entry["rel"], ""
        if entry.get("product") is not None and product_of(wow)[0] == entry["product"]:
            return wow / entry["rel"], ""  # même produit réinstallé ailleurs
        return None, f"produit {entry.get('product')} : jamais copié dans une autre installation"
    path = str(entry["path"])
    if path.startswith("cache/"):
        return deps.cache_dir / path.removeprefix("cache/"), ""
    return origin, ""


def restore(
    deps: Deps,
    stamp: str | None,
    *,
    only: frozenset[str] = frozenset(),
    confirm: bool,
    root: Path | None = None,
) -> RestorePlan:
    """Restaure une sauvegarde (la plus récente si `stamp` est None) : jeu fermé exigé ; sans `confirm`, rien n'est
    écrit (plan seulement) ; sinon l'état courant est sauvegardé d'abord, puis chaque fichier est réécrit d'un bloc."""
    base = _resolve_root(deps, root)
    found = list_backups(base)
    chosen = next((b for b in found if b.stamp == stamp), None) if stamp else (found[-1] if found else None)
    if chosen is None:
        raise PathNotFoundError("Sauvegarde", str(base / (stamp or "<aucune>")), "lister : forever backup list")
    if deps.game_running() is not False:
        raise InvalidArgumentError(
            "Restauration refusée : le jeu est ouvert (ou son état est inconnu) ; il réécrirait ses SavedVariables "
            "à la fermeture.",
            "fermer le jeu, puis relancer forever backup restore",
        )
    written, skipped, todo = [], [], []
    for entry in manifest_of(chosen.path)["files"]:
        if only and entry["kind"] not in only:
            continue
        target, why = _target(deps, entry)
        if target is None:
            skipped.append(f"{entry['path']} : {why}")
            continue
        written.append(str(target))
        todo.append(((chosen.path / entry["path"]).read_bytes(), target))  # lu avant toute nouvelle sauvegarde
    if not confirm:
        return RestorePlan(chosen.stamp, written, skipped)
    before = make_backup(deps, deps.now(), reason="avant restauration", root=base)
    for data, target in todo:
        _write_atomic(target, data)
    return RestorePlan(chosen.stamp, written, skipped, before, True)
