"""Mesures tirées des journaux de combat : PV des monstres, coûts, intervalles entre sorts instantanés, durées
d'incantation, rapports de critique, touchés et ratés par écart de niveau.

Fonctions pures sur des événements déjà lus (`combatlog.read_log`) ; aucun seuil de jeu : la fenêtre d'enchaînement
des instantanés est un paramètre de mesure passé par l'appelant. Les écoles se lisent dans le masque d'école du
journal (format du fichier). Les motifs d'échec (`SPELL_CAST_FAILED`) sont localisés : jamais interprétés."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from itertools import pairwise
from typing import NamedTuple, TypedDict

from forever.pipeline.combatlog import Event, LogHeader, is_known

# Masque d'école du journal (format) -> nom d'école des données.
SCHOOLS = {1: "physical", 2: "holy", 4: "fire", 8: "nature", 16: "frost", 32: "shadow", 64: "arcane"}
DIRECT_DAMAGE = frozenset({"SPELL_DAMAGE", "RANGE_DAMAGE"})
DIRECT_MISSED = frozenset({"SPELL_MISSED", "RANGE_MISSED"})


class MonsterObservation(TypedDict):
    npc_id: int
    name: str
    level: int
    max_hp: int
    guids: int
    ui_map_id: int
    log: str


class Conflict(TypedDict):
    npc_id: int
    level: int
    values: list[int]
    log: str


class HitCount(TypedDict):
    hits: int
    misses: int
    by_type: dict[str, int]


class HitTally(NamedTuple):
    counts: dict[tuple[str, int], HitCount]
    assumptions: list[str]


def school_name(mask: int) -> str:
    """Nom d'une école simple ; masque combiné en hexadécimal (`0x14` pour givrefeu)."""
    return SCHOOLS.get(mask, f"{mask:#x}")


def find_mine(events: Iterable[Event]) -> str | None:
    """GUID du joueur qui journalise (premier joueur « à moi » rencontré)."""
    for e in events:
        for u in (e.source, e.dest):
            if u is not None and u.is_mine and u.kind == "Player":
                return u.guid
    return None


def unit_name(events: Iterable[Event], guid: str) -> str | None:
    for e in events:
        for u in (e.source, e.dest):
            if u is not None and u.guid == guid and u.name:
                return u.name
    return None


def monster_hp(events: Iterable[Event], *, log: str = "") -> tuple[list[MonsterObservation], list[Conflict]]:
    """PV max par (PNJ, niveau), lus dans le bloc avancé qui décrit une créature. Une seule valeur observée :
    observation ; plusieurs valeurs au même niveau : conflit listé, jamais moyenné."""
    values: dict[tuple[int, int], set[int]] = defaultdict(set)
    guids: dict[tuple[int, int], set[str]] = defaultdict(set)
    names: dict[tuple[int, int], str] = {}
    maps: dict[tuple[int, int], int] = {}
    for e in events:
        adv = e.advanced
        if adv is None:
            continue
        unit = next((u for u in (e.source, e.dest) if u is not None and u.guid == adv.guid), None)
        if unit is None or unit.kind != "Creature" or unit.npc_id is None:
            continue
        key = (unit.npc_id, adv.level)
        values[key].add(adv.max_hp)
        guids[key].add(adv.guid)
        names.setdefault(key, unit.name or "")
        maps.setdefault(key, adv.ui_map_id)
    observations: list[MonsterObservation] = []
    conflicts: list[Conflict] = []
    for key in sorted(values):
        npc_id, level = key
        if len(values[key]) > 1:
            conflicts.append({"npc_id": npc_id, "level": level, "values": sorted(values[key]), "log": log})
            continue
        observations.append(
            {
                "npc_id": npc_id,
                "name": names[key],
                "level": level,
                "max_hp": next(iter(values[key])),
                "guids": len(guids[key]),
                "ui_map_id": maps[key],
                "log": log,
            }
        )
    return observations, conflicts


def spell_costs(events: Iterable[Event], caster: str) -> dict[int, set[int]]:
    """Sort -> coûts relevés sur `SPELL_CAST_SUCCESS` (bloc avancé du lanceur)."""
    costs: dict[int, set[int]] = defaultdict(set)
    for e in events:
        if (
            e.name == "SPELL_CAST_SUCCESS"
            and e.source is not None
            and e.source.guid == caster
            and e.spell is not None
            and e.advanced is not None
            and e.advanced.guid == caster
        ):
            costs[e.spell[0]].add(e.advanced.power_cost)
    return dict(costs)


class _Cast(NamedTuple):
    event: Event
    spell: int
    started: Event | None  # START qui a ouvert l'incantation ; None pour un instantané


def _casts(events: Iterable[Event], caster: str) -> list[_Cast]:
    """Sorts réussis du lanceur, dans l'ordre. Un START ouvre une incantation (il remplace toute incantation en
    cours) ; le SUCCESS suivant du même sort la clôt. Un échec ne l'annule pas : le motif est localisé et un échec
    qui suit le START de quelques millisecondes vise un second appui, pas le sort en cours."""
    pending: dict[int, Event] = {}
    out: list[_Cast] = []
    for e in events:
        if e.source is None or e.source.guid != caster or e.spell is None:
            continue
        spell = e.spell[0]
        if e.name == "SPELL_CAST_START":
            pending = {spell: e}
        elif e.name == "SPELL_CAST_SUCCESS":
            out.append(_Cast(e, spell, pending.get(spell)))
            pending = {}
    return out


