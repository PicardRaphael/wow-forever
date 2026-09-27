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

from forever.engine.model import GameData
from forever.pipeline.combatlog import NO_GUID, Event, LogHeader, is_known
from forever.pipeline.levels import CasterLevels

# Masque d'école du journal (format) -> nom d'école des données.
SCHOOLS = {1: "physical", 2: "holy", 4: "fire", 8: "nature", 16: "frost", 32: "shadow", 64: "arcane"}
DIRECT_DAMAGE = frozenset({"SPELL_DAMAGE", "RANGE_DAMAGE"})
DIRECT_MISSED = frozenset({"SPELL_MISSED", "RANGE_MISSED"})
# Types de raté du journal qui relèvent de la table de toucher des sorts (les autres : ABSORB, IMMUNE, EVADE…,
# restent comptés à part dans `by_type`).
HIT_TABLE_MISSES = frozenset({"MISS", "RESIST"})


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
        if unit is None or unit.kind != "Creature" or unit.npc_id is None or adv.owner != NO_GUID:
            continue  # créature invoquée (totem, gardien…) : propriétaire non nul
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


def gcd_intervals(
    events: Iterable[Event], caster: str, *, max_gap_s: float, gcd_spells: frozenset[int] | None = None
) -> list[float]:
    """Intervalles (s) entre deux sorts instantanés réussis consécutifs du lanceur, dans l'ordre chronologique ; un
    intervalle plus long que `max_gap_s` (paramètre de mesure) n'est pas un enchaînement et n'est pas retenu.
    Avec `gcd_spells`, les deux sorts doivent en faire partie (sorts qui déclenchent la recharge globale) : un sort
    hors de l'ensemble (baguette, sort hors recharge globale) rompt l'enchaînement.

    Sert de preuve de journal à l'entrée B1 du registre."""
    casts = _casts(events, caster)
    out = []
    for prev, cur in pairwise(casts):
        if gcd_spells is not None and (prev.spell not in gcd_spells or cur.spell not in gcd_spells):
            continue
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


def hit_tally(
    events: Iterable[Event],
    caster: str,
    caster_level: CasterLevels | int | None,
    *,
    known_spells: frozenset[int] | None = None,
) -> HitTally:
    """Touchés et ratés des sorts directs du lanceur sur des créatures, par (école, niveau de la cible - niveau du
    lanceur à l'instant du sort). Niveau : chronologie (`CasterLevels`) ou niveau fixe ; sans niveau, rien n'est
    compté. Avec `known_spells`, seuls ces sorts comptent (ni baguette, ni effets déclenchés comme Chilled).

    Sert de preuve de journal à l'entrée A3 du registre."""
    if caster_level is None:
        return HitTally({}, ["niveau du lanceur inconnu (ForeverLoggerDB absent) : touchés et ratés non comptés"])
    levels = CasterLevels(fixed=caster_level) if isinstance(caster_level, int) else caster_level
    evs = list(events)
    targets: dict[str, int] = {}
    for e in evs:  # d'abord les niveaux : un raté n'a pas de bloc avancé, la cible peut n'être décrite qu'après
        if e.advanced is not None:
            targets.setdefault(e.advanced.guid, e.advanced.level)
    counts: dict[tuple[str, int], HitCount] = {}
    unknown = no_level = excluded = 0
    sources: dict[str, int] = {}
    for e in evs:
        if e.source is None or e.source.guid != caster or e.dest is None or e.dest.kind != "Creature":
            continue
        if e.spell is None or e.name not in DIRECT_DAMAGE | DIRECT_MISSED:
            continue
        if known_spells is not None and e.spell[0] not in known_spells:
            excluded += 1
            continue
        target = targets.get(e.dest.guid)
        if target is None:
            unknown += 1
            continue
        own = levels.level_at(e.time)
        if own is None:
            no_level += 1
            continue
        sources[own[1]] = sources.get(own[1], 0) + 1
        key = (school_name(e.spell[2]), target - own[0])
        count = counts.setdefault(key, {"hits": 0, "misses": 0, "by_type": {}})
        if e.name in DIRECT_DAMAGE:
            count["hits"] += 1
        else:
            miss_type = str(e.suffix.get("miss_type"))
            count["by_type"][miss_type] = count["by_type"].get(miss_type, 0) + 1
            if miss_type in HIT_TABLE_MISSES:
                count["misses"] += 1
    notes = [f"{unknown} sort(s) sur une cible de niveau inconnu non compté(s)"] if unknown else []
    if no_level:
        notes.append(f"{no_level} sort(s) avant tout niveau connu : niveau du lanceur inconnu, non compté(s)")
    if excluded:
        notes.append(f"{excluded} sort(s) absent(s) des données (baguette, effets déclenchés) exclu(s)")
    if sources and isinstance(caster_level, CasterLevels):
        notes.append("niveau du lanceur : " + ", ".join(f"{src} ({n} sort(s))" for src, n in sorted(sources.items())))
    return HitTally(counts, notes)


