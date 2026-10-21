"""SkillUp Forever lu pour les métiers (plan « Sources d'abord », étape b ; décisions 272 et 288).

Lecture locale de `Data/Thresholds.lua` (seuils orange, jaune, vert, gris de chaque recette, générés par l'addon depuis
le client du build nommé dans l'en-tête) et de `Data/Recipes.lua` (métier de chaque recette, noms des métiers). SkillUp
calcule en jeu l'itinéraire jusqu'au rang visé (`/skillup`) : on lit et on présente, on ne recalcule pas. Rien n'est
recopié dans le dépôt (décision 133)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FOLDER = "SkillUpForever"
_HEADER = re.compile(r"^-- Source: .*?(\d+\.\d+\.\d+\.\d+), (\d{4}-\d{2}-\d{2})", re.MULTILINE)
_THRESHOLD = re.compile(
    r"^\s*\[(\d+)\]\s*=\s*\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\},?\s*(?:--\s*(.*))?$", re.MULTILINE
)
_RECIPE = re.compile(r"^\s*\[(\d+)\]\s*=\s*\{\s*skillLine\s*=\s*(\d+)", re.MULTILINE)
_PROFESSION = re.compile(r'^\s*\["([^"]+)"\]\s*=\s*(\d+),?\s*$', re.MULTILINE)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def read_skillup(addons: Path) -> dict[str, Any] | None:
    """Build et date des données, métiers (nom -> ligne de compétence), recettes (seuils, métier, nom) ; None sans
    l'addon."""
    folder = addons / FOLDER / "Data"
    thresholds = _read(folder / "Thresholds.lua")
    if thresholds is None:
        return None
    recipes_text = _read(folder / "Recipes.lua") or ""
    head = _HEADER.search(thresholds)
    lines = {int(m.group(1)): int(m.group(2)) for m in _RECIPE.finditer(recipes_text)}
    block = (
        recipes_text[recipes_text.find("ns.ProfessionSkillLines") :]
        if "ns.ProfessionSkillLines" in recipes_text
        else ""
    )
    block = block[: block.find("}") + 1]
    professions = {m.group(1): int(m.group(2)) for m in _PROFESSION.finditer(block)}
    recipes: dict[int, dict[str, Any]] = {}
    for m in _THRESHOLD.finditer(thresholds):
        spell = int(m.group(1))
        recipes[spell] = {
            "skill_line": lines.get(spell),
            "name": (m.group(6) or "").strip() or str(spell),
            "thresholds": tuple(int(m.group(i)) for i in range(2, 6)),
        }
    return {
        "build": head.group(1) if head else None,
        "date": head.group(2) if head else None,
        "professions": professions,
        "recipes": recipes,
    }
