"""Consultation des sorts d'une version de données (rangs positionnels du fichier `spells.json`)."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from forever.config import Deps
from forever.errors import (
    InvalidArgumentError,
    UnknownRankError,
    UnknownSpellError,
    UnknownTalentError,
    UnsupportedKindError,
)
from forever.freshness import freshness_for_version
from forever.pipeline.hotfixes import entity_assumptions
from forever.pipeline.questie import TOC_NAME, ZoneAdvice, read_questie, zones_for_level
from forever.provenance import Certainty, Provenance, make_provenance, min_certainty
from forever.store import load_version

SPELLS_FILE = "spells.json"
TALENTS_FILE = "talents.json"
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
        assumptions=[
            *fresh["assumptions"],
            *notes,
            *entity_assumptions(deps.cache_dir, data.game_version, data.path, "spell", key),
        ],
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


class TalentRank(TypedDict):
    rank: int
    values: list[float]
    description: str


class TalentPrereq(TypedDict):
    id: str
    name: str
    max_rank: int


class TalentLookup(TypedDict):
    kind: Literal["talent"]
    id: str
    name: str
    tree: str
    tier: int
    col: int
    required_tree_points: int
    prereq: TalentPrereq | None
    max_rank: int
    description_template: str
    spell: str | None
    source: str
    duration_s: float | None
    derived: list[Any]  # valeurs par cumul des talents à cumuls (engine/derived.py, T06b)
    ranks: list[TalentRank]
    provenance: Provenance


def lookup_talent(deps: Deps, name: str, rank: int | None = None) -> TalentLookup:
    """Talent du Mage par nom anglais ou clé (casse, espaces, tirets et soulignés ignorés) : arbre, palier, points
    exigés dans l'arbre, prérequis, rangs et valeurs (description aux valeurs du rang), sort appris, provenance.

    Registre : G3"""
    from forever.engine.derived import stack_tables
    from forever.engine.talents import tier_points_required
    from forever.gamedata import build_game_data

    data = load_version(deps)
    raw: dict[str, Any] = data.read_json(TALENTS_FILE)
    entries: dict[str, dict[str, Any]] = {t["key"]: t for tree in raw["trees"] for t in tree["talents"]}
    index: dict[str, str] = {}
    for key, t in entries.items():
        index[_talent_key(key)] = key
        index[_talent_key(t["name"])] = key
    wanted = _talent_key(name)
    if wanted not in index:
        names = {_talent_key(t["name"]): t["name"] for t in entries.values()}
        close = difflib.get_close_matches(wanted, sorted(names), n=3, cutoff=0.6)
        raise UnknownTalentError(name, [names[c] for c in close])
    key = index[wanted]
    entry = entries[key]
    gd = build_game_data(data)
    talent = gd.talents[key]
    all_ranks: list[TalentRank] = [
        {"rank": i, "values": list(values), "description": _describe(entry["desc"], values)}
        for i, values in enumerate(talent.ranks, start=1)
    ]
    if rank is not None:
        if not 1 <= rank <= talent.max_rank:
            raise UnknownRankError(key, rank, talent.max_rank)
        ranks = [all_ranks[rank - 1]]
    else:
        ranks = all_ranks

    prereq: TalentPrereq | None = None
    if talent.prereq is not None:
        pk = gd.talent_at[(talent.tree, *talent.prereq)]
        prereq = {"id": pk, "name": gd.talents[pk].name, "max_rank": gd.talents[pk].max_rank}
    spells_file = data.read_json(SPELLS_FILE)
    spell_key = normalize_name(talent.name)
    spell = spell_key if spell_key in spells_file["spells"] or spell_key in spells_file.get("utility", {}) else None

    # Certitude par talent : rangs lus sur la version courante (certain) ou sur un build antérieur (probable).
    source = str(entry["certainty"])
    current_build = data.game_version.rsplit(".", 1)[-1]
    notes: list[str] = []
    if source == f"FC-{current_build}":
        certainty: Certainty = "certain"
    else:
        certainty = "probable"
        notes.append(f"valeurs lues sur le build {source.removeprefix('FC-')}, pas sur {data.game_version}")
    if talent.duration_s is not None:
        # Durée d'aura corrigée d'après le client : la description, tirée des rangs, peut garder l'ancienne valeur.
        notes.append(f"durée corrigée d'après le client : {_fmt_value(talent.duration_s)} s (champ duration_s)")
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty=certainty,
        assumptions=[*fresh["assumptions"], *notes],
    )
    return {
        "kind": "talent",
        "id": key,
        "name": talent.name,
        "tree": talent.tree,
        "tier": talent.tier,
        "col": talent.col,
        "required_tree_points": tier_points_required(gd, talent.tier),
        "prereq": prereq,
        "max_rank": talent.max_rank,
        "description_template": entry["desc"],
        "spell": spell,
        "source": source,
        "duration_s": talent.duration_s,
        "derived": [t for t in stack_tables(gd, key) if rank is None or t["rank"] == rank],
        "ranks": ranks,
        "provenance": provenance,
    }


def _talent_key(name: str) -> str:
    return re.sub(r"[\s\-_']+", "", name.strip().lower())


def _fmt_value(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def _describe(template: str, values: tuple[float, ...]) -> str:
    """Description du rang : `{i}` remplacé par la valeur i du rang (laissé tel quel si la valeur manque)."""
    return re.sub(
        r"\{(\d+)\}",
        lambda m: _fmt_value(values[int(m.group(1))]) if int(m.group(1)) < len(values) else m.group(0),
        template,
    )


class ZoneLookup(ZoneAdvice):
    provenance: Provenance


def lookup_zones(
    deps: Deps, level: int | None, *, faction: str | None = None, questie_dir: Path | None = None
) -> ZoneLookup:
    """Zones et donjons adaptés au niveau (base Questie lue sur disque, jamais par le réseau), avec la provenance ;
    InvalidArgumentError (code 2) si le niveau manque ou sort des bornes, si la faction est inconnue ou si l'addon
    Questie est introuvable.

    Registre : I7"""
    from forever.gamedata import build_game_data
    from forever.leveling import check_level, level_cap

    if level is None:
        raise InvalidArgumentError("Niveau manquant.", "donner --level (niveau du personnage)")
    data = load_version(deps)
    check_level(level, level_cap(data))
    if questie_dir is None and deps.wow_dir is not None:
        questie_dir = deps.wow_dir / "Interface" / "AddOns" / "Questie"
    if questie_dir is None or not (questie_dir / TOC_NAME).is_file():
        raise InvalidArgumentError(
            f"Addon Questie introuvable : {questie_dir or 'aucun dossier'}.",
            "donner --questie <Interface/AddOns/Questie> ou définir FOREVER_WOW_DIR",
        )
    try:
        advice = zones_for_level(read_questie(questie_dir), build_game_data(data), level, faction=faction)
    except ValueError as exc:
        raise InvalidArgumentError(f"{exc}.", "choisir --faction horde ou alliance") from exc
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty="suppose",
        assumptions=[*fresh["assumptions"], f"source : {advice['source']}", *advice["notes"]],
    )
    return {**advice, "provenance": provenance}


def _class_knowledge(deps: Deps, cls: str) -> tuple[str, Any, Any]:
    from forever.gamedata import build_game_data
    from forever.profile import normalize_class

    name = normalize_class(cls)
    gd = build_game_data(load_version(deps))
    if name not in gd.classes:
        raise InvalidArgumentError(f"Classe {name} absente des données.", "installer classes.json (forever install)")
    return name, gd.classes[name], gd


def lookup_class_talent(deps: Deps, cls: str, name: str) -> dict[str, Any]:
    """Talent d'une des 9 classes par nom anglais ou clé : arbre, palier (communautaire s'il est inconnu du client),
    colonne, points exigés, prérequis, rangs, description du client, provenance (PV1, bloc E).

    Registre : G3"""
    from forever.engine.talents import tier_points_required

    cls_name, knowledge, gd = _class_knowledge(deps, cls)
    entries = {t["key"]: t for tree in knowledge.trees for t in tree["talents"]}
    index = {_talent_key(k): k for k in entries} | {_talent_key(t["name"]): k for k, t in entries.items()}
    wanted = _talent_key(name)
    if wanted not in index:
        names = {_talent_key(t["name"]): t["name"] for t in entries.values()}
        close = difflib.get_close_matches(wanted, sorted(names), n=3, cutoff=0.6)
        raise UnknownTalentError(name, [names[c] for c in close])
    t = entries[index[wanted]]
    by_node = {x["node_id"]: x for x in entries.values()}
    tier = t["tier"] if t["tier"] is not None else (t.get("tier_community") or {}).get("tier")
    notes = [f"classes.json : talent {t['key']} de {cls_name} décodé du client (nœud {t['node_id']})"]
    certainty: Certainty = "certain"
    if t["tier"] is None and t.get("tier_community"):
        certainty = "probable"
        notes.append(f"palier communautaire ({', '.join(t['tier_community']['sources'])})")
    if t.get("unresolved"):
        notes += t["unresolved"]
    if t.get("position"):
        notes.append(f"position : {t['position']['source']}")
    notes.append("valeurs par rang non décodées pour cette classe : gabarit de description du client")
    return {
        "kind": "talent",
        "class": cls_name,
        "id": t["key"],
        "name": t["name"],
        "name_fr": t["name_fr"],
        "tree": t["tree"],
        "tier": tier,
        "col": t["col"],
        "node_id": t["node_id"],
        "required_tree_points": tier_points_required(gd, tier) if tier else None,
        "prereqs": [
            {"id": by_node[p["node_id"]]["key"], "name": by_node[p["node_id"]]["name"], "kind": p["kind"]}
            for p in t["prereqs"]
            if p["node_id"] in by_node
        ],
        "max_rank": t["max"],
        "description_template": t["desc"],
        "spell_id": t["spell_id"],
        "provenance": make_provenance(
            deps,
            game_version=load_version(deps).game_version,
            data_sha=load_version(deps).data_sha,
            freshness=freshness_for_version(deps, load_version(deps).game_version, allow_network=False)["freshness"],
            certainty=certainty,
            assumptions=notes,
        ),
    }


def check_talents(deps: Deps, cls: str, talents: dict[str, int], level: int) -> dict[str, Any]:
    """Légalité d'un build d'une des 9 classes au niveau donné : légal ou erreurs, points, description des talents
    pris (PV1, bloc E).

    Registre : G3"""
    from forever.engine.talents import check_class_build, points_available

    cls_name, knowledge, gd = _class_knowledge(deps, cls)
    rules = gd.constants.talents
    errors = check_class_build(knowledge, rules, talents, level)
    entries = {t["key"]: t for tree in knowledge.trees for t in tree["talents"]}
    taken = [
        {
            "key": k,
            "name": entries[k]["name"],
            "rank": r,
            "max_rank": entries[k]["max"],
            "tree": entries[k]["tree"],
            "description_template": entries[k]["desc"],
        }
        for k, r in talents.items()
        if k in entries and r > 0
    ]
    by_tree: dict[str, int] = {}
    for t in taken:
        by_tree[t["tree"]] = by_tree.get(t["tree"], 0) + int(t["rank"])
    community = [k for k in talents if k in entries and entries[k]["tier"] is None and entries[k].get("tier_community")]
    notes = [f"légalité contrôlée sur classes.json ({cls_name}) : points par palier, rangs, prérequis, niveau"]
    if community:
        notes.append(f"palier communautaire (probable) pour {', '.join(community)}")
    data = load_version(deps)
    return {
        "kind": "build_check",
        "class": cls_name,
        "level": level,
        "legal": not errors,
        "errors": errors,
        "points": {
            "spent": sum(max(0, r) for r in talents.values()),
            "available": points_available(gd, level),
            "by_tree": by_tree,
        },
        "talents": taken,
        "provenance": make_provenance(
            deps,
            game_version=data.game_version,
            data_sha=data.data_sha,
            freshness=freshness_for_version(deps, data.game_version, allow_network=False)["freshness"],
            certainty="probable" if community else "certain",
            assumptions=notes,
        ),
    }
