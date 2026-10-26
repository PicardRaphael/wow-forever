"""Historique des installations de la veille (décision 295) : chaque écriture fusionnée dans `main` par
`forever update` laisse une fiche `<cache>/update/installed/<id>.json` (version, révision, commit, ce qui a changé
en mots de joueur, état). La fiche nourrit la carte « Mis à jour » du pont et `forever update status`, et porte la
commande « Annuler » (`forever update undo <id>`). Une fiche annulée empêche la veille de réinstaller le même
contenu ; un contenu nouveau s'installe normalement.

Ce module ne fait ni git ni réseau : il lit et écrit des fiches."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forever.errors import InvalidArgumentError

INSTALLED_STATES = ("installée", "annulée")


def installed_dir(cache_dir: Path) -> Path:
    return cache_dir / "update" / "installed"


def _path(cache_dir: Path, record_id: str) -> Path:
    if not record_id or any(c in record_id for c in "/\\") or record_id.startswith("."):
        raise InvalidArgumentError(f"Identifiant d'installation invalide : {record_id!r}.", "`forever update status`")
    return installed_dir(cache_dir) / f"{record_id}.json"


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path: Path, doc: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def save_installed(cache_dir: Path, record: Mapping[str, Any]) -> Path:
    """Écrit (ou remplace) la fiche d'une installation ; l'historique n'est jamais élagué."""
    path = _path(cache_dir, str(record["id"]))
    _write(path, record)
    return path


def load_installed(cache_dir: Path, record_id: str) -> dict[str, Any]:
    doc = _read(_path(cache_dir, record_id))
    if not isinstance(doc, dict):
        raise InvalidArgumentError(
            f"Aucune installation {record_id} dans l'historique de la veille.",
            "`forever update status` liste les installations et leur identifiant",
        )
    return doc


def update_installed(cache_dir: Path, record_id: str, **fields: Any) -> dict[str, Any]:
    doc = {**load_installed(cache_dir, record_id), **fields}
    save_installed(cache_dir, doc)
    return doc


def list_installed(cache_dir: Path) -> list[dict[str, Any]]:
    """Fiches de l'historique, de la plus récente à la plus ancienne."""
    folder = installed_dir(cache_dir)
    docs = [d for p in sorted(folder.glob("*.json")) if isinstance(d := _read(p), dict)] if folder.is_dir() else []
    return sorted(docs, key=lambda d: (str(d.get("installed_at") or ""), str(d.get("id"))), reverse=True)


def undone(cache_dir: Path, record_id: str) -> dict[str, Any] | None:
    """Fiche annulée de ce contenu (même identifiant), sinon None : la veille ne le réinstalle pas."""
    doc = _read(_path(cache_dir, record_id)) if record_id else None
    return doc if isinstance(doc, dict) and doc.get("state") == "annulée" else None


def notices(cache_dir: Path) -> list[dict[str, Any]]:
    """Installations à signaler (carte « Mis à jour ») : ni masquées ni annulées, plus récentes d'abord."""
    return [d for d in list_installed(cache_dir) if d.get("state") == "installée" and not d.get("dismissed")]


def notice_lines(record: Mapping[str, Any]) -> list[str]:
    """Ce qu'une installation a changé, pour la carte et `forever update status` : résumé des valeurs, puis les notes
    de la règle (valeur faite à la main remplacée…)."""
    lines: list[str] = []
    summary = str(record.get("summary") or "")
    if summary:
        lines.append(summary)
    lines += [str(m) for m in record.get("measures") or []]
    lines += [str(n) for n in record.get("notes") or []]
    return lines


def title(record: Mapping[str, Any]) -> str:
    what = "mesure des journaux" if record.get("kind") == "measures" else "données"
    return f"{what} {record.get('version')} r{record.get('revision')}"
