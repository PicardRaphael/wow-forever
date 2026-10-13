"""Chaîne de quêtes du Cozy Sleeping Bag lue dans les addons installés (T04f, bloc E), en lecture locale :
Naowh Forever Discovery (`NaowhForever_Discovery/Data/SleepingBag.lua` : objets à cliquer, cartes, positions,
quêtes) et FojjiCore Dungeon Journal (`FojjiCore_DungeonJournal/Data/Guides.lua`, clé `sleepingbag` : zones,
positions, titres). Jamais recopiée dans le dépôt (décision 133) ; aucun chiffre de jeu ici."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.errors import DataSchemaError
from forever.pipeline.lua_table import parse_lua_value_at

NAOWH = ("NaowhForever_Discovery", "Data/SleepingBag.lua")
FOJJI = ("FojjiCore_DungeonJournal", "Data/Guides.lua")


@dataclass(frozen=True)
class AddonChain:
    """Chaîne lue dans un addon : niveau conseillé, objet, étapes par camp (« A », « H », ou « * » : les deux)."""

    addon: str
    version: str | None
    level: int | None
    item: int | None
    steps: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    optional: dict[str, Any] | None = None


def _version(folder: Path) -> str | None:
    for toc in sorted(folder.glob("*.toc")):
        for line in toc.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("## Version:"):
                return line.split(":", 1)[1].strip() or None
    return None


def _text(path: Path) -> str:
    """Texte du fichier, chaînes concaténées (« "a" .. "b" ») réunies."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DataSchemaError(f"{path} illisible ({exc}).") from exc
    return re.sub(r'"\s*\.\.\s*"', "", text)


def _value_after(text: str, marker: str, path: Path) -> Any:
    start = text.find(marker)
    if start < 0:
        raise DataSchemaError(f"{path} : « {marker} » absent (format de l'addon changé).")
    try:
        return parse_lua_value_at(text, start + len(marker))[0]
    except ValueError as exc:
        raise DataSchemaError(f"{path} : {exc}.") from exc


def _int(value: Any) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def read_naowh_chain(addons_dir: Path) -> AddonChain | None:
    """Chaîne de Naowh Forever Discovery ; None si l'addon ou le fichier manque. Les tables locales partagées
    (`local POCKET_LITTER = {…}`) sont remplacées par leur valeur avant la lecture."""
    folder = addons_dir / NAOWH[0]
    path = folder / NAOWH[1]
    if not path.is_file():
        return None
    text = _text(path)
    locals_: dict[str, str] = {}
    for m in re.finditer(r"^local\s+([A-Z][A-Z0-9_]*)\s*=\s*(?=\{)", text, re.MULTILINE):
        try:
            _, end = parse_lua_value_at(text, m.end())
        except ValueError as exc:
            raise DataSchemaError(f"{path} : {exc}.") from exc
        locals_[m.group(1)] = text[m.end() : end]
    marker = "ns.SleepingBag ="
    head = text.find(marker)
    if head < 0:
        raise DataSchemaError(f"{path} : « {marker} » absent (format de l'addon changé).")
    body = text[head:]
    if locals_:
        body = re.sub(r"\b(" + "|".join(map(re.escape, locals_)) + r")\b", lambda m: locals_[m.group(1)], body)
    raw = _value_after(body, marker, path)
    if not isinstance(raw, dict) or not isinstance(raw.get("steps"), dict):
        raise DataSchemaError(f"{path} : table SleepingBag sans étapes.")
    steps = {
        str(side): [dict(s) for s in v if isinstance(s, dict)]
        for side, v in raw["steps"].items()
        if isinstance(v, list)
    }
    optional = raw.get("optional")
    return AddonChain(
        NAOWH[0],
        _version(folder),
        _int(raw.get("level")),
        _int(raw.get("item")),
        steps,
        dict(optional) if isinstance(optional, dict) else None,
    )


def read_fojji_chain(addons_dir: Path) -> AddonChain | None:
    """Chaîne du guide `sleepingbag` de FojjiCore Dungeon Journal ; None si l'addon, le fichier ou le guide manque.
    Étapes sous « * » (chacune peut porter son camp, `side`)."""
    folder = addons_dir / FOJJI[0]
    path = folder / FOJJI[1]
    if not path.is_file():
        return None
    guides = _value_after(_text(path), "FDJ.Guides =", path)
    guide = (
        next((g for g in guides if isinstance(g, dict) and g.get("key") == "sleepingbag"), None)
        if isinstance(guides, list)
        else None
    )
    if guide is None:
        return None
    rewards = guide.get("rewards")
    item = _int(rewards[0]) if isinstance(rewards, list) and rewards else None
    steps = [dict(s) for s in guide.get("steps") or [] if isinstance(s, dict)]
    return AddonChain(FOJJI[0], _version(folder), _int(guide.get("level")), item, {"*": steps})
