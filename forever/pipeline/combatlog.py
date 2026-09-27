"""Lecture des journaux de combat du client (`WoWCombatLog-*.txt`, format 22 avec le bloc avancé).

Ce module décrit un **format de fichier** (noms de préfixes et de suffixes, 19 champs du bloc avancé, drapeaux
d'unité), comme les colonnes CSV de `tables.py` : aucun chiffre de jeu. Seuls `COMBAT_LOG_VERSION 22` et
`ADVANCED_LOG_ENABLED 1` sont acceptés (`unsupported_log`) ; un événement inconnu est gardé brut, jamais interprété ;
une ligne mal formée lève `data_schema` avec le fichier et le numéro de ligne. Aucun accès réseau.

L'unité décrite par le bloc avancé n'est pas fixe par événement (source pour `SPELL_CAST_SUCCESS` et `SWING_DAMAGE`,
destination pour `SPELL_DAMAGE`…) : on se fie à son GUID, premier champ du bloc."""

from __future__ import annotations

import csv
import gzip
import zlib
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from forever.errors import DataSchemaError, UnsupportedLogError

SUPPORTED_VERSION = 22
LOG_GLOBS = ("WoWCombatLog-*.txt", "WoWCombatLog-*.txt.gz")  # journal du client, ou fixture compressée
NO_GUID = "0000000000000000"
AFFILIATION_MINE = 0x1  # COMBATLOG_OBJECT_AFFILIATION_MINE
TIME_FORMAT = "%m/%d/%Y %H:%M:%S.%f"
ADVANCED_FIELDS = 19
UNIT_FIELDS = 8

# Préfixes : nombre de champs après les deux unités (sort : identifiant, nom, école).
PREFIXES = {"SWING": 0, "RANGE": 3, "SPELL": 3, "SPELL_PERIODIC": 3, "SPELL_BUILDING": 3, "ENVIRONMENTAL": 0}
# Événements spéciaux qui se lisent comme un préfixe de sort suivi d'un suffixe.
SPECIAL = {
    "DAMAGE_SHIELD": ("SPELL", "_DAMAGE"),
    "DAMAGE_SPLIT": ("SPELL", "_DAMAGE"),
    "DAMAGE_SHIELD_MISSED": ("SPELL", "_MISSED"),
}
DAMAGE: tuple[str, ...] = (
    "amount",
    "base_amount",
    "overkill",
    "school",
    "resisted",
    "blocked",
    "absorbed",
    "critical",
    "glancing",
    "crushing",
)
# Suffixes : (bloc avancé présent, champs nommés obligatoires).
SUFFIXES: dict[str, tuple[bool, tuple[str, ...]]] = {
    "_DAMAGE": (True, DAMAGE),
    "_DAMAGE_LANDED": (True, DAMAGE),
    "_MISSED": (False, ("miss_type",)),
    "_HEAL": (True, ("amount", "base_amount", "overhealing", "absorbed", "critical")),
    "_ENERGIZE": (True, ("amount", "over_energize", "power_type", "max_power")),
    "_DRAIN": (True, ("amount", "power_type", "extra_amount")),
    "_LEECH": (True, ("amount", "power_type", "extra_amount")),
    "_CAST_START": (False, ()),
    "_CAST_SUCCESS": (True, ()),
    "_CAST_FAILED": (False, ("failed_type",)),
    "_AURA_APPLIED": (False, ("aura_type",)),
    "_AURA_REMOVED": (False, ("aura_type",)),
    "_AURA_REFRESH": (False, ("aura_type",)),
    "_AURA_APPLIED_DOSE": (False, ("aura_type", "amount")),
    "_AURA_REMOVED_DOSE": (False, ("aura_type", "amount")),
    "_AURA_BROKEN": (False, ("aura_type",)),
    "_AURA_BROKEN_SPELL": (False, ()),
    "_INTERRUPT": (False, ()),
    "_DISPEL": (False, ()),
    "_DISPEL_FAILED": (False, ()),
    "_STOLEN": (False, ()),
    "_EXTRA_ATTACKS": (False, ("amount",)),
    "_INSTAKILL": (False, ()),
    "_DURABILITY_DAMAGE": (False, ()),
    "_DURABILITY_DAMAGE_ALL": (False, ()),
    "_CREATE": (False, ()),
    "_SUMMON": (False, ()),
    "_RESURRECT": (False, ()),
}
# Événements à deux unités sans préfixe ni suffixe (champs restants gardés dans `raw`).
# SPELL_ABSORBED et SPELL_HEAL_ABSORBED : disposition variable (sort de l'attaquant présent ou non), reste brut.
UNIT_EVENTS = frozenset(
    {"UNIT_DIED", "UNIT_DESTROYED", "UNIT_DISSIPATES", "PARTY_KILL", "SPELL_ABSORBED", "SPELL_HEAL_ABSORBED"}
)
# Événements sans unité (contexte : zone, carte, rencontre, personnage).
CONTEXT_EVENTS = frozenset(
    {
        "ZONE_CHANGE",
        "MAP_CHANGE",
        "ENCOUNTER_START",
        "ENCOUNTER_END",
        "COMBATANT_INFO",
        "CHALLENGE_MODE_START",
        "CHALLENGE_MODE_END",
        "WORLD_MARKER_PLACED",
        "WORLD_MARKER_REMOVED",
    }
)
_PREFIX_ORDER = sorted(PREFIXES, key=len, reverse=True)


