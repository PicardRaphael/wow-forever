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
import re
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


# --- français réactivé dans RestedXP (accord de l'utilisateur du 2026-11-13) ------------------------------------

LOCALE_FILE = ("RXPGuides", "RXPGuides.lua")
_TABLE = re.compile(r"addon\.enabledLocale\s*=\s*\{(?P<body>[^}]*)\}")
_COMMENTED = re.compile(r'^([ \t]*)--[ \t]*(\["frFR"\][ \t]*=[ \t]*true)', re.MULTILINE)
_ACTIVE = re.compile(r'^[ \t]*\["frFR"\][ \t]*=[ \t]*true', re.MULTILINE)


def enable_french(addons: Path, cache_dir: Path, *, simulate: bool = False) -> str:
    """Réactive `["frFR"] = true` dans `addon.enabledLocale` de `RXPGuides.lua` : depuis RestedXP v4.11.36 la ligne
    est en commentaire et les guides anglais se chargent en plus des guides français. Seule cette ligne change, après
    une copie du fichier de RestedXP. Rend « réactivé », « à réactiver » (simulation), « déjà actif » ou « absent »."""
    path = addons.joinpath(*LOCALE_FILE)
    if not path.is_file():
        return "absent"
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="surrogateescape")
    table = _TABLE.search(text)
    if table is None:
        return "absent"
    body = table.group("body")
    if _ACTIVE.search(body):
        return "déjà actif"
    if not _COMMENTED.search(body):
        return "absent"
    if simulate:
        return "à réactiver"
    _atomic(backup_root(cache_dir) / "restedxp" / f"RXPGuides.lua.{hashlib.sha256(raw).hexdigest()[:12]}", raw)
    new_body = _COMMENTED.sub(r"\1\2", body, count=1)
    start, end = table.span("body")
    _atomic(path, (text[:start] + new_body + text[end:]).encode("utf-8", errors="surrogateescape"))
    return "réactivé"


def restore_locale(addons: Path, cache_dir: Path) -> bool:
    """Remet le `RXPGuides.lua` de RestedXP sauvegardé avant la dernière réactivation du français (`--annuler`)."""
    saved = sorted((backup_root(cache_dir) / "restedxp").glob("RXPGuides.lua.*"), key=lambda p: p.stat().st_mtime)
    path = addons.joinpath(*LOCALE_FILE)
    if not saved or not path.is_file() or path.read_bytes() == saved[-1].read_bytes():
        return False
    _atomic(path, saved[-1].read_bytes())
    return True
