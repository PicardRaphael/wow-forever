"""Lecture de la SavedVariable `ForeverLoggerDB` de l'addon ForeverLogger (fichier
`WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua`), sans exécuter de Lua ni accéder au réseau.

Contenu (addon/README.md) : par GUID de personnage, des instantanés (connexion, gain de niveau, changement de talents)
et les gains d'expérience, horodatés en heure du serveur (`time`) et en heure locale (`localtime`, même format que
les journaux de combat). La jointure avec un journal se fait par GUID et heure locale.

CH0 : instantanés du familier du Chasseur et des statistiques du Chasseur (`pet_snapshots`), relevés de la fenêtre
Beast Training (`training`) ; les retours multiples d'une API sont gardés par position (`{1: …, 2: …}`), un trou
pour une valeur secrète ou absente.

T04d (0.4.0, schéma 2) : montant et cible de chaque gain d'XP, états de l'XP et du repos (`xp_states`), quêtes
acceptées et rendues (`quests`) ; les anciennes entrées restent lues (montant tiré du texte)."""

from __future__ import annotations

import re
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
    trivial_range: int | None = None  # UnitQuestTrivialLevelRange (0.4.0)
    state: dict[str, Any] = {}  # noqa: RUF012 : xp, max, rested, rest_state (0.4.0)
    resting: bool | None = None


class ParsedXp(NamedTuple):
    amount: int | None
    kind: str  # "monster", "other" ou "unknown"
    monster: str | None
    group_bonus: int | None
    rested_bonus: int | None
    extra: str


_NUMBER = r"(\d[\d,]*)"
_GAIN_FORMS = (
    re.compile(rf"^(?P<monster>.+?) dies, you gain {_NUMBER} experience\.\s*(?P<extra>.*)$"),
    re.compile(rf"^(?P<monster>.+?) meurt, vous gagnez {_NUMBER} points d'expérience\.\s*(?P<extra>.*)$"),
    re.compile(rf"^You gain {_NUMBER} experience\.\s*(?P<extra>.*)$"),
    re.compile(rf"^Vous gagnez {_NUMBER} points d'expérience\.\s*(?P<extra>.*)$"),
)
_GROUP_BONUS = re.compile(r"\+(\d[\d,]*) group bonus")
_RESTED_BONUS = re.compile(r"\+(\d[\d,]*) exp Rested bonus")


def _count(raw: str) -> int:
    return int(raw.replace(",", ""))


def parse_xp_text(text: str) -> ParsedXp:
    """Montant, monstre et bonus d'un texte de `CHAT_MSG_COMBAT_XP_GAIN` (formes anglaises et françaises relevées ;
    bonus de repos sous sa forme de Classic, `(+N exp Rested bonus)`, non encore vue sur Forever : LVL10). Le texte
    qui suit la première phrase est gardé tel quel dans `extra` ; une forme inconnue donne `unknown`, sans montant.
    Le montant est celui du texte : l'inclusion des bonus n'est pas tranchée ici (règles du modèle d'XP)."""
    for form in _GAIN_FORMS:
        match = form.match(text.strip())
        if match is None:
            continue
        groups = match.groupdict()
        extra = groups["extra"].strip()
        group = _GROUP_BONUS.search(extra)
        rested = _RESTED_BONUS.search(extra)
        return ParsedXp(
            _count(match.group(2) if groups.get("monster") else match.group(1)),
            "monster" if groups.get("monster") else "other",
            groups.get("monster"),
            _count(group.group(1)) if group else None,
            _count(rested.group(1)) if rested else None,
            extra,
        )
    return ParsedXp(None, "unknown", None, None, None, "")


class XpGain(NamedTuple):
    """Gain d'XP ; les champs après `text` viennent de ForeverLogger 0.4.0 (absents des anciennes entrées, sauf ceux
    lus dans le texte)."""

    time: int | None
    localtime: datetime | None
    level: int | None
    text: str
    seq: int | None = None
    amount: int | None = None
    kind: str = "unknown"
    monster: str | None = None
    group_bonus: int | None = None
    rested_bonus: int | None = None
    extra: str = ""
    target: dict[str, Any] | None = None  # name, level, classification, npc, creature_type, source
    seen_levels: list[int] = []  # noqa: RUF012 : NamedTuple, jamais modifiée
    state: dict[str, Any] = {}  # noqa: RUF012 : xp, max, rested, rest_state au moment du message
    resting: bool | None = None
    instance: dict[str, Any] = {}  # noqa: RUF012 : inside, type, name, id
    group: dict[str, Any] = {}  # noqa: RUF012 : size, raid, levels
    map: int | None = None


