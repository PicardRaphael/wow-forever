"""`forever measures refresh` : relance toutes les mesures sur les journaux et SavedVariables présents sur disque,
compare au `monsters.json` installé, aux preuves du registre et au dernier instantané, puis écrit après accord.

Écritures (après confirmation seulement) : `monsters.json` de la version installée, le champ `source` de son entrée
dans `sources.json`, le manifeste, et un instantané des autres mesures dans le cache (`<cache>/measures/last.json`, état de l'outil). Les preuves du registre ne sont jamais
écrites : l'écart et le bloc `preuves` proposé s'affichent. Les PNJ d'un journal disparu du dossier sont conservés.
Lecture sur disque uniquement, jamais de réseau."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import CHAIN_MAX_GAP_S
from forever.engine.damage import predict_ignite_ticks
from forever.engine.model import GameData
from forever.errors import ForeverError, InvalidArgumentError
from forever.manifest import SOURCES_NAME, write_manifest
from forever.pipeline.addon_sv import LoggerDB, read_logger_db
from forever.pipeline.combatlog import log_files, read_log
from forever.pipeline.levels import CasterLevels, from_logger_db, from_questie_journey, logger_utc_offset
from forever.pipeline.measure import (
    Conflict,
    IgniteObservation,
    MonsterObservation,
    cast_times,
    crit_ratios,
    find_mine,
    gcd_intervals,
    hit_tally,
    ignite_ticks,
    log_spell_sets,
    monster_hp,
    spell_costs,
)
from forever.pipeline.monsters import MONSTERS_FILE, build_monsters
from forever.pipeline.questie import QuestieDB
from forever.registry import Mechanic

SNAPSHOT_DIR = "measures"
SNAPSHOT_NAME = "last.json"
LOGGER_SV, QUESTIE_SV = "ForeverLogger.lua", "Questie.lua"
SV_NAMES = (LOGGER_SV, QUESTIE_SV)
MEASURE_KEYS = ("sources", "b1", "a3", "costs", "cast_times", "crits", "ignite")
OTHER_MEASURES = ("costs", "cast_times", "crits")
B1_ID = "B1"
DECILES = 10  # statistics.quantiles : 10e percentile = premier décile (méthode de la preuve B1)
SOURCE_FIELD = re.compile(r'"source":\s*("(?:[^"\\]|\\.)*")')
SOURCE_RE = re.compile(r"^journal (?P<logs>.+) \(bloc avancé, (?P<guids>\d+) individu")
NO_IGNITE = "aucune mesure : pas de critique de feu suivi de tics d'Ignite dans les journaux"
IGNITE_NOTE = "écarts entre tics relevés et prédits (règle des données : rolling ; variante : keep_timer)"
A3_NOTE = "aucune preuve A3 enregistrée au registre (écarts affichés seulement)"

MeasureSnapshot = dict[str, Any]
RefreshDiff = dict[str, Any]


class RefreshSources(NamedTuple):
    logs: tuple[Path, ...]
    saved_variables: tuple[Path, ...]


def collect_sources(logs_dir: Path, sv_dir: Path | None = None) -> RefreshSources:
    """Journaux (`WoWCombatLog-*.txt[.gz]`) et SavedVariables utiles (ForeverLogger, Questie) trouvés."""
    if not logs_dir.is_dir():
        raise InvalidArgumentError(
            f"Dossier des journaux introuvable : {logs_dir}.", "donner --logs ou définir FOREVER_WOW_DIR"
        )
    logs = tuple(log_files(logs_dir))
    if not logs:
        raise InvalidArgumentError(
            f"Aucun journal WoWCombatLog-*.txt dans {logs_dir}.", "vérifier --logs (dossier Logs du client)"
        )
    found = tuple(sv_dir / name for name in SV_NAMES if (sv_dir / name).is_file()) if sv_dir else ()
    return RefreshSources(logs, found)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _kept_observations(
    installed: Mapping[str, Any], present: set[str], measured: set[tuple[int, int]]
) -> tuple[list[MonsterObservation], list[str], list[str]]:
    """Observations reconstituées depuis `monsters.json` installé pour les PNJ vus seulement dans des journaux
    disparus du dossier : (observations, PNJ conservés, journaux disparus utilisés)."""
    gone = set(installed.get("logs", [])) - present
    observations: list[MonsterObservation] = []
    kept: set[str] = set()
    used: set[str] = set()
    for npc_id, entry in installed.get("npcs", {}).items():
        for level, row in entry.get("levels", {}).items():
            match = SOURCE_RE.match(str(row.get("source", "")))
            if match is None or (int(npc_id), int(level)) in measured:
                continue
            names = match["logs"].split(", ")
            if not all(name in gone for name in names):
                continue
            for i, name in enumerate(names):
                observations.append(
                    {
                        "npc_id": int(npc_id),
                        "name": entry["name"],
                        "level": int(level),
                        "max_hp": int(row["max_hp"]),
                        "guids": int(match["guids"]) if i == 0 else 0,
                        "ui_map_id": 0,
                        "log": name,
                    }
                )
            kept.add(npc_id)
            used |= set(names)
    return observations, sorted(kept, key=int), sorted(used)


def _levels(db: LoggerDB | None, questie_sv: Path | None, mine: str, offset: timedelta | None) -> CasterLevels | None:
    """Niveau du lanceur : ForeverLogger, puis carnet de Questie (décalage donné, sinon celui de ForeverLogger)."""
    timelines = []
    if db is not None:
        timelines.append(from_logger_db(db, mine))
    if questie_sv is not None:
        journey_offset = offset if offset is not None else (logger_utc_offset(db, mine) if db is not None else None)
        timelines.append(from_questie_journey(questie_sv, mine, utc_offset=journey_offset))
    return CasterLevels(tuple(timelines)) if timelines else None


def _b1(gd: GameData, intervals: list[float]) -> dict[str, Any]:
    n = len(intervals)
    if n < 2:
        return {"n": n}
    median = statistics.median(intervals)
    p10 = statistics.quantiles(intervals, n=DECILES)[0]
    gcd = gd.rules.gcd_s
    return {"n": n, "median_s": median, "p10_s": p10, "ecart_median_s": abs(median - gcd), "ecart_p10_s": gcd - p10}


def _gap(observed: Sequence[Sequence[float]], predicted: Sequence[Sequence[float]]) -> dict[str, Any]:
    pairs = list(zip(observed, predicted, strict=False))
    return {
        "ticks": len(predicted),
        "max_time_gap_s": max((abs(o[0] - q[0]) for o, q in pairs), default=0.0),
        "max_amount_gap": max((abs(o[1] - q[1]) for o, q in pairs), default=0.0),
    }


def _ignite(gd: GameData, episodes: list[IgniteObservation]) -> list[dict[str, Any]]:
    """Épisodes relevés comparés à la règle des données et à la variante qui garde le compteur de tics ; part
    d'Ignite estimée sur l'épisode (somme des tics / somme des critiques, conservée par les deux variantes)."""
    out = []
    for e in episodes:
        crit_sum = sum(amount for _, amount in e["crits"])
        part = sum(amount for _, amount in e["ticks"]) / crit_sum if crit_sum else 0.0
        out.append(
            {
                **e,
                "part": part,
                "rolling": _gap(e["ticks"], predict_ignite_ticks(gd, e["crits"], part)),
                "keep_timer": _gap(e["ticks"], predict_ignite_ticks(gd, e["crits"], part, keep_timer=True)),
            }
        )
    return out


def curve_exclusions(
    installed: Mapping[str, Any], new_ids: Collection[int] | None, reason: str | None
) -> dict[int, str]:
    """PNJ écartés de la courbe des PV par niveau : ceux de `monsters.json` installé (avec leur raison), plus
    `new_ids` avec `reason` (obligatoire : un écart sans raison n'est jamais écrit)."""
    out = {int(e["npc_id"]): str(e["reason"]) for e in installed.get("curve_excluded", []) or []}
    if new_ids:
        if not reason:
            raise ValueError("--curve-exclude demande une raison (--curve-exclude-reason)")
        out |= {int(n): reason for n in new_ids}
    return out


def remeasure(
    gd: GameData,
    sources: RefreshSources,
    questie: QuestieDB | None,
    *,
    version: str,
    installed: Mapping[str, Any] | None = None,
    fit_exclude: Collection[int] = (),
    curve_exclude: Mapping[int, str] | None = None,
    utc_offset: timedelta | None = None,
) -> MeasureSnapshot:
    """Nouvelles mesures : table des monstres (PNJ des journaux disparus conservés), B1, A3, coûts, incantations,
    critiques, épisodes d'Ignite. Rendu sous forme JSON (clés en texte), comparable à un instantané relu."""
    notes: list[str] = []
    svs = {p.name: p for p in sources.saved_variables}
    db = None
    if LOGGER_SV in svs:
        try:
            db = read_logger_db(svs[LOGGER_SV])
        except ForeverError as err:
            notes.append(f"{LOGGER_SV} ignoré : {err.message}")
    spells = log_spell_sets(gd)
    observations: list[MonsterObservation] = []
    conflicts: list[Conflict] = []
    names: list[str] = []
    intervals: list[float] = []
    tally: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: {"hits": 0, "misses": 0})
    costs: dict[int, set[int]] = defaultdict(set)
    casts: dict[int, list[float]] = defaultdict(list)
    crits: dict[int, list[float]] = defaultdict(list)
    episodes: list[IgniteObservation] = []
    for path in sources.logs:
        try:
            _, stream = read_log(path)
            events = list(stream)
        except ForeverError as err:
            notes.append(f"{path.name} ignoré : {err.message}")
            continue
        found, clash = monster_hp(events, log=path.name)
        observations += found
        conflicts += clash
        names.append(path.name)
        mine = find_mine(events)
        if mine is None:
            notes.append(f"{path.name} : aucun lanceur « à moi », seuls les PV des monstres sont relevés")
            continue
        intervals += gcd_intervals(events, mine, max_gap_s=CHAIN_MAX_GAP_S, gcd_spells=spells.gcd)
        try:
            levels = _levels(db, svs.get(QUESTIE_SV), mine, utc_offset)
        except ForeverError as err:
            notes.append(f"{path.name} : niveau du lanceur illisible ({err.message})")
            levels = None
        for (school, diff), count in hit_tally(events, mine, levels, known_spells=spells.known).counts.items():
            tally[(school, diff)]["hits"] += count["hits"]
            tally[(school, diff)]["misses"] += count["misses"]
        for spell, values in spell_costs(events, mine).items():
            costs[spell] |= values
        for spell, times in cast_times(events, mine).items():
            casts[spell] += times
        for spell, ratio in crit_ratios(events, mine):
            crits[spell].append(ratio)
        episodes += ignite_ticks(
            events, mine, ignite_spell=gd.leveling.ignite_aura_id, window_s=gd.leveling.ignite_duration_s
        )
    measured = {(o["npc_id"], o["level"]) for o in observations}
    kept_obs, kept, _ = _kept_observations(installed or {}, set(names), measured)
    gone = sorted(set((installed or {}).get("logs", [])) - set(names))
    table = build_monsters(
        [*observations, *kept_obs],
        questie,
        version,
        conflicts=conflicts,
        logs=[*names, *gone],  # un journal disparu reste listé (jamais de suppression)
        fit_exclude=fit_exclude,
        curve_exclude=curve_exclude,
    )
    snapshot = {
        "schema_version": 1,
        "game_version": version,
        "sources": {
            "logs": {p.name: _sha(p) for p in sources.logs},
            "saved_variables": {p.name: _sha(p) for p in sources.saved_variables},
        },
        "monsters": table,
        "kept_npcs": kept,
        "gone_logs": gone,
        "b1": _b1(gd, intervals),
        "a3": [{"school": s, "level_diff": d, **c} for (s, d), c in sorted(tally.items())],
        "costs": {str(k): sorted(v) for k, v in sorted(costs.items())},
        "cast_times": {str(k): {"n": len(v), "median_s": statistics.median(v)} for k, v in sorted(casts.items())},
        "crits": {str(k): {"n": len(v), "median": statistics.median(v)} for k, v in sorted(crits.items())},
        "ignite_rule": gd.leveling.ignite_rule,
        "ignite": _ignite(gd, episodes),
        "notes": notes,
    }
    result: MeasureSnapshot = json.loads(json.dumps(snapshot, ensure_ascii=False))
    return result


