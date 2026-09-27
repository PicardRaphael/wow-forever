"""Lecture de la SavedVariable `ForeverLoggerDB` de l'addon ForeverLogger (fichier
`WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua`), sans exécuter de Lua ni accéder au réseau.

Contenu (addon/README.md) : par GUID de personnage, des instantanés (connexion, gain de niveau, changement de talents)
et les gains d'expérience, horodatés en heure du serveur (`time`) et en heure locale (`localtime`, même format que
les journaux de combat). La jointure avec un journal se fait par GUID et heure locale."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.lua_table import parse_lua_assignments

VARIABLE = "ForeverLoggerDB"
LOCAL_TIME_FORMAT = "%m/%d/%Y %H:%M:%S"


class Snapshot(NamedTuple):
    reason: str
    time: int | None
    localtime: datetime | None
    level: int | None
    talents: dict[int, int] | None
    spell_bonus: dict[str, float]
    spell_crit: dict[str, float]


class XpGain(NamedTuple):
    time: int | None
    localtime: datetime | None
    level: int | None
    text: str


class Character(NamedTuple):
    guid: str
    name: str | None
    realm: str | None
    class_: str | None
    race: str | None
    snapshots: list[Snapshot]
    xp: list[XpGain]


class LoggerDB(NamedTuple):
    schema: int | None
    characters: dict[str, Character]

    def level_at(self, guid: str, when: datetime) -> int | None:
        """Niveau du dernier instantané de ce personnage pris avant `when` (heure locale) ; None sinon."""
        character = self.characters.get(guid)
        if character is None:
            return None
        known = [s for s in character.snapshots if s.localtime is not None and s.level is not None]
        before = [s for s in known if s.localtime is not None and s.localtime <= when]
        if not before:
            return None
        return max(before, key=lambda s: s.localtime or when).level


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):  # table Lua à trous : positions en clés entières
        return [value[k] for k in sorted(k for k in value if isinstance(k, int))]
    return []


def _opt_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _numbers(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {str(k): float(v) for k, v in value.items() if isinstance(v, int | float) and not isinstance(v, bool)}


def _localtime(value: Any, path: Path) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.strptime(str(value), LOCAL_TIME_FORMAT)  # noqa: DTZ007 : heure locale du client
    except ValueError as exc:
        raise DataSchemaError(f"{path.name} : heure locale illisible « {value} ».") from exc


def read_logger_db(path: Path) -> LoggerDB:
    """`ForeverLoggerDB` lue dans un fichier de SavedVariables (PathNotFoundError, DataSchemaError)."""
    if not path.is_file():
        raise PathNotFoundError(
            "SavedVariables de ForeverLogger",
            str(path),
            "donner WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua (écrit au /reload ou à la déconnexion)",
        )
    try:
        values = parse_lua_assignments(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise DataSchemaError(f"{path.name} : {exc}.") from exc
    raw = values.get(VARIABLE)
    if not isinstance(raw, dict):
        raise DataSchemaError(f"{path.name} : variable {VARIABLE} absente ou qui n'est pas une table.")
    characters: dict[str, Character] = {}
    chars = raw.get("characters")
    for guid, c in chars.items() if isinstance(chars, dict) else []:
        if not isinstance(guid, str) or not isinstance(c, dict):
            continue
        snapshots = []
        for s in _list(c.get("snapshots")):
            if not isinstance(s, dict):
                continue
            talents = s.get("talents")
            snapshots.append(
                Snapshot(
                    reason=_str(s.get("reason")) or "",
                    time=_opt_int(s.get("time")),
                    localtime=_localtime(s.get("localtime"), path),
                    level=_opt_int(s.get("level")),
                    talents={int(k): int(v) for k, v in talents.items() if isinstance(k, int) and isinstance(v, int)}
                    if isinstance(talents, dict)
                    else None,
                    spell_bonus=_numbers(s.get("spell_bonus")),
                    spell_crit=_numbers(s.get("spell_crit")),
                )
            )
        xp = [
            XpGain(
                _opt_int(x.get("time")),
                _localtime(x.get("localtime"), path),
                _opt_int(x.get("level")),
                str(x.get("text", "")),
            )
            for x in _list(c.get("xp"))
            if isinstance(x, dict)
        ]
        characters[guid] = Character(
            guid, _str(c.get("name")), _str(c.get("realm")), _str(c.get("class")), _str(c.get("race")), snapshots, xp
        )
    return LoggerDB(_opt_int(raw.get("schema")), characters)
