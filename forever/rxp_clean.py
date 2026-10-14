"""Retrait sûr des feuilles de route livrées par forever dans RestedXP (CJ1, bloc 2, demande de l'utilisateur du
2026-10-14, décision 272).

RestedXP range chaque guide importé dans sa sauvegarde de compte (`RXPDB`, `WTF/Account/*/SavedVariables/
RXPGuides.lua`), sous une clé `<groupe>|<sous-groupe>|<nom>` suivie d'un compteur : deux imports du même guide laissent
deux entrées, et le bouton « Remove » de `/rxp import` n'efface pas la bonne (question RXP3). Cette commande, **jeu
fermé seulement**, retire les seules entrées du groupe « Forever Routes » après une copie datée du fichier ; le
fichier est relu après coup et tout le reste doit être identique, sinon rien n'est écrit. Essai à blanc par défaut.
Aucun appel à une fonction interne de RestedXP, aucune autre clé touchée."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forever.errors import DataSchemaError, InvalidArgumentError
from forever.pipeline.lua_table import parse_lua_value_at

ROUTES_GROUP = "Forever Routes"  # groupe des guides livrés par le pont (forever/bridge/loop.py, ROUTE_GROUP)
SV_GLOB = "WTF/Account/*/SavedVariables/RXPGuides.lua"
DB_MARKER = "RXPDB = "
_KEY = re.compile(r'\["(' + re.escape(ROUTES_GROUP) + r'\|(?:[^"\\]|\\.)*)"\]\s*=\s*')


BYTES = "latin-1"  # lecture et écriture octet pour octet : la sauvegarde porte des guides compressés (pas de l'UTF-8)


def _read(path: Path) -> str:
    return path.read_bytes().decode(BYTES)


def _shown(key: str) -> str:
    """Clé lue octet pour octet, affichée en UTF-8 (noms des guides de forever : « Forever · Bob · 1-10 »)."""
    return key.encode(BYTES).decode("utf-8", "replace")


def forever_keys(text: str) -> list[str]:
    """Clés des guides du groupe « Forever Routes » dans le texte d'une sauvegarde, dans l'ordre."""
    return [m.group(1) for m in _KEY.finditer(text)]


def _without(value: Any) -> Any:
    """Copie d'une valeur lue sans les clés du groupe « Forever Routes », à toute profondeur."""
    if isinstance(value, dict):
        return {
            k: _without(v) for k, v in value.items() if not (isinstance(k, str) and k.startswith(ROUTES_GROUP + "|"))
        }
    if isinstance(value, list):
        return [_without(v) for v in value]
    return value


def _db(text: str, where: Path) -> Any:
    start = text.find(DB_MARKER)
    if start < 0:
        raise DataSchemaError(f"{where} : « RXPDB » absent ; fichier laissé tel quel.")
    return parse_lua_value_at(text, start + len(DB_MARKER))[0]


def remove_forever_entries(text: str) -> tuple[str, list[str]]:
    """Texte sans les entrées du groupe « Forever Routes » (clé, valeur, virgule et fin de ligne), et les clés
    retirées ; le reste du texte est gardé octet pour octet."""
    out: list[str] = []
    removed: list[str] = []
    pos = 0
    for m in _KEY.finditer(text):
        if m.start() < pos:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        start = line_start if not text[line_start : m.start()].strip() else m.start()
        _, end = parse_lua_value_at(text, m.end())
        while end < len(text) and text[end] in " \t":
            end += 1
        if end < len(text) and text[end] == ",":
            end += 1
        newline = text.find("\n", end)
        if (
            newline >= 0
            and not text[end:newline].strip(" \t")
            or (newline >= 0 and text[end:newline].lstrip().startswith("--"))
        ):
            end = newline + 1
        out.append(text[pos:start])
        removed.append(m.group(1))
        pos = end
    out.append(text[pos:])
    return "".join(out), removed


def clean_rxp_routes(
    wow_dir: Path | None,
    *,
    apply: bool,
    backup_dir: Path,
    game_running: Callable[[], bool | None],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Liste (à blanc) ou retire (`apply`, jeu fermé) les routes de forever des sauvegardes de RestedXP de chaque
    compte ; copie datée de chaque fichier avant écriture ; relecture qui exige un fichier identique hors de ces
    entrées. `InvalidArgumentError` si le jeu tourne ou si son état est inconnu."""
    files = sorted(wow_dir.glob(SV_GLOB)) if wow_dir is not None and wow_dir.is_dir() else []
    if not files:
        return {"status": "à blanc", "files": [], "message": "aucune sauvegarde de RestedXP trouvée (rien à retirer)"}
    rows = [{"path": str(f), "keys": [_shown(k) for k in forever_keys(_read(f))]} for f in files]
    total = sum(len(r["keys"]) for r in rows)
    if not apply:
        message = (
            f"{total} route(s) de forever dans RestedXP ; `forever route rxp-clean --apply`, jeu fermé, les retire"
        )
        return {"status": "à blanc", "files": rows, "message": message}
    if game_running() is not False:
        raise InvalidArgumentError(
            "Le jeu tourne, ou son état est inconnu : la sauvegarde de RestedXP serait réécrite à sa fermeture.",
            "fermer complètement le jeu, puis relancer forever route rxp-clean --apply",
        )
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    for path, row in zip(files, rows, strict=True):
        if not row["keys"]:
            continue
        text = _read(path)
        new_text, removed = remove_forever_entries(text)
        if _db(new_text, path) != _without(_db(text, path)) or forever_keys(new_text):
            raise DataSchemaError(f"{path} : relecture différente après le retrait ; fichier laissé tel quel.")
        target = backup_dir / stamp / path.parent.parent.name / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(new_text.encode(BYTES))
        os.replace(tmp, path)
        row["removed"] = [_shown(k) for k in removed]
        row["backup"] = str(target)
    message = f"{total} route(s) de forever retirée(s) de RestedXP ; copies dans {backup_dir / stamp}"
    return {"status": "retirées", "files": rows, "message": message}
