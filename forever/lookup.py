"""Consultation des sorts d'une version de données (rangs positionnels du fichier `spells.json`)."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from forever.config import Deps
from forever.errors import InvalidArgumentError, UnknownRankError, UnknownSpellError, UnsupportedKindError
from forever.freshness import freshness_for_version
from forever.pipeline.questie import ZoneAdvice
from forever.provenance import Certainty, Provenance, make_provenance, min_certainty
from forever.store import load_version

SPELLS_FILE = "spells.json"
# Champs du spell exposés hors de `details`.
_BASE_FIELDS = frozenset({"school", "range", "ranks", "mana_pct_base"})


class SpellRank(TypedDict):
    rank: int
    level: int
    damage_min: int
    damage_max: int
    dot_total: int
    dot_duration_s: float
    cast_time_s: float
    mana: int | None
    mana_pct_base: float | None
    cooldown_s: float


class SpellLookup(TypedDict):
    kind: Literal["spell"]
    id: str
    school: str
    range_yd: float | None
    ranks_total: int
    ranks: list[SpellRank]
    total: int
    next_offset: int | None
    details: dict[str, object] | None
    provenance: Provenance


def normalize_name(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", name.strip().lower())


def _rank(position: int, row: list[Any], rank_format: list[str], mana_pct_base: float | None) -> SpellRank:
    values = dict(zip(rank_format, row, strict=True))
    mana = values["mana"]
    return {
        "rank": position,
        "level": int(values["level"]),
        "damage_min": int(values["min"]),
        "damage_max": int(values["max"]),
        "dot_total": int(values["dot_total"]),
        "dot_duration_s": float(values["dot_duration"]),
        "cast_time_s": float(values["cast_s"]),
        "mana": None if mana is None else int(mana),
        "mana_pct_base": mana_pct_base,
        "cooldown_s": float(values["cooldown_s"]),
    }


def lookup_spell(
    deps: Deps,
    name: str,
    rank: int | None = None,
    *,
    detail: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> SpellLookup:
    if limit < 1 or offset < 0:
        raise InvalidArgumentError(
            f"Pagination invalide (limit={limit}, offset={offset}).", "utiliser limit ≥ 1 et offset ≥ 0"
        )
    data = load_version(deps)
    spells_file = data.read_json(SPELLS_FILE)
    spells: dict[str, Any] = spells_file["spells"]
    utility: dict[str, Any] = spells_file.get("utility", {})
    key = normalize_name(name)
    if key not in spells:
        available = sorted(spells)
        if key in utility:
            raise UnsupportedKindError(f"sort utilitaire « {key} » (format non exposé en T01)", available)
        raise UnknownSpellError(name, difflib.get_close_matches(key, available + sorted(utility), n=3, cutoff=0.6))

    spell: dict[str, Any] = spells[key]
    rank_format: list[str] = spells_file["rank_format"]
    mana_pct = spell.get("mana_pct_base")
    all_ranks = [_rank(i, row, rank_format, mana_pct) for i, row in enumerate(spell["ranks"], start=1)]
    n = len(all_ranks)
    if rank is not None:
        if not 1 <= rank <= n:
            raise UnknownRankError(key, rank, n)
        ranks, total, next_offset = [all_ranks[rank - 1]], 1, None
    else:
        ranks, total = all_ranks[offset : offset + limit], n
        next_offset = offset + limit if offset + limit < n else None

    meta: dict[str, Any] = data.sources.get("files", {}).get(SPELLS_FILE, {})
    base_certainty = cast(Certainty, meta.get("certainty", "suppose"))
    field_certainty: dict[str, Certainty] = meta.get("field_certainty", {})
    field_notes: dict[str, str] = meta.get("field_notes", {})
    details = {k: v for k, v in spell.items() if k not in _BASE_FIELDS} if detail else None

    certainties: list[Certainty] = [base_certainty]
    notes: list[str] = list(meta.get("notes", []))
    if any(r["mana"] is None for r in ranks) and "mana" in field_notes:
        notes.append(field_notes["mana"])
    for field_name, value in (details or {}).items():
        if value is not None:
            certainties.append(field_certainty.get(field_name, base_certainty))
            if field_name in field_notes:
                notes.append(field_notes[field_name])

    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty=min_certainty(certainties),
        assumptions=[*fresh["assumptions"], *notes],
    )
    range_yd = spell.get("range")
    return {
        "kind": "spell",
        "id": key,
        "school": spell["school"],
        "range_yd": None if range_yd is None else float(range_yd),
        "ranks_total": n,
        "ranks": ranks,
        "total": total,
        "next_offset": next_offset,
        "details": details,
        "provenance": provenance,
    }


class ZoneLookup(ZoneAdvice):
    provenance: Provenance


def lookup_zones(deps: Deps, level: int, *, faction: str | None = None, questie_dir: Path | None = None) -> ZoneLookup:
    """Zones et donjons adaptés au niveau (base Questie lue sur disque), avec la provenance."""
    raise NotImplementedError