def gcd_intervals(events: Iterable[Event], caster: str, *, max_gap_s: float) -> list[float]:
    """Intervalles (s) entre deux sorts instantanés réussis consécutifs du lanceur, dans l'ordre chronologique ; un
    intervalle plus long que `max_gap_s` (paramètre de mesure) n'est pas un enchaînement et n'est pas retenu.

    Sert de preuve de journal à l'entrée B1 du registre."""
    casts = _casts(events, caster)
    out = []
    for prev, cur in pairwise(casts):
        if prev.started is None and cur.started is None:
            gap = (cur.event.time - prev.event.time).total_seconds()
            if gap <= max_gap_s:
                out.append(gap)
    return out


def cast_times(events: Iterable[Event], caster: str) -> dict[int, list[float]]:
    """Sort -> durées START -> SUCCESS (s) des incantations du lanceur."""
    out: dict[int, list[float]] = defaultdict(list)
    for c in _casts(events, caster):
        if c.started is not None:
            out[c.spell].append((c.event.time - c.started.time).total_seconds())
    return dict(out)


def crit_ratios(events: Iterable[Event], caster: str) -> list[tuple[int, float]]:
    """(sort, montant / montant d'origine) de chaque coup critique du lanceur."""
    out = []
    for e in events:
        if not e.name.endswith("_DAMAGE") or e.source is None or e.source.guid != caster or e.spell is None:
            continue
        amount, base = e.suffix.get("amount"), e.suffix.get("base_amount")
        if e.suffix.get("critical") and isinstance(amount, int | float) and isinstance(base, int | float) and base:
            out.append((e.spell[0], amount / base))
    return out


def hit_tally(events: Iterable[Event], caster: str, caster_level: int | None) -> HitTally:
    """Touchés et ratés des sorts directs du lanceur sur des créatures, par (école, niveau de la cible - niveau du
    lanceur). Sans niveau du lanceur (ForeverLoggerDB), rien n'est compté.

    Sert de preuve de journal à l'entrée A3 du registre."""
    if caster_level is None:
        return HitTally({}, ["niveau du lanceur inconnu (ForeverLoggerDB absent) : touchés et ratés non comptés"])
    levels: dict[str, int] = {}
    counts: dict[tuple[str, int], HitCount] = {}
    unknown = 0
    for e in events:
        if e.advanced is not None:
            levels[e.advanced.guid] = e.advanced.level
        if e.source is None or e.source.guid != caster or e.dest is None or e.dest.kind != "Creature":
            continue
        if e.spell is None or e.name not in DIRECT_DAMAGE | DIRECT_MISSED:
            continue
        target = levels.get(e.dest.guid)
        if target is None:
            unknown += 1
            continue
        key = (school_name(e.spell[2]), target - caster_level)
        count = counts.setdefault(key, {"hits": 0, "misses": 0, "by_type": {}})
        if e.name in DIRECT_DAMAGE:
            count["hits"] += 1
        else:
            count["misses"] += 1
            miss_type = str(e.suffix.get("miss_type"))
            count["by_type"][miss_type] = count["by_type"].get(miss_type, 0) + 1
    notes = [f"{unknown} sort(s) sur une cible de niveau inconnu non compté(s)"] if unknown else []
    return HitTally(counts, notes)


class GcdIntervals(TypedDict):
    values: list[float]
    n: int
    min: float | None
    max_gap_s: float


class LogMeasures(TypedDict):
    name: str
    header: dict[str, object]
    caster: dict[str, str | None] | None
    events: int
    unknown_events: list[str]
    monsters: list[MonsterObservation]
    conflicts: list[Conflict]
    costs: dict[str, list[int]]
    gcd_intervals: GcdIntervals
    cast_times: dict[str, list[float]]
    crits: list[dict[str, int | float]]
    hit_tally: list[dict[str, object]]
    assumptions: list[str]


def measure_log(
    header: LogHeader, events: list[Event], *, name: str, max_gap_s: float, caster_level: int | None = None
) -> LogMeasures:
    """Toutes les mesures d'un journal, pour le joueur « à moi » (sérialisables en JSON)."""
    caster = find_mine(events)
    unknown = sorted({e.name for e in events if not is_known(e.name)})
    notes: list[str] = []
    if caster is None:
        notes.append("aucun joueur « à moi » dans le journal : mesures du lanceur vides")
    guid = caster or ""
    intervals = gcd_intervals(events, guid, max_gap_s=max_gap_s)
    tally = hit_tally(events, guid, caster_level)
    monsters, conflicts = monster_hp(events, log=name)
    return {
        "name": name,
        "header": header._asdict(),
        "caster": {"guid": caster, "name": unit_name(events, caster)} if caster else None,
        "events": len(events),
        "unknown_events": unknown,
        "monsters": monsters,
        "conflicts": conflicts,
        "costs": {str(k): sorted(v) for k, v in sorted(spell_costs(events, guid).items())},
        "gcd_intervals": {
            "values": intervals,
            "n": len(intervals),
            "min": min(intervals, default=None),
            "max_gap_s": max_gap_s,
        },
        "cast_times": {str(k): v for k, v in sorted(cast_times(events, guid).items())},
        "crits": [{"spell_id": s, "ratio": r} for s, r in crit_ratios(events, guid)],
        "hit_tally": [
            {"school": school, "level_diff": diff, **count} for (school, diff), count in sorted(tally.counts.items())
        ],
        "assumptions": [*notes, *tally.assumptions],
    }