def _hp(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {level: row.get("max_hp") for level, row in entry.get("levels", {}).items()}


def _proof_b1(registry: Sequence[Mechanic]) -> dict[str, Any] | None:
    entry = next((m for m in registry if m.id == B1_ID), None)
    if entry is None or not entry.proofs:
        return None
    proof = entry.proofs[-1]
    return {k: proof.get(k) for k in ("n", "ecart_median_s", "ecart_p10_s")}


def _decimals(value: Any) -> int:
    text = repr(float(value))
    return len(text.split(".")[1]) if "." in text else 0


def _compare_b1(registry: Sequence[Mechanic], measured: Mapping[str, Any]) -> dict[str, Any]:
    """B1 mesuré contre la dernière preuve du registre (écarts arrondis à la précision de la preuve) et bloc
    `preuves` proposé, à reporter à la main avec une fixture (jamais écrit par l'outil)."""
    proof = _proof_b1(registry)
    enough = measured.get("n", 0) >= 2
    same = False
    if proof is not None and enough:
        same = proof["n"] == measured["n"] and all(
            round(measured[k], _decimals(proof[k])) == proof[k] for k in ("ecart_median_s", "ecart_p10_s")
        )
    proposed = ""
    if enough:
        proposed = (
            "preuves:\n"
            "  - journal: [<journaux utilisés, copiés en fixtures>]\n"
            f'    mesure: "médiane {measured["median_s"]:.4f} s, 10e percentile {measured["p10_s"]:.4f} s '
            '(forever measures refresh)"\n'
            f"    n: {measured['n']}\n"
            f"    ecart_median_s: {round(measured['ecart_median_s'], 4)}\n"
            f"    ecart_p10_s: {round(measured['ecart_p10_s'], 4)}\n"
        )
    return {"registry": proof, "measured": dict(measured), "same": same, "proposed": proposed}


def _changed_keys(previous: MeasureSnapshot | None, new: MeasureSnapshot) -> dict[str, list[str]]:
    out = {}
    for key in OTHER_MEASURES:
        old, cur = (previous or {}).get(key, {}), new.get(key, {})
        out[key] = sorted((k for k in set(old) | set(cur) if old.get(k) != cur.get(k)), key=int)
    return out


def compare(
    installed_monsters: Mapping[str, Any],
    registry: Sequence[Mechanic],
    previous: MeasureSnapshot | None,
    new: MeasureSnapshot,
) -> RefreshDiff:
    """Changements à écrire (`changed`) et écarts à afficher : journaux et SavedVariables (nouveaux, modifiés,
    disparus), PNJ (ajoutés, changés, conservés), agrégat par niveau et correction Questie avant et après, B1 et A3
    contre le registre, autres mesures contre le dernier instantané, épisodes d'Ignite contre la règle des données."""
    installed_logs = set(installed_monsters.get("logs", []))
    prev_sources = (previous or {}).get("sources", {"logs": {}, "saved_variables": {}})
    logs, svs = new["sources"]["logs"], new["sources"]["saved_variables"]
    table = new["monsters"]
    old_npcs = installed_monsters.get("npcs", {})
    old_levels = installed_monsters.get("hp_by_level", {})
    changed_levels = {
        level: {"before": (old_levels.get(level) or {}).get("value"), "after": row.get("value")}
        for level, row in table.get("hp_by_level", {}).items()
        if (old_levels.get(level) or {}).get("value") != row.get("value")
    }

    def modified(kind: str, found: Mapping[str, str]) -> list[str]:
        old = prev_sources.get(kind, {})
        return sorted(n for n, sha in found.items() if n in old and old[n] != sha)

    measures_changed = previous is None or any(previous.get(k) != new.get(k) for k in MEASURE_KEYS)
    episodes = new.get("ignite", [])
    npcs = table.get("npcs", {})
    return {
        "changed": table != installed_monsters or measures_changed,
        "logs": {
            "new": sorted(n for n in logs if n not in installed_logs),
            "modified": modified("logs", logs),
            "gone": new.get("gone_logs", []),
        },
        "saved_variables": {
            "new": sorted(n for n in svs if n not in prev_sources.get("saved_variables", {})),
            "modified": modified("saved_variables", svs),
        },
        "npcs": {
            "added": sorted((n for n in npcs if n not in old_npcs), key=int),
            "changed": sorted((n for n, e in npcs.items() if n in old_npcs and _hp(e) != _hp(old_npcs[n])), key=int),
            "kept": new.get("kept_npcs", []),
            "removed": sorted((n for n in old_npcs if n not in npcs), key=int),
        },
        "hp_by_level": changed_levels,
        "questie_correction": {
            "before": (installed_monsters.get("questie_correction") or {}).get("fit"),
            "after": (table.get("questie_correction") or {}).get("fit"),
        },
        "b1": _compare_b1(registry, new.get("b1", {})),
        "a3": {"measured": new.get("a3", []), "note": A3_NOTE},
        "measures": {"first_snapshot": previous is None, "changed": _changed_keys(previous, new)},
        "ignite": {
            "rule": new.get("ignite_rule"),
            "episodes": episodes,
            "note": IGNITE_NOTE if episodes else NO_IGNITE,
        },
    }


def snapshot_exists(cache_dir: Path) -> bool:
    return (cache_dir / SNAPSHOT_DIR / SNAPSHOT_NAME).is_file()


def read_snapshot(cache_dir: Path) -> MeasureSnapshot | None:
    """Dernier instantané (None s'il n'existe pas ou est illisible)."""
    try:
        doc = json.loads((cache_dir / SNAPSHOT_DIR / SNAPSHOT_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def monsters_source(table: Mapping[str, Any], date: str) -> str:
    """Texte `source` de `monsters.json` dans `sources.json` après un rafraîchissement écrit."""
    excluded = [str(e["npc_id"]) for e in (table.get("questie_correction") or {}).get("excluded", [])]
    questie = table.get("questie_source") or "sans Questie"
    return (
        f"Journaux de combat du client ({', '.join(table.get('logs', []))}, PV max du bloc avancé) ; valeurs en "
        f"regard et agrégat des niveaux non observés : {questie} ; table écrite par forever measures refresh le {date}"
        + (f" (--fit-exclude {', '.join(excluded)})" if excluded else "")
    )


def _update_sources(path: Path, source: str) -> None:
    """Remplace le texte `source` de l'entrée `monsters.json` de `sources.json`, sans réécrire le reste du fichier."""
    text = path.read_bytes().decode("utf-8")
    entry = text.index(f'"{MONSTERS_FILE}": {{')
    match = SOURCE_FIELD.search(text, entry)
    if match is None:
        raise ValueError(f"{path} : entrée {MONSTERS_FILE} sans champ source")
    new = json.dumps(source, ensure_ascii=False)
    path.write_bytes((text[: match.start(1)] + new + text[match.end(1) :]).encode("utf-8"))


def apply_refresh(new: MeasureSnapshot, data_dir: Path, cache_dir: Path, *, date: str) -> list[Path]:
    """Écrit `monsters.json` de la version installée, sa source dans `sources.json`, le manifeste et l'instantané
    (sans la table des monstres) ; rend les chemins écrits. Octets LF (chemins -text : empreintes du manifeste)."""
    version_dir = data_dir / new["game_version"]
    monsters = version_dir / MONSTERS_FILE
    monsters.write_bytes((json.dumps(new["monsters"], ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    sources = version_dir / SOURCES_NAME
    _update_sources(sources, monsters_source(new["monsters"], date))
    manifest = write_manifest(data_dir)
    snapshot = cache_dir / SNAPSHOT_DIR / SNAPSHOT_NAME
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    rest = {k: v for k, v in new.items() if k != "monsters"}
    snapshot.write_bytes((json.dumps(rest, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return [monsters, sources, manifest, snapshot]