class XpState(NamedTuple):
    """État de l'XP relevé à la connexion, au gain de niveau, à chaque `PLAYER_XP_UPDATE` (`xp`) et à chaque
    changement du repos (`repos`)."""

    seq: int | None
    reason: str
    time: int | None
    localtime: datetime | None
    level: int | None
    xp: int | None
    max: int | None
    rested: int | None
    rest_state: int | None
    resting: bool | None


class QuestEvent(NamedTuple):
    """Quête acceptée (`QUEST_ACCEPTED`) ou rendue (`QUEST_TURNED_IN`, avec `xp_reward` et `money_reward`)."""

    event: str
    quest_id: int
    seq: int | None
    time: int | None
    localtime: datetime | None
    level: int | None
    title: str | None
    quest_level: int | None
    xp_reward: int | None
    money_reward: int | None
    state: dict[str, Any]
    resting: bool | None
    map: int | None
    instance: dict[str, Any]
    group: dict[str, Any]


class PetSnapshot(NamedTuple):
    reason: str
    time: int | None
    localtime: datetime | None
    level: int | None  # niveau du Chasseur
    pet: dict[str, Any]  # famille, niveau, PV maximaux, armure, vitesse, puissance d'attaque, loyauté, régime…
    hunter: dict[str, Any]  # Endurance, armure, puissance d'attaque (mêlée, distance), critique


class TrainingWindow(NamedTuple):
    time: int | None
    localtime: datetime | None
    skill_line: str | None
    family: str | None
    pet_level: int | None
    entries: list[dict[str, Any]]  # name, rank, type, cost, level


class Character(NamedTuple):
    guid: str
    name: str | None
    realm: str | None
    class_: str | None
    race: str | None
    snapshots: list[Snapshot]
    xp: list[XpGain]
    pet_snapshots: list[PetSnapshot] = []  # noqa: RUF012 : NamedTuple, jamais modifiée
    training: list[TrainingWindow] = []  # noqa: RUF012
    xp_states: list[XpState] = []  # noqa: RUF012
    quest_accepts: list[QuestEvent] = []  # noqa: RUF012
    quest_turnins: list[QuestEvent] = []  # noqa: RUF012


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


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _plain(value: Any) -> Any:
    """Table Lua lue -> valeurs Python : liste (ou table à positions entières) -> liste, table -> dict."""
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        if value and all(isinstance(k, int) and not isinstance(k, bool) for k in value):
            return [_plain(v) for v in _list(value)]
        return {str(k): _plain(v) for k, v in value.items()}
    return value


def _table(value: Any) -> dict[str, Any]:
    plain = _plain(value)
    return plain if isinstance(plain, dict) else {}


def _int_list(value: Any) -> list[int]:
    return [v for v in _list(value) if isinstance(v, int) and not isinstance(v, bool)]


def _str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _numbers(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {str(k): float(v) for k, v in value.items() if isinstance(v, int | float) and not isinstance(v, bool)}


def _returns(value: Any) -> Any:
    """Retours multiples d'une API gardés par position : liste ou table à trous -> {position: valeur}."""
    if isinstance(value, list):
        return {i: v for i, v in enumerate(value, start=1) if v is not None}
    if isinstance(value, dict) and all(isinstance(k, int) for k in value):
        return dict(sorted(value.items()))
    return value


def _state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(k): _returns(v) for k, v in value.items()}


def _localtime(value: Any, path: Path) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.strptime(str(value), LOCAL_TIME_FORMAT)  # noqa: DTZ007 : heure locale du client
    except ValueError as exc:
        raise DataSchemaError(f"{path.name} : heure locale illisible « {value} ».") from exc


