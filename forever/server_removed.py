"""Talents retirés par un correctif du serveur (décision 290) : lus dans `confirmed_changes.json` de la version
installée (changement `removed`, nature `correctif_serveur`), nommés d'après la plus récente version installée qui les
portait encore. `lookup` les dit « probablement retirés » avec leur source ; une recommandation qui les contient
(build populaire d'un addon) est écartée avec sa raison. Aucune valeur de jeu ici."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import EXIT_NOT_FOUND, ForeverError
from forever.manifest import load_manifest
from forever.pipeline.builds import version_key

SERVER = "correctif_serveur"


class RemovedTalentError(ForeverError):
    exit_code = EXIT_NOT_FOUND  # comme un talent inconnu

    def __init__(self, entry: Mapping[str, Any]) -> None:
        super().__init__(
            "removed_talent",
            f"{entry['name']} ({entry['class']}) : probablement retiré par le serveur ({_label(entry)}, certitude "
            f"{entry['certainty']}, décision 290).",
            "le jeu le confirmera à la prochaine connexion ; aucune recommandation ne le propose",
        )


def _label(entry: Mapping[str, Any]) -> str:
    if "Raidbots" in str(entry.get("source")):
        return "correctif lu dans un cache vérifié de Raidbots, sans session de jeu"
    return "correctif lu dans le cache du jeu"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _names_before(data_dir: Path, version: str) -> dict[str, tuple[str, str]]:
    """Clé -> (nom, classe) des talents des versions installées antérieures ou égales à `version`, la plus récente
    d'abord (une clé retirée garde le nom qu'elle avait)."""
    out: dict[str, tuple[str, str]] = {}
    versions = sorted((load_manifest(data_dir) or {}).get("versions", {}), key=version_key, reverse=True)
    for v in versions:
        if version_key(v) > version_key(version):
            continue
        talents = _read(data_dir / v / "talents.json") or {}
        for tree in talents.get("trees", []):
            for t in tree.get("talents", []):
                out.setdefault(str(t["key"]), (str(t.get("name") or t["key"]), "Mage"))
        classes = (_read(data_dir / v / "classes.json") or {}).get("classes") or {}
        for cls, doc in classes.items():
            for tree in doc.get("trees", []):
                for t in tree.get("talents", []):
                    out.setdefault(str(t["key"]), (str(t.get("name") or t["key"]), str(cls)))
    return out


def server_removed_talents(data_dir: Path) -> list[dict[str, Any]]:
    """Talents retirés par un correctif du serveur dans la version installée : clé, nom, classe, source (décision
    de l'entrée confirmée), certitude (`probable` pour une copie tierce du cache, décision 290)."""
    version = str((load_manifest(data_dir) or {}).get("game_version") or "")
    doc = _read(data_dir / version / "confirmed_changes.json") or {}
    removed = [
        c
        for c in doc.get("changes", [])
        if c.get("kind") == "talent" and c.get("change") == "removed" and c.get("nature") == SERVER
    ]
    if not removed:
        return []
    names = _names_before(data_dir, version)
    out = []
    for c in removed:
        key = str(c["key"])
        name, cls = names.get(key, (key, "?"))
        decision = str(c.get("decision") or "")
        certainty = "probable" if "Raidbots" in decision else "certain"
        out.append({"key": key, "name": name, "class": cls, "source": decision, "certainty": certainty})
    return out


def removed_entry(data_dir: Path, wanted: str, normalize: Any) -> dict[str, Any] | None:
    """Entrée retirée dont la clé ou le nom correspond à `wanted` (normalisé par `normalize`)."""
    for r in server_removed_talents(data_dir):
        if wanted in (normalize(r["key"]), normalize(r["name"])):
            return r
    return None


def exclude_removed_builds(
    top: Sequence[Mapping[str, Any]], class_name: str, removed: Sequence[Mapping[str, Any]]
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Builds d'un addon gardés, et écartés parce qu'ils placent un talent retiré par le serveur (positions de
    l'addon sans correspondance chez nous qui portent un nom retiré) : `{rank, removed}`."""
    names = {str(r["name"]) for r in removed if r.get("class") == class_name}
    if not names:
        return list(top), []
    kept, aside = [], []
    for b in top:
        hit = [n for n in b.get("unverifiable") or [] if n in names]
        if hit:
            aside.append({"rank": b.get("rank"), "removed": hit})
        else:
            kept.append(b)
    return kept, aside