class LogHeader(NamedTuple):
    version: int
    advanced: bool
    build: str
    project_id: int


class Unit(NamedTuple):
    guid: str
    name: str | None
    flags: int
    raid_flags: int

    @property
    def kind(self) -> str:
        """Type du GUID : Player, Creature, Pet, GameObject, Vehicle…"""
        return self.guid.split("-", 1)[0]

    @property
    def npc_id(self) -> int | None:
        """Identifiant de PNJ (sixième champ du GUID) d'une créature, d'un familier, d'un objet ou d'un véhicule."""
        parts = self.guid.split("-")
        if parts[0] in ("Creature", "Pet", "GameObject", "Vehicle") and len(parts) >= 7 and parts[5].isdigit():
            return int(parts[5])
        return None

    @property
    def is_mine(self) -> bool:
        """Unité du joueur qui journalise (drapeau d'affiliation « à moi »)."""
        return bool(self.flags & AFFILIATION_MINE)


class Advanced(NamedTuple):
    """Bloc avancé (19 champs). `unknown_a` et `unknown_b` : sens inconnu (docs/OPEN_QUESTIONS.md) ; `level` est le
    niveau d'une créature, son sens pour un joueur reste à vérifier. Ressources multiples (« 3|4 ») : la première,
    ressource principale, est retenue dans `power_type`, `power`, `max_power` et `power_cost`."""

    guid: str
    owner: str
    hp: int
    max_hp: int
    attack_power: int
    spell_power: int
    armor: int
    absorb: int
    unknown_a: int
    unknown_b: int
    power_type: int
    power: int
    max_power: int
    power_cost: int
    x: float
    y: float
    ui_map_id: int
    facing: float
    level: int


class Event(NamedTuple):
    line: int
    time: datetime  # heure locale du client, sans fuseau
    name: str
    source: Unit | None
    dest: Unit | None
    spell: tuple[int, str, int] | None
    advanced: Advanced | None
    suffix: Mapping[str, object]
    raw: tuple[str, ...]


class LogSummary(NamedTuple):
    name: str
    path: Path
    header: LogHeader | None
    start: datetime | None
    end: datetime | None
    lines: int
    events: int
    mine: list[str]
    error: str | None


class _Malformed(ValueError):
    """Ligne mal formée (message sans le fichier ni la ligne, ajoutés par l'appelant)."""


def _split(line: str) -> tuple[datetime, list[str]]:
    stamp, sep, body = line.partition("  ")
    if not sep or not body:
        raise _Malformed("horodatage ou corps absent")
    try:
        time = datetime.strptime(stamp, TIME_FORMAT)  # noqa: DTZ007 : le journal n'a pas de fuseau
    except ValueError as exc:
        raise _Malformed(f"horodatage illisible « {stamp} »") from exc
    return time, next(csv.reader([body]))


