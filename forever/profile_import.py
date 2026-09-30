"""Import automatique minimal du profil joueur (PV1, bloc A ; décisions 99, 105, 125) : collecte, plan, écriture.

Sources, lues sur disque et jamais par le réseau : ForeverLogger (classe, race, niveau, nœuds de talents du dernier
instantané de chaque GUID), mes journaux de combat (personnages « à moi » ; classe déduite des sorts de classe
lancés, `probable`, si ForeverLogger ne connaît pas le GUID), Questie (quêtes faites, par personnage) et
Auctionator (mes prix, par royaume). Chaque champ garde sa source, sa date (UTC) et la version du client en vigueur
(`client_builds.version_at`, `null` si inconnue) ; la fusion suit `profile.merge_field`. La faction n'est jamais
importée. Rien n'est écrit sans accord : `plan_import` rend les changements, `apply_import` les écrit."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

from forever.config import Deps
from forever.errors import DataSchemaError, UnsupportedLogError
from forever.pipeline.addon_sv import read_logger_db
from forever.pipeline.auctionator import read_price_database
from forever.pipeline.client_builds import ClientBuild, current_builds, version_at
from forever.pipeline.combatlog import log_files, read_log
from forever.pipeline.questie import read_completed_quests
from forever.profile import (
    CLASS_NAMES,
    character_values,
    is_valid,
    load_profile,
    make_field,
    merge_field,
    resolve_path,
    save_profile,
)
from forever.provenance import Provenance, local_provenance
from forever.store import VersionData, current_identity, load_version
from forever.timefmt import format_utc

LOGGER_FILE = "ForeverLogger.lua"
QUESTIE_FILE = "Questie.lua"
AUCTIONATOR_FILE = "Auctionator.lua"
SPELLS_FILE = "spells.json"
CLASSES_FILE = "classes.json"
UNKNOWN_BUILD_NOTE = "version du client inconnue"


class ImportPlan(TypedDict):
    status: str
    changes: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    sources: dict[str, str | None]
    notes: list[str]
    doc: dict[str, Any]
    provenance: Provenance


@dataclass
class _Seen:
    """Personnage vu dans une source : identité et champs sourcés."""

    guid: str
    name: str
    realm: str | None
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)


def class_spell_index(data: VersionData) -> dict[int, str]:
    """Identifiant de sort -> classe (nom anglais du client), d'après les sorts de classe et de familier des 9
    classes (`classes.json`, PV1) ; un sort présent dans plusieurs classes n'indique aucune classe. Version sans
    `classes.json` : rangs des sorts du Mage de `spells.json`."""
    if (data.path / CLASSES_FILE).is_file():
        owners: dict[int, set[str]] = {}
        for cls, c in data.read_json(CLASSES_FILE)["classes"].items():
            for spells in (c.get("spells") or {}, c.get("pet_spells") or {}):
                for spell in spells.values():
                    for rank in spell.get("ranks", []):
                        owners.setdefault(int(rank["spell_id"]), set()).add(cls)
        return {spell_id: next(iter(classes)) for spell_id, classes in owners.items() if len(classes) == 1}
    out: dict[int, str] = {}
    for spell in data.read_json(SPELLS_FILE)["spells"].values():
        for spell_id in (spell.get("source") or {}).get("rank_spell_ids") or []:
            out[int(spell_id)] = "Mage"
    return out


def _utc_of_local(when: datetime, offset: timedelta | None) -> datetime:
    """Heure locale du client (sans fuseau) ramenée en UTC (décalage donné, sinon celui du système)."""
    shift = offset if offset is not None else datetime.now().astimezone().utcoffset() or timedelta()
    return when.replace(tzinfo=UTC) - shift


class _Stamper:
    """Date UTC et version du client d'un instant ; retient si une version est restée inconnue."""

    def __init__(self, builds: list[ClientBuild]) -> None:
        self.builds = builds
        self.unknown: set[str] = set()

    def field(self, value: Any, source: str, moment: datetime, certainty: str = "certain") -> dict[str, Any]:
        build = version_at(self.builds, moment)
        if build is None:
            self.unknown.add(source)
        return make_field(value, source, format_utc(moment), build, certainty)


