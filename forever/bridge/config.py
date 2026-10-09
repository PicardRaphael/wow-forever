"""Configuration du pont (P06a, sonde en jeu E du 2026-10-09) : `<cache>/bridge/config.json`. `model` : modèle de la
conversation « jeu » (alias de Claude Code : `sonnet`, `haiku`, `opus`, ou un identifiant complet) ; Sonnet par défaut,
les calculs venant des outils forever."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "sonnet"
DEFAULTS: dict[str, Any] = {"model": DEFAULT_MODEL}


def config_path(cache_dir: Path) -> Path:
    return cache_dir / "bridge" / "config.json"


def load_config(cache_dir: Path) -> dict[str, Any]:
    """Configuration lue, valeurs par défaut pour ce qui manque ou est illisible."""
    try:
        doc = json.loads(config_path(cache_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {}
    out = dict(DEFAULTS)
    if isinstance(doc, dict) and isinstance(doc.get("model"), str) and doc["model"].strip():
        out["model"] = doc["model"].strip()
    return out


def save_config(cache_dir: Path, values: dict[str, Any]) -> dict[str, Any]:
    """Écrit la configuration (fusionnée avec l'existante) atomiquement ; rend la configuration complète."""
    merged = {**load_config(cache_dir), **{k: v for k, v in values.items() if v is not None}}
    path = config_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8"))
    os.replace(tmp, path)
    return merged