def _value(token: str) -> object:
    """Nombre (décimal ou hexadécimal `0x…`), `nil` -> None, sinon texte."""
    if token == "nil":
        return None
    try:
        return int(token, 16) if token.startswith(("0x", "-0x")) else int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token


def _int(token: str, what: str) -> int:
    value = _value(token)
    if not isinstance(value, int):
        raise _Malformed(f"{what} : entier attendu, « {token} » lu")
    return value


def _float(token: str, what: str) -> float:
    value = _value(token)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _Malformed(f"{what} : nombre attendu, « {token} » lu")
    return float(value)


def _unit(fields: list[str]) -> Unit | None:
    guid, name, flags, raid_flags = fields
    if guid == NO_GUID:
        return None
    return Unit(guid, None if name == "nil" else name, _int(flags, "drapeaux"), _int(raid_flags, "drapeaux de raid"))


def _advanced(fields: list[str]) -> Advanced:
    # Plusieurs ressources (énergie et points de combo…) s'écrivent « 3|4 » : la ressource principale est retenue.
    hp, max_hp, ap, sp, armor, absorb, unknown_a, unknown_b, power_type, power, max_power, cost = (
        _int(fields[i].split("|", 1)[0], f"bloc avancé, champ {i + 1}") for i in range(2, 14)
    )
    return Advanced(
        fields[0],
        fields[1],
        hp,
        max_hp,
        ap,
        sp,
        armor,
        absorb,
        unknown_a,
        unknown_b,
        power_type,
        power,
        max_power,
        cost,
        _float(fields[14], "bloc avancé, x"),
        _float(fields[15], "bloc avancé, y"),
        _int(fields[16], "bloc avancé, uiMapID"),
        _float(fields[17], "bloc avancé, orientation"),
        _int(fields[18], "bloc avancé, niveau"),
    )


def _shape(name: str) -> tuple[str, str] | None:
    """(préfixe, suffixe) d'un nom d'événement connu, sinon None."""
    if name in SPECIAL:
        return SPECIAL[name]
    for prefix in _PREFIX_ORDER:
        rest = name[len(prefix) :]
        if name.startswith(prefix + "_") and rest in SUFFIXES:
            return prefix, rest
    return None


def is_known(name: str) -> bool:
    """Événement dont le format est connu (les autres sont gardés bruts)."""
    return name in CONTEXT_EVENTS or name in UNIT_EVENTS or _shape(name) is not None


def _event(number: int, time: datetime, row: list[str]) -> Event:
    name, raw = row[0], tuple(row)
    if name in CONTEXT_EVENTS:
        return Event(number, time, name, None, None, None, None, {}, raw)
    shape = _shape(name)
    if shape is None and name not in UNIT_EVENTS:
        return Event(number, time, name, None, None, None, None, {}, raw)  # inconnu : gardé brut
    if len(row) < 1 + UNIT_FIELDS:
        raise _Malformed(f"{name} : {len(row) - 1} champ(s), au moins {UNIT_FIELDS} attendus pour les unités")
    source, dest = _unit(row[1:5]), _unit(row[5:9])
    if shape is None:
        return Event(number, time, name, source, dest, None, None, {}, raw)
    prefix, suffix_name = shape
    has_advanced, names = SUFFIXES[suffix_name]
    if prefix == "ENVIRONMENTAL":
        names = ("environmental_type", *names)
    rest = row[1 + UNIT_FIELDS :]
    n_prefix = PREFIXES[prefix]
    needed = n_prefix + (ADVANCED_FIELDS if has_advanced else 0) + len(names)
    if len(rest) < needed:
        raise _Malformed(f"{name} : {len(rest)} champ(s) après les unités, au moins {needed} attendus")
    spell = None
    if n_prefix:
        spell = (_int(rest[0], "identifiant de sort"), rest[1], _int(rest[2], "école du sort"))
    rest = rest[n_prefix:]
    advanced = None
    if has_advanced:
        advanced, rest = _advanced(rest[:ADVANCED_FIELDS]), rest[ADVANCED_FIELDS:]
    suffix: dict[str, object] = {key: _value(token) for key, token in zip(names, rest, strict=False)}
    extra = rest[len(names) :]
    if suffix_name in ("_DAMAGE", "_DAMAGE_LANDED") and extra[:1] in (["ST"], ["AOE"]):
        suffix["aoe"] = extra[0] == "AOE"
        extra = extra[1:]
    if extra:
        suffix["extra"] = tuple(extra)
    return Event(number, time, name, source, dest, spell, advanced, suffix, raw)


