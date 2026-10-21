"""Valeurs héritées de la Classic, recensées et marquées (décision 294 : Forever seulement ; plan des simulateurs §6).

Une règle d'origine (`origins.json`) ou une entrée de `mechanics.json` dont la source cite la Classic (règle de
Classic, vMangos, émulateur de Classic, barème Classic) est listée ici ; une réponse qui s'appuie sur un fichier qui en
porte le dit dans sa provenance (`classic_note`). Leur remplacement par des valeurs de Forever vient après la sortie,
avec les mesures de l'utilisateur. Aucune valeur de jeu lue ici : seulement les sources."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_CLASSIC = re.compile(r"\bclassic\b|vmangos", re.IGNORECASE)
ENGINE_FILES = frozenset({"mechanics.json", "leveling.json"})  # fichiers lus par le moteur du Mage gelé
NOTE_KEYS = 4  # clés citées dans la note de provenance (réglage d'affichage)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def classic_values(version_dir: Path, files: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Valeurs héritées de la Classic d'une version installée : (fichier, chemin, origine, certitude, source), sans
    doublon, triées ; `files` : seulement ces fichiers (`mechanics.json` n'est lu que s'il en fait partie)."""
    wanted = set(files) if files is not None else None
    out: dict[tuple[str, str], dict[str, Any]] = {}
    origins = _read(version_dir / "origins.json") or {}
    for rule in origins.get("rules", []):
        text = " ".join(str(rule.get(k) or "") for k in ("source", "reason"))
        if not _CLASSIC.search(text):
            continue
        if wanted is not None and rule["file"] not in wanted:
            continue
        for path in rule.get("paths") or []:
            out.setdefault((rule["file"], path), {"file": rule["file"], "path": path, "origin": rule.get("origin"),
                                                  "certainty": rule.get("certainty"), "source": text.strip()})  # fmt: skip
    read_mechanics = wanted is None or "mechanics.json" in wanted
    mechanics = (_read(version_dir / "mechanics.json") if read_mechanics else None) or {}
    for key, entry in (mechanics.get("values") or {}).items():
        if not isinstance(entry, dict):
            continue
        text = " ".join(str(entry.get(k) or "") for k in ("source", "note"))
        if _CLASSIC.search(text):
            path = f"/values/{key}"
            out.setdefault(("mechanics.json", path), {"file": "mechanics.json", "path": path, "origin": "manuel",
                                                      "certainty": entry.get("certainty"), "source": text.strip()})  # fmt: skip
    return [out[k] for k in sorted(out)]


def classic_note(version_dir: Path, files: Iterable[str], keys: Iterable[str] | None = None) -> str | None:
    """Hypothèse de provenance d'une réponse qui s'appuie sur `files` (et, si donnés, sur les seules clés `keys`) :
    nombre et premières clés des valeurs héritées de la Classic qu'ils portent ; None s'il n'y en a aucune."""
    wanted = set(files)
    only = {k.strip("/") for k in keys} if keys is not None else None
    rows = [
        r
        for r in classic_values(version_dir, wanted)
        if r["file"] in wanted and (only is None or r["path"].removeprefix("/values/").strip("/") in only)
    ]
    if not rows:
        return None
    keys = [r["path"].removeprefix("/values/").lstrip("/") for r in rows]
    shown = ", ".join(keys[:NOTE_KEYS]) + (", …" if len(keys) > NOTE_KEYS else "")
    return (
        f"s'appuie sur {len(rows)} valeur(s) héritées de la Classic ({shown} ; liste : `forever origins classic`), "
        "suppose ; remplacées par des valeurs de Forever après la sortie, avec tes mesures (décision 294)"
    )