class LogSpellSets(NamedTuple):
    gcd: frozenset[int]  # rangs dont `start_recovery_ms` > 0 (déclenchent la recharge globale)
    known: frozenset[int]  # rangs et sorts déclenchés suivis par les données (`spell_scaling.json`)


def log_spell_sets(gd: GameData) -> LogSpellSets:
    """Sorts du lanceur retenus par les mesures, tirés des données de la version (aucun identifiant en dur)."""
    ranks = [r for ranks in gd.scaling.values() for r in ranks]
    known = {r.spell_id for r in ranks} | {c.spell_id for r in ranks for c in r.components}
    return LogSpellSets(frozenset(r.spell_id for r in ranks if r.start_recovery_ms > 0), frozenset(known))


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
    caster_level: int | None
    caster_level_changes: list[dict[str, object]]
    player_level_field: list[int]
    assumptions: list[str]


def measure_log(
    header: LogHeader,
    events: list[Event],
    *,
    name: str,
    max_gap_s: float,
    caster_level: CasterLevels | int | None = None,
    spells: LogSpellSets | None = None,
) -> LogMeasures:
    """Toutes les mesures d'un journal, pour le joueur « à moi » (sérialisables en JSON)."""
    caster = find_mine(events)
    unknown = sorted({e.name for e in events if not is_known(e.name)})
    notes: list[str] = []
    if caster is None:
        notes.append("aucun joueur « à moi » dans le journal : mesures du lanceur vides")
    guid = caster or ""
    intervals = gcd_intervals(events, guid, max_gap_s=max_gap_s, gcd_spells=spells.gcd if spells else None)
    tally = hit_tally(events, guid, caster_level, known_spells=spells.known if spells else None)
    monsters, conflicts = monster_hp(events, log=name)
    levels = CasterLevels(fixed=caster_level) if isinstance(caster_level, int) else caster_level
    start = levels.level_at(events[0].time) if levels and events else None
    changes: list[dict[str, object]] = []
    if levels and events:
        previous = start
        moments = sorted({t for tl in levels.timelines for t, _ in tl.points if events[0].time < t <= events[-1].time})
        for t in moments:
            now = levels.level_at(t)
            if now is not None and (previous is None or now[0] != previous[0]):
                changes.append({"time": t.isoformat(), "level": now[0], "source": now[1]})
            previous = now
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
        "caster_level": start[0] if start else None,
        "caster_level_changes": changes,
        "player_level_field": sorted(
            {e.advanced.level for e in events if e.advanced is not None and caster and e.advanced.guid == caster}
        ),
        "assumptions": [*notes, *tally.assumptions],
    }


class IgniteObservation(TypedDict):
    """Critiques de feu du lanceur sur une cible et tics d'Ignite qui suivent (instants en s depuis le premier
    critique de l'épisode, dégâts)."""

    target: str
    crits: list[tuple[float, float]]
    ticks: list[tuple[float, float]]


def ignite_ticks(
    events: Iterable[Event], caster: str, *, ignite_spell: int, window_s: float
) -> list[IgniteObservation]:
    """Épisodes d'Ignite du lanceur : un épisode s'arrête après `window_s` sans critique ni tic sur la cible."""
    raise NotImplementedError
