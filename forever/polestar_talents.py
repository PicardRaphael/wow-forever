"""Builds de talents de Polestar (LV1, décision 303) : lecture locale de `Polestar/Talents/Builds.lua`, un point par
niveau pour les trois spécialisations de chaque classe, avec les notes du guide.

Lecture par l'analyseur `lua_table` (aucun Lua exécuté) : chaque `T.Register({…})` après remplacement des chaînes
traduites `L["…"]` par leur texte anglais. Le fichier dit dans son en-tête la version du client sur laquelle il a été
écrit (`the Forever 1.60.1.NNNNN trait tables`) ; le `.toc` donne la version de l'addon. Rien n'est relié ici à nos
talents : `forever/leveling_plan.py` le fait, par le nom du talent."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from forever.pipeline.lua_table import parse_lua_value_at

ADDON_FOLDER = "Polestar"
BUILDS_FILE = Path("Talents") / "Builds.lua"
_L_STRING = re.compile(r'L\[("(?:[^"\\]|\\.)*")\]')
_REGISTER = re.compile(r"\bT\.Register\(")
_WRITTEN_ON = re.compile(r"Forever (\d+\.\d+\.\d+\.\d+) trait tables")
_TOC_VERSION = re.compile(r"^## Version:\s*(\S+)", re.MULTILINE)
NODE_SPELL, NODE_NAME = 2, 6


def _toc_version(folder: Path) -> str | None:
    try:
        text = (folder / f"{ADDON_FOLDER}.toc").read_text(encoding="utf-8-sig")
    except OSError:
        return None
    m = _TOC_VERSION.search(text)
    return m.group(1) if m else None


def _class_name(file_name: str) -> str:
    """`SHAMAN` -> `Shaman` (nom de classe de nos données)."""
    return file_name.title()


def _build(raw: dict[str, Any]) -> dict[str, Any]:
    picks = [(int(p[0]), int(p[1])) for p in raw.get("picks") or []]
    notes = raw.get("notes") or {}
    return {
        "key": str(raw.get("key")),
        "spec": raw.get("spec"),
        "split": raw.get("split"),
        "link": raw.get("link"),
        "picks": picks,
        "notes": {int(k): str(v) for k, v in (notes.items() if isinstance(notes, dict) else enumerate(notes, 1))},
    }


def read_polestar_talents(folder: Path) -> dict[str, Any] | None:
    """Builds de talents du dossier de l'addon Polestar, ou None si le fichier manque.

    Rend `version` (`.toc`), `written_on` (version du client de l'en-tête), `classes` : par classe, `summary`,
    `source`, `specs`, `nodes` (nœud -> `spell`, `name`) et `builds` (clé, spécialisation, répartition, points
    `(nœud, rang)` dans l'ordre, notes par niveau). Une table illisible lève ValueError (ligne, colonne)."""
    try:
        text = (folder / BUILDS_FILE).read_text(encoding="utf-8-sig")
    except OSError:
        return None
    head = _WRITTEN_ON.search(text[:2000])
    plain = _L_STRING.sub(r"\1", text)
    classes: dict[str, Any] = {}
    for m in _REGISTER.finditer(plain):
        value, _ = parse_lua_value_at(plain, m.end())
        if not isinstance(value, dict) or not isinstance(value.get("class"), str):
            continue
        nodes = value.get("nodes") or {}
        classes[_class_name(value["class"])] = {
            "summary": value.get("summary"),
            "source": value.get("source"),
            "specs": list(value.get("specs") or []),
            "nodes": {
                int(node): {"spell": int(e[NODE_SPELL]), "name": str(e[NODE_NAME])}
                for node, e in (nodes.items() if isinstance(nodes, dict) else ())
                if isinstance(e, list) and len(e) > NODE_NAME
            },
            "builds": [_build(b) for b in value.get("builds") or [] if isinstance(b, dict)],
        }
    return {
        "version": _toc_version(folder),
        "written_on": head.group(1) if head else None,
        "classes": classes,
    }