def _from_logger(path: Path, stamp: _Stamper, offset: timedelta | None) -> dict[str, _Seen]:
    db = read_logger_db(path)
    out: dict[str, _Seen] = {}
    for guid, c in db.characters.items():
        if not c.name:
            continue

        def moment(s: Any) -> datetime | None:
            if s.time is not None:
                return datetime.fromtimestamp(s.time, UTC)
            return _utc_of_local(s.localtime, offset) if s.localtime is not None else None

        snaps = sorted(((m, s) for s in c.snapshots if (m := moment(s)) is not None), key=lambda p: p[0])
        seen = _Seen(guid, c.name, c.realm)
        if snaps:
            last = snaps[-1][0]
            cls = CLASS_NAMES.get((c.class_ or "").lower())
            if cls is not None:
                seen.fields["class"] = stamp.field(cls, "ForeverLogger", last)
            if c.race:
                seen.fields["race"] = stamp.field(c.race, "ForeverLogger", last)
            levels = [(m, s.level) for m, s in snaps if s.level is not None]
            if levels:
                seen.fields["level"] = stamp.field(levels[-1][1], "ForeverLogger", levels[-1][0])
            talents = [(m, s.talents) for m, s in snaps if s.talents is not None]
            if talents:
                nodes = {str(k): v for k, v in sorted(talents[-1][1].items())}
                seen.fields["talent_nodes"] = stamp.field(nodes, "ForeverLogger", talents[-1][0])
        out[guid] = seen
    return out


def _from_logs(
    directory: Path, offset: timedelta | None, notes: list[str]
) -> dict[str, tuple[str, str | None, datetime, set[int]]]:
    """GUID -> (nom, royaume, dernier événement vu en UTC, sorts lancés) des joueurs « à moi »."""
    out: dict[str, tuple[str, str | None, datetime, set[int]]] = {}
    for path in log_files(directory):
        try:
            _, events = read_log(path)
            for e in events:
                for unit in (e.source, e.dest):
                    if unit is None or not unit.is_mine or unit.kind != "Player" or not unit.name:
                        continue
                    name, _, realm = unit.name.partition("-")
                    when = _utc_of_local(e.time, offset)
                    prev = out.get(unit.guid)
                    casts = prev[3] if prev else set()
                    out[unit.guid] = (name, realm or None, max(when, prev[2]) if prev else when, casts)
                if e.name == "SPELL_CAST_SUCCESS" and e.spell and e.source is not None and e.source.guid in out:
                    out[e.source.guid][3].add(e.spell[0])
        except (UnsupportedLogError, DataSchemaError) as err:
            notes.append(f"journal {path.name} ignoré : {err.message}")
    return out


def _class_of(casts: set[int], index: Mapping[int, str]) -> tuple[str | None, str]:
    classes = sorted({index[s] for s in casts if s in index})
    if len(classes) == 1:
        return classes[0], ""
    if not classes:
        return None, "classe inconnue : aucun sort de classe lancé dans les journaux"
    return None, f"classe inconnue : sorts de plusieurs classes lancés ({', '.join(classes)})"


def _change(character: str | None, name: str, old: Any, new: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "character": character,
        **extra,
        "field": name,
        "old": old,
        "new": new.get("value"),
        "source": new.get("source"),
        "at": new.get("at"),
        "client_build": new.get("client_build"),
    }


def _merge_character(
    deps: Deps, doc: dict[str, Any], seen: _Seen, plan: dict[str, list[dict[str, Any]]], version: str
) -> None:
    chars: dict[str, Any] = doc["characters"]
    raw = copy.deepcopy(chars.get(seen.name) or {})
    flat = character_values(raw)
    if raw:
        if flat["realm"] and seen.realm and flat["realm"] != seen.realm:
            reason = f"même nom qu'un personnage de {flat['realm']}, vu sur {seen.realm}"
            plan["skipped"].append({"name": seen.name, "guid": seen.guid, "reason": reason})
            return
        theirs = seen.fields.get("class")
        if flat["class"] and theirs is not None and theirs["value"] != flat["class"]:
            disagreement = {"kept": raw["class"], "other": theirs}
            plan["conflicts"].append({"character": seen.name, "field": "class", **disagreement})
            return
    changes: list[dict[str, Any]] = []
    conflicts = list(raw.get("conflicts") or [])
    for name, new in seen.fields.items():
        old = raw.get(name)
        kept, conflict = merge_field(old, new)
        if kept != old:
            changes.append(_change(seen.name, name, (old or {}).get("value"), kept))
            raw[name] = kept
        if conflict is not None:
            record = {"field": name, **conflict}
            plan["conflicts"].append({"character": seen.name, **record})
            if record not in conflicts:
                conflicts.append(record)
                changes.append(_change(seen.name, f"conflit:{name}", None, conflict["other"]))
    for key, value in (("guid", seen.guid), ("realm", seen.realm)):
        if value is not None and raw.get(key) is None:
            raw[key] = value
    if raw.get("planned"):
        changes.append(_change(seen.name, "planned", True, make_field(False, "journal", None)))
    raw["planned"] = False
    if not changes:
        return
    if conflicts:
        raw["conflicts"] = conflicts
    raw["validated"] = is_valid(deps, character_values(raw))
    raw["game_version"] = version
    raw["updated_at"] = format_utc(deps.now())
    chars[seen.name] = raw
    if doc.get("active") is None:
        doc["active"] = seen.name
    plan["changes"] += changes


