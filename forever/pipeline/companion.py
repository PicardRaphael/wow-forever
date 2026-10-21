"""Forever Companion lu pour les neuf classes (plan « Sources d'abord », étape b ; décisions 272 et 288).

Lecture locale de `Data/Talents.lua` (arbres : identifiant de sort, rangs, ligne, colonne ; builds par spécialisation,
points par arbre et par position, sans ordre de prise), `Data/Rotations.lua` (rotations en prose : texte et sorts
nommés) et `Data/Meta.lua` (version et date des données). Chaque build est ramené à nos clés de talent par
l'identifiant de sort, le nom à défaut ; une position inconnue de nos données n'est jamais devinée : le build est écarté
avec sa raison et la classe a ses talents « sans correspondance ». Rien n'est recopié dans le dépôt (décision 133)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.pipeline.lua_table import parse_lua_value_at

FOLDER = "ForeverCompanion"
_TREES = re.compile(r'ForeverCompanionData\.talentTrees\["(\w+)"\]\s*=\s*')
_BUILDS = re.compile(r'ForeverCompanionData\.talentBuilds\["(\w+)"\]\s*=\s*')
_ROTATIONS = re.compile(r'R\["([^"]+)"\]\s*=\s*')


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _tables(text: str, pattern: re.Pattern[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m in pattern.finditer(text):
        try:
            value, _ = parse_lua_value_at(text, m.end())
        except ValueError:
            continue
        out[m.group(1)] = value
    return out


def _list(value: Any) -> list[Any]:
    """Table Lua lue en liste (clés 1…n) ou laissée telle quelle."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        keys = sorted(k for k in value if isinstance(k, int))
        return [value[k] for k in keys]
    return []


def _text(tokens: Any) -> str:
    return "".join(str(t.get("v", "")) for t in _list(tokens) if isinstance(t, dict)).strip()


def talents_of_build(
    tabs: Mapping[Any, Any], trees: Sequence[Sequence[Mapping[str, Any]]], by_id: Mapping[int, str],
    by_name: Mapping[str, str],
) -> tuple[dict[str, int], list[str]]:  # fmt: skip
    """Points d'un build (`tabs` : arbre à partir de 1 -> position à partir de 0 -> rang) en nos clés, et les
    positions sans correspondance (nom du talent de l'addon, ou « position <arbre>.<position> »)."""
    talents: dict[str, int] = {}
    unmatched: list[str] = []
    for tab, points in sorted((int(k), v) for k, v in tabs.items()):
        tree = trees[tab - 1] if 0 < tab <= len(trees) else []
        for pos, rank in sorted((int(k), int(v)) for k, v in (points or {}).items()):
            if rank <= 0:
                continue
            entry = tree[pos] if 0 <= pos < len(tree) else None
            if entry is None:
                unmatched.append(f"position {tab}.{pos}")
                continue
            key = by_id.get(int(entry.get("id") or 0)) or by_name.get(str(entry.get("name") or ""))
            if key is None:
                unmatched.append(str(entry.get("name") or f"position {tab}.{pos}"))
                continue
            talents[key] = talents.get(key, 0) + rank
    return talents, unmatched


def read_companion(addons: Path, classes: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
    """Arbres, builds et rotations de Forever Companion par classe (nos noms de classe), builds en nos clés ; None
    sans l'addon."""
    folder = addons / FOLDER / "Data"
    talents_text = _read(folder / "Talents.lua")
    if talents_text is None:
        return None
    meta_text = _read(folder / "Meta.lua") or ""
    meta: dict[str, Any] = {}
    m = re.search(r"ForeverCompanionData\.meta\s*=\s*", meta_text)
    if m:
        try:
            value, _ = parse_lua_value_at(meta_text, m.end())
            meta = {k: value.get(k) for k in ("dataVersion", "updated")} if isinstance(value, dict) else {}
        except ValueError:
            meta = {}
    trees_by_token = _tables(talents_text, _TREES)
    builds_by_token = _tables(talents_text, _BUILDS)
    rotations = _tables(_read(folder / "Rotations.lua") or "", _ROTATIONS)
    out: dict[str, Any] = {}
    for cls, doc in classes.items():
        token = str(doc.get("file") or cls).lower()
        raw_trees = _list(trees_by_token.get(token))
        if not raw_trees:
            continue
        trees = [[t for t in _list(tree.get("talents")) if isinstance(t, dict)] for tree in raw_trees]
        ours = [t for tree in doc.get("trees", []) for t in tree.get("talents", [])]
        by_id = {int(t["spell_id"]): str(t["key"]) for t in ours if t.get("spell_id")}
        by_name = {str(t["name"]): str(t["key"]) for t in ours}
        class_unmatched = [
            str(t.get("name"))
            for tree in trees
            for t in tree
            if int(t.get("id") or 0) not in by_id and str(t.get("name")) not in by_name
        ]
        specs: dict[str, Any] = {}
        for spec, rows in (builds_by_token.get(token) or {}).items():
            builds = []
            for b in _list(rows):
                if not isinstance(b, dict):
                    continue
                talents, unmatched = talents_of_build(b.get("tabs") or {}, trees, by_id, by_name)
                builds.append({"name": str(b.get("name")), "level": b.get("lv"), "talents": talents,
                               "unmatched": unmatched})  # fmt: skip
            rot = (rotations.get(cls) or {}).get(spec) or {}
            specs[str(spec)] = {
                "builds": builds,
                "rotation": {
                    "single": [_text(line) for line in _list(rot.get("single"))],
                    "aoe": [_text(line) for line in _list(rot.get("aoe"))],
                    "intro": _text(rot.get("intro")),
                },
            }
        out[cls] = {"specs": specs, "unmatched": class_unmatched}
    return {"meta": meta, "classes": out}
