"""Consultation des sorts d'une version de données (rangs positionnels du fichier `spells.json`)."""

from __future__ import annotations

from typing import Literal, TypedDict

from forever.config import Deps
from forever.provenance import Provenance


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
    raise NotImplementedError


def lookup_spell(
    deps: Deps,
    name: str,
    rank: int | None = None,
    *,
    detail: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> SpellLookup:
    raise NotImplementedError