def _xp_gain(x: dict[str, Any], path: Path) -> XpGain:
    text = str(x.get("text", ""))
    parsed = parse_xp_text(text)
    target = x.get("target")
    return XpGain(
        _opt_int(x.get("time")),
        _localtime(x.get("localtime"), path),
        _opt_int(x.get("level")),
        text,
        seq=_opt_int(x.get("seq")),
        amount=parsed.amount if parsed.amount is not None else _opt_int(x.get("amount")),
        kind=parsed.kind if parsed.kind != "unknown" else (_str(x.get("kind")) or "unknown"),
        monster=parsed.monster or _str(x.get("monster")),
        group_bonus=parsed.group_bonus,
        rested_bonus=parsed.rested_bonus,
        extra=parsed.extra,
        target=_table(target) if isinstance(target, dict) else None,
        seen_levels=_int_list(x.get("seen_levels")),
        state=_table(x.get("state")),
        resting=_bool(x.get("resting")),
        instance=_table(x.get("instance")),
        group=_table(x.get("group")),
        map=_opt_int(x.get("map")),
    )


def _xp_state(s: dict[str, Any], path: Path) -> XpState:
    return XpState(
        seq=_opt_int(s.get("seq")),
        reason=_str(s.get("reason")) or "",
        time=_opt_int(s.get("time")),
        localtime=_localtime(s.get("localtime"), path),
        level=_opt_int(s.get("level")),
        xp=_opt_int(s.get("xp")),
        max=_opt_int(s.get("max")),
        rested=_opt_int(s.get("rested")),
        rest_state=_opt_int(s.get("rest_state")),
        resting=_bool(s.get("resting")),
    )


def _quest_event(q: dict[str, Any], path: Path) -> QuestEvent:
    return QuestEvent(
        event=_str(q.get("event")) or "",
        quest_id=int(q["quest_id"]),
        seq=_opt_int(q.get("seq")),
        time=_opt_int(q.get("time")),
        localtime=_localtime(q.get("localtime"), path),
        level=_opt_int(q.get("level")),
        title=_str(q.get("title")),
        quest_level=_opt_int(q.get("quest_level")),
        xp_reward=_opt_int(q.get("xp_reward")),
        money_reward=_opt_int(q.get("money_reward")),
        state=_table(q.get("state")),
        resting=_bool(q.get("resting")),
        map=_opt_int(q.get("map")),
        instance=_table(q.get("instance")),
        group=_table(q.get("group")),
    )


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
                    else ({} if talents == [] else None),  # table vide : lue comme liste
                    spell_bonus=_numbers(s.get("spell_bonus")),
                    spell_crit=_numbers(s.get("spell_crit")),
                    trivial_range=_opt_int(s.get("trivial_range")),
                    state=_table(s.get("state")),
                    resting=_bool(s.get("resting")),
                )
            )
        xp = [_xp_gain(x, path) for x in _list(c.get("xp")) if isinstance(x, dict)]
        states = [_xp_state(s, path) for s in _list(c.get("xp_states")) if isinstance(s, dict)]
        quests = [
            _quest_event(q, path)
            for q in _list(c.get("quests"))
            if isinstance(q, dict) and _opt_int(q.get("quest_id")) is not None
        ]
        pets = [
            PetSnapshot(
                reason=_str(s.get("reason")) or "",
                time=_opt_int(s.get("time")),
                localtime=_localtime(s.get("localtime"), path),
                level=_opt_int(s.get("level")),
                pet=_state(s.get("pet")),
                hunter=_state(s.get("hunter")),
            )
            for s in _list(c.get("pet_snapshots"))
            if isinstance(s, dict)
        ]
        training = [
            TrainingWindow(
                time=_opt_int(t.get("time")),
                localtime=_localtime(t.get("localtime"), path),
                skill_line=_str(t.get("skill_line")),
                family=_str(t.get("family")),
                pet_level=_opt_int(t.get("pet_level")),
                entries=[dict(e) for e in _list(t.get("entries")) if isinstance(e, dict)],
            )
            for t in _list(c.get("training"))
            if isinstance(t, dict)
        ]
        characters[guid] = Character(
            guid,
            _str(c.get("name")),
            _str(c.get("realm")),
            _str(c.get("class")),
            _str(c.get("race")),
            snapshots,
            xp,
            pets,
            training,
            states,
            [q for q in quests if q.event == "accepted"],
            [q for q in quests if q.event == "turned_in"],
        )
    return LoggerDB(_opt_int(raw.get("schema")), characters)