def plan_import(
    deps: Deps,
    *,
    sv_dir: Path | None,
    logs_dir: Path | None,
    utc_offset: timedelta | None = None,
    class_spells: Mapping[int, str] | None = None,
) -> ImportPlan:
    """Changements que l'import apporterait au profil, sans rien écrire. `class_spells` : index sort -> classe
    (défaut : `class_spell_index` des données courantes)."""
    data = load_version(deps)
    index = class_spells if class_spells is not None else class_spell_index(data)
    stamp = _Stamper(current_builds(deps.cache_dir, deps.wow_dir))
    notes: list[str] = []

    def present(directory: Path | None, name: str) -> Path | None:
        path = directory / name if directory is not None else None
        return path if path is not None and path.is_file() else None

    logger, questie, auctionator = (present(sv_dir, n) for n in (LOGGER_FILE, QUESTIE_FILE, AUCTIONATOR_FILE))
    logs = logs_dir if logs_dir is not None and logs_dir.is_dir() and log_files(logs_dir) else None
    sources = {
        "ForeverLogger": str(logger) if logger else None,
        "Questie": str(questie) if questie else None,
        "Auctionator": str(auctionator) if auctionator else None,
        "journaux": str(logs) if logs else None,
    }
    notes += [f"source absente : {name}" for name, path in sources.items() if path is None]

    seen = _from_logger(logger, stamp, utc_offset) if logger else {}
    skipped: list[dict[str, Any]] = []
    for guid, (name, realm, last, casts) in (_from_logs(logs, utc_offset, notes) if logs else {}).items():
        if guid in seen:
            continue  # classe de ForeverLogger, par jointure de GUID (D2)
        cls, reason = _class_of(casts, index)
        if cls is None:
            skipped.append({"name": name, "guid": guid, "reason": reason})
            continue
        seen[guid] = _Seen(guid, name, realm, {"class": stamp.field(cls, "journal", last, "probable")})
    if questie is not None:
        for guid, character in seen.items():
            done = read_completed_quests(questie, guid)
            if done:
                last_done = datetime.fromtimestamp(max(ts for _, ts in done), UTC)
                value = {str(q): format_utc(datetime.fromtimestamp(ts, UTC)) for q, ts in done}
                character.fields["quests_completed"] = stamp.field(value, "Questie", last_done)

    doc = load_profile(resolve_path(deps))
    plan: dict[str, list[dict[str, Any]]] = {"changes": [], "conflicts": [], "skipped": skipped}
    version = current_identity(deps.data_dir).game_version
    for character in seen.values():
        _merge_character(deps, doc, character, plan, version)
    if auctionator is not None:
        realms = doc.setdefault("realms", {})
        for realm, items in read_price_database(auctionator).items():
            table = {str(item): price._asdict() for item, price in sorted(items.items())}
            new = make_field(table, "Auctionator", max(p.date for p in items.values()), None, "probable")
            old = (realms.get(realm) or {}).get("prices")
            kept, _ = merge_field(old, new)
            if kept != old:
                before = len(old["value"]) if old else None
                plan["changes"].append(
                    {**_change(None, "prices", before, kept, realm=realm), "new": len(kept["value"])}
                )
                realms[realm] = {"prices": kept}
    if stamp.unknown:
        notes.append(
            f"{UNKNOWN_BUILD_NOTE} pour {', '.join(sorted(stamp.unknown))} (instant antérieur au premier relevé de "
            ".build.info, ou journal des versions absent) : champ `client_build` à null"
        )
    notes.append("faction jamais importée (décision 99) ; champ `level` du journal non lu pour un joueur")
    probable = any(c["certainty"] != "certain" for s in seen.values() for c in s.fields.values())
    return {
        "status": "changements" if plan["changes"] else "aucun changement",
        "changes": plan["changes"],
        "skipped": plan["skipped"],
        "conflicts": plan["conflicts"],
        "sources": sources,
        "notes": notes,
        "doc": doc,
        "provenance": local_provenance(deps, certainty="probable" if probable else "certain", assumptions=notes),
    }


def apply_import(deps: Deps, plan: ImportPlan) -> None:
    """Écrit le profil planifié (après accord) ; rien si aucun changement."""
    if plan["changes"]:
        save_profile(resolve_path(deps), plan["doc"])
