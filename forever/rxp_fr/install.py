"""Écriture des guides français générés (FR1), seulement sous `RXPGuides/lang/Guides-frFR/forever/`.

Avant d'écraser un fichier que RestedXP a livré (sans marqueur FR1), sa version est gardée dans
`<cache>/backups/rxp_fr/original/<fichier>` (et une copie datée par empreinte) : elle reste la source des guides
recopiés et `forever rxp traduire --annuler` la remet. Chaque écriture garde aussi le fichier qu'elle remplace sous
`<cache>/backups/rxp_fr/<id>/` : `forever update undo <id>` le remet. Écriture atomique (fichier temporaire puis
remplacement)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from forever.errors import InvalidArgumentError
from forever.rxp_fr.source import FR_DIR, is_ours, read_text

ORIGINAL = "original"


def backup_root(cache_dir: Path) -> Path:
    return cache_dir / "backups" / "rxp_fr"


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".fr1tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def originals(addons: Path, cache_dir: Path) -> dict[str, str]:
    """Fichiers français de RestedXP sauvegardés avant une écriture de FR1 (chemin relatif -> texte)."""
    root = backup_root(cache_dir) / ORIGINAL
    if not root.is_dir():
        return {}
    return {p.relative_to(root).as_posix(): read_text(p) for p in root.rglob("*.lua")}


def write_guides(addons: Path, rel: str, text: str, cache_dir: Path, write_id: str) -> Path:
    """Écrit le fichier français `rel` ; garde la version de RestedXP et le fichier remplacé."""
    target = addons.joinpath(*FR_DIR, rel)
    root = backup_root(cache_dir)
    if target.is_file() and not is_ours(target):
        raw = target.read_bytes()
        _atomic(root / ORIGINAL / rel, raw)
        _atomic(root / "restedxp" / f"{rel}.{hashlib.sha256(raw).hexdigest()[:12]}", raw)
    previous = root / write_id / rel
    if target.is_file():
        _atomic(previous, target.read_bytes())
    else:
        _atomic(previous.with_name(previous.name + ".absent"), b"")
    _atomic(target, text.encode("utf-8"))
    record = root / write_id / "write.json"
    try:
        files = json.loads(record.read_text(encoding="utf-8")).get("files", [])
    except (OSError, ValueError):
        files = []
    record.write_text(json.dumps({"files": sorted({*files, rel})}, ensure_ascii=False), encoding="utf-8")
    return target


def restore_previous(addons: Path, cache_dir: Path, write_id: str) -> list[str]:
    """Remet les fichiers remplacés par l'écriture `write_id` (annulation de la veille)."""
    folder = backup_root(cache_dir) / write_id
    if not folder.is_dir():
        raise InvalidArgumentError(
            f"Aucune sauvegarde des guides français pour {write_id}.", "voir forever update status"
        )
    done: list[str] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.name == "write.json":
            continue
        rel = path.relative_to(folder).as_posix()
        if rel.endswith(".absent"):
            rel = rel.removesuffix(".absent")
            target = addons.joinpath(*FR_DIR, rel)
            if target.is_file():
                target.unlink()
        else:
            _atomic(addons.joinpath(*FR_DIR, rel), path.read_bytes())
        done.append(rel)
    return done


def restore_originals(addons: Path, cache_dir: Path) -> list[str]:
    """Remet la version de RestedXP de chaque fichier écrit par FR1 (`--annuler`)."""
    root = backup_root(cache_dir) / ORIGINAL
    done: list[str] = []
    for path in sorted(root.rglob("*.lua")) if root.is_dir() else []:
        rel = path.relative_to(root).as_posix()
        target = addons.joinpath(*FR_DIR, rel)
        if is_ours(target):
            _atomic(target, path.read_bytes())
            done.append(rel)
    return done