def _header(path: Path, first: str) -> LogHeader:
    try:
        _, row = _split(first)
    except _Malformed as exc:
        raise UnsupportedLogError(str(path), f"en-tête illisible : {exc}") from exc
    values = dict(zip(row[0::2], row[1::2], strict=False))
    if row[:1] != ["COMBAT_LOG_VERSION"]:
        raise UnsupportedLogError(str(path), "première ligne sans COMBAT_LOG_VERSION")
    try:
        header = LogHeader(
            int(values["COMBAT_LOG_VERSION"]),
            values.get("ADVANCED_LOG_ENABLED") == "1",
            values.get("BUILD_VERSION", ""),
            int(values.get("PROJECT_ID", "0")),
        )
    except (KeyError, ValueError) as exc:
        raise UnsupportedLogError(str(path), "en-tête incomplet") from exc
    if header.version != SUPPORTED_VERSION:
        raise UnsupportedLogError(str(path), f"format {header.version}, seul le format {SUPPORTED_VERSION} est lu")
    if not header.advanced:
        raise UnsupportedLogError(str(path), "journal avancé désactivé (ADVANCED_LOG_ENABLED 0)")
    return header


def log_files(directory: Path) -> list[Path]:
    """Journaux d'un dossier (`WoWCombatLog-*.txt` et leur forme compressée `.txt.gz`), triés par nom."""
    return sorted({p for pattern in LOG_GLOBS for p in directory.glob(pattern)}, key=lambda p: p.name)


def _lines(path: Path) -> list[str]:
    try:
        data = path.read_bytes()
        if path.suffix == ".gz":
            data = gzip.decompress(data)
        return data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise DataSchemaError(f"{path} : encodage invalide (UTF-8 attendu).") from exc
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise DataSchemaError(f"{path} : compression gzip invalide ({exc}).") from exc


def read_log(path: Path) -> tuple[LogHeader, Iterator[Event]]:
    """(en-tête, événements dans l'ordre du fichier). `unsupported_log` si l'en-tête ne convient pas ; `data_schema`
    (fichier et ligne) au premier événement mal formé, levé pendant l'itération."""
    lines = _lines(path)
    if not lines or not lines[0].strip():
        raise UnsupportedLogError(str(path), "journal vide")
    header = _header(path, lines[0])

    def iterate() -> Iterator[Event]:
        for number, line in enumerate(lines[1:], start=2):
            if not line.strip():
                continue
            try:
                time, row = _split(line)
                yield _event(number, time, row)
            except _Malformed as exc:
                raise DataSchemaError(
                    f"{path.name}, ligne {number} : {exc}.",
                    "vérifier que le journal n'est pas tronqué (fichier encore ouvert par le jeu ?)",
                ) from exc

    return header, iterate()


def scan_logs(directory: Path) -> list[LogSummary]:
    """Résumé de chaque `WoWCombatLog-*.txt` du dossier (triés par nom) ; un journal illisible est listé avec
    son erreur."""
    out = []
    for path in log_files(directory):
        n_lines = 0
        try:
            n_lines = len(_lines(path))
            header, events = read_log(path)
            start = end = None
            count = 0
            mine: list[str] = []
            for e in events:
                count += 1
                start = start or e.time
                end = e.time
                for u in (e.source, e.dest):
                    if u is not None and u.is_mine and u.kind == "Player" and u.name and u.name not in mine:
                        mine.append(u.name)
            out.append(LogSummary(path.name, path, header, start, end, n_lines, count, mine, None))
        except (UnsupportedLogError, DataSchemaError) as err:
            out.append(LogSummary(path.name, path, None, None, None, n_lines, 0, [], err.message))
    return out
