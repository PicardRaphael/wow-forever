"""Quêtes de Forever (T04d, bloc D) : fusion des sources locales, statut, écarts, ordre, cache.

La liste fusionnée vit dans le cache (`<cache>/quests/<empreinte>.json`), jamais dans le dépôt ; elle est rebâtie
seulement quand un fichier lu ou les données installées changent. Règle de priorité par champ (une seule, testée) :
client (`quest_rewards.json`) > relevé du joueur (`QuestieForeverDB`) > addons de Forever (Forever Guide, Completo,
Dungeon Journal de Naowh, Journeys, ForeverDungeonJournal) > Questie Classic. La valeur retenue porte sa source et
sa certitude ; tout désaccord entre sources sur un même champ est gardé dans `discrepancies`, jamais tranché par
moyenne.

Statut d'une quête : `nouvelle` (absente de la base Classic de Questie, présente dans une source de Forever),
`retouchée` (présente dans les deux, avec des champs changés : `changed_fields`), `absente des sources Forever`
(base Classic seule dans une zone couverte par Completo : candidate au retrait, `suppose`, jamais « retirée »),
`inchangée`, `non couverte` (base Classic seule, zone hors de Completo)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.pipeline import quest_sources as qs
from forever.pipeline.factoruide import AVAILABLE, DB_REL, SEEN_ONLY, FactoruideDB, load_factoruide
from forever.pipeline.quest_rewards import QUEST_FILE, seen_quest_xp

PRIORITY = (
    "client",
    "questie_forever",
    "forever_guide",
    "completo",
    "naowh_dj",
    "journeys",
    "fdj",
    "gearquest",
    "questie",
)
COMPARED = ("level", "min_level", "faction", "prereq_all", "prereq_any", "next", "xp")
CHANGED = ("level", "min_level", "prereq_all", "prereq_any", "xp")
STATUSES = ("nouvelle", "retouchée", "absente des sources Forever", "inchangée", "non couverte", SEEN_ONLY)
CACHE_DIR = "quests"
MERGE_FORMAT = 3  # version de la forme du cache (changée avec la règle de fusion ; 3 : RX1, Factoruide)
CLIENT_CERTAINTY = "probable"  # disposition de questcache.wdb probable (LVL6) ; QuestXP elle-même est certaine
FDJ_TEXT = "fdj_text"  # source d'écart : XP écrite dans le texte des récompenses de ForeverDungeonJournal
XP_TEXT = "xp_text"  # champ de ForeverDungeonJournal qui la porte
FACTIONS = ("horde", "alliance")
GEAR_NOTE_NAMES = 10  # noms ambigus cités dans la note (paramètre d'affichage)

Quest = dict[str, Any]


class QuestBook(NamedTuple):
    quests: dict[int, Quest]
    sources: list[dict[str, Any]]  # source, addon, version, certitude, nombre de quêtes
    fingerprint: str
    from_cache: bool
    notes: list[str]
    zone_names: dict[int, str]  # uiMapID -> nom anglais (Completo)


class OrderResult(NamedTuple):
    order: list[int]
    cycles: list[list[int]]
    missing_prereqs: dict[int, list[int]]


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return sorted(a, key=str) == sorted(b, key=str)
    if isinstance(a, int | float) and isinstance(b, int | float):
        return abs(float(a) - float(b)) < 1e-9
    return bool(a == b)


def _client_facts(doc: dict[str, Any] | None) -> dict[int, qs.Facts]:
    out: dict[int, qs.Facts] = {}
    for key, seen in ((doc or {}).get("seen_quests") or {}).items():
        quest_id = int(key)
        facts: qs.Facts = {"level": seen["level"], "min_level": seen["min_level"]}
        if seen.get("next_quest"):
            facts["next"] = seen["next_quest"]
        if seen.get("sort_id", 0) > 0:
            facts["zone_area"] = seen["sort_id"]
        xp = seen_quest_xp(doc or {}, quest_id)
        if xp is not None:
            facts["xp"] = xp
        out[quest_id] = facts
    return out


def _merge_one(quest_id: int, by_source: dict[str, qs.Facts], certainty: dict[str, str]) -> Quest:
    fields: dict[str, dict[str, Any]] = {}
    discrepancies: dict[str, dict[str, Any]] = {}
    names = {f for facts in by_source.values() for f in facts}
    for field in sorted(names):
        candidates = [(s, by_source[s][field]) for s in PRIORITY if s in by_source and field in by_source[s]]
        if field == XP_TEXT or not candidates:
            continue
        source, chosen = candidates[0]
        if field == "rewards":
            chosen = dict(chosen)
            for s, v in candidates[1:]:
                for k, x in v.items():
                    chosen.setdefault(k, x)
        fields[field] = {"value": chosen, "source": source, "certainty": certainty[source]}
        if field in COMPARED:
            distinct = dict(candidates)
            if any(not _same(v, chosen) for v in distinct.values()):
                discrepancies[field] = distinct
    fdj = by_source.get("fdj", {})
    if XP_TEXT in fdj and "xp" in fdj and not _same(fdj["xp"], fdj[XP_TEXT]):
        xp = discrepancies.setdefault("xp", {s: v["xp"] for s, v in by_source.items() if "xp" in v})
        xp[FDJ_TEXT] = fdj[XP_TEXT]
    return {
        "id": quest_id,
        "name": fields.get("name", {}).get("value"),
        "sources": [s for s in PRIORITY if s in by_source],
        "fields": fields,
        "discrepancies": discrepancies,
    }


def _status(quest: Quest, by_source: dict[str, qs.Facts], covered: set[int], completo_ids: set[int]) -> None:
    forever = [s for s in quest["sources"] if s not in ("questie", "gearquest")]
    questie = by_source.get("questie")
    certainty = quest["fields"].get("level", {}).get("certainty", "suppose")
    changed: list[str] = []
    if questie is None:
        status = "nouvelle"  # absente de la base Classic (ou Questie absent : voir les notes, statut supposé)
    elif forever:
        for field in CHANGED:
            retained = quest["fields"].get(field)
            if retained and retained["source"] != "questie" and field in questie:
                if not _same(retained["value"], questie[field]):
                    changed.append(field)
            elif retained and retained["source"] != "questie" and field in ("prereq_all", "prereq_any"):
                changed.append(field)
        status = "retouchée" if changed else "inchangée"
    elif questie.get("map") in covered and quest["id"] not in completo_ids:
        status, certainty = "absente des sources Forever", "suppose"
    else:
        status = "non couverte"
    quest.update({"status": status, "changed_fields": changed, "certainty": certainty})


def _attach_gear(quests: dict[int, Quest], rewards: list[qs.GearReward], zone_names: dict[int, str]) -> list[str]:
    ambiguous: dict[str, list[int]] = {}
    by_name: dict[str, list[int]] = {}
    for quest_id, quest in quests.items():
        if quest["name"]:
            by_name.setdefault(quest["name"], []).append(quest_id)
    for reward in rewards:
        ids = by_name.get(reward.quest_name, [])
        if reward.zone and len(ids) > 1:
            in_zone = [i for i in ids if zone_names.get(value(quests[i], "map")) == reward.zone]
            ids = in_zone or ids
        if len(ids) != 1:
            if ids:
                ambiguous[reward.quest_name] = sorted(ids)
            continue
        quest = quests[ids[0]]
        current = quest["fields"].get("rewards")
        items = [
            *((current or {}).get("value", {}).get("items") or []),
            {"item": reward.item, "name": reward.item_name},
        ]
        merged = {**((current or {}).get("value") or {}), "items": items}
        quest["fields"]["rewards"] = {
            "value": merged,
            "source": (current or {}).get("source", "gearquest"),
            "certainty": (current or {}).get("certainty", qs.ADDON_CERTAINTY),
        }
        if "gearquest" not in quest["sources"]:
            quest["sources"].append("gearquest")
    if not ambiguous:
        return []
    shown = sorted(ambiguous.items())[:GEAR_NOTE_NAMES]
    names = "; ".join(f"« {n} » ({', '.join(map(str, ids))})" for n, ids in shown)
    more = f" ; {len(ambiguous) - len(shown)} autre(s)" if len(ambiguous) > len(shown) else ""
    return [f"GearQuest : nom de quête ambigu, objets non rattachés ({len(ambiguous)} nom(s)) : {names}{more}"]


def _merge(
    sources: list[qs.SourceQuests], completo: qs.Completo | None, gear: list[qs.GearReward]
) -> tuple[dict[int, Quest], list[str]]:
    certainty = {s.info.key: s.info.certainty for s in sources}
    ids = sorted({q for s in sources for q in s.quests})
    covered = set(completo.zones) if completo else set()
    completo_ids = set(completo.source.quests) if completo else set()
    quests: dict[int, Quest] = {}
    for quest_id in ids:
        by_source = {s.info.key: s.quests[quest_id] for s in sources if quest_id in s.quests}
        quest = _merge_one(quest_id, by_source, certainty)
        _status(quest, by_source, covered, completo_ids)
        quests[quest_id] = quest
    notes = _attach_gear(quests, gear, completo.zone_names if completo else {})
    return quests, notes


def _seen_only(db: FactoruideDB, ours: dict[int, Quest]) -> dict[int, Quest]:
    """Quêtes `available` de Factoruide inconnues de nos sources : signalées, jamais fusionnées (décision 266)."""
    out: dict[int, Quest] = {}
    for quest_id, q in db.quests.items():
        if q.status != AVAILABLE or quest_id in ours:
            continue
        fields = {
            k: {"value": v, "source": "factoruide", "certainty": "suppose"}
            for k, v in (("name", q.name), ("level", q.level), ("min_level", q.min_level))
            if v is not None
        }
        out[quest_id] = {
            "id": quest_id,
            "name": q.name,
            "sources": ["factoruide"],
            "fields": fields,
            "discrepancies": {},
            "status": SEEN_ONLY,
            "changed_fields": [],
            "certainty": "suppose",
        }
    return out


def _wow(deps: Deps, wow_dir: Path | None) -> Path:
    wow = wow_dir or deps.wow_dir
    if wow is None:
        raise InvalidArgumentError("Dossier du client inconnu.", "définir FOREVER_WOW_DIR")
    return wow


def _client_doc(deps: Deps) -> tuple[dict[str, Any] | None, str]:
    from forever.store import load_version

    data = load_version(deps)
    path = data.path / QUEST_FILE
    doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    return doc, f"{data.game_version}:{data.data_sha}"


def _fingerprint(files: list[Path], data_id: str) -> str:
    parts: list[Any] = [MERGE_FORMAT, qs.READ_FORMAT, data_id]
    for path in files:
        st = os.stat(path)
        parts.append([path.as_posix(), st.st_size, st.st_mtime_ns])
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()[:16]


def _to_json(book: QuestBook) -> dict[str, Any]:
    return {
        "format": MERGE_FORMAT,
        "fingerprint": book.fingerprint,
        "sources": book.sources,
        "notes": book.notes,
        "zone_names": {str(k): v for k, v in book.zone_names.items()},
        "quests": {str(k): v for k, v in book.quests.items()},
    }


def _from_json(doc: dict[str, Any]) -> QuestBook:
    return QuestBook(
        quests={int(k): v for k, v in doc["quests"].items()},
        sources=doc["sources"],
        fingerprint=doc["fingerprint"],
        from_cache=True,
        notes=doc["notes"],
        zone_names={int(k): v for k, v in doc.get("zone_names", {}).items()},
    )


def build_quests(deps: Deps, *, wow_dir: Path | None = None, rebuild: bool = False) -> QuestBook:
    """Liste fusionnée des quêtes du dossier du client `wow_dir` (défaut : `deps.wow_dir`) : addons de
    `Interface/AddOns`, `QuestieForeverDB` des SavedVariables de chaque compte, quêtes vues de `quest_rewards.json`
    installé ; relue dans le cache si aucune empreinte n'a changé (`rebuild` : reconstruite)."""
    wow = _wow(deps, wow_dir)
    addons, wtf = wow / "Interface" / "AddOns", wow / "WTF"
    client_doc, data_id = _client_doc(deps)
    factoruide_db = deps.cache_dir / DB_REL
    files = qs.source_files(addons, wtf) + ([factoruide_db] if factoruide_db.is_file() else [])
    fingerprint = _fingerprint(files, data_id)
    cache = deps.cache_dir / CACHE_DIR / f"{fingerprint}.json"
    if cache.is_file() and not rebuild:
        try:
            return _from_json(json.loads(cache.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError):
            pass  # cache illisible : rebâti
    sources: list[qs.SourceQuests] = []
    notes: list[str] = []
    client = _client_facts(client_doc)
    sources.append(qs.SourceQuests(qs.SourceInfo("client", QUEST_FILE, data_id, CLIENT_CERTAINTY, ()), client, []))
    questie = qs.read_questie_quests(addons)
    if questie is None:
        notes.append("Questie absent : aucune base Classic, statut des quêtes limité")
    else:
        sources.append(questie[0])
        area_to_map = questie[1].area_to_map
        for facts in client.values():
            if "zone_area" in facts and facts["zone_area"] in area_to_map:
                facts["map"] = area_to_map[facts["zone_area"]]
    completo = qs.read_completo(addons)
    if completo is not None:
        sources.append(completo.source)
    for reader in (qs.read_journeys, qs.read_naowh_dj, qs.read_forever_guide, qs.read_fdj):
        read = reader(addons)
        if read is not None:
            sources.append(read)
    recorded = qs.read_questie_forever(wtf) if wtf.is_dir() else None
    if recorded is not None:
        sources.append(recorded)
    gear = qs.read_gearquest(addons)
    quests, gear_notes = _merge(sources, completo, gear[1] if gear else [])
    if questie is None:
        for quest in quests.values():
            quest["certainty"] = "suppose"
    for s in sources:
        notes += s.notes
    notes += gear_notes
    factoruide = load_factoruide(deps.cache_dir)
    if factoruide.status == "illisible":
        notes += factoruide.notes
    seen_only = _seen_only(factoruide, quests)
    quests.update(seen_only)
    infos = [
        {
            "source": s.info.key,
            "label": qs.SOURCE_LABELS[s.info.key],
            "addon": s.info.addon,
            "version": s.info.version,
            "certainty": s.info.certainty,
            "quests": len(s.quests),
        }
        for s in sources
    ]
    if gear:
        infos.append(
            {
                "source": "gearquest",
                "label": qs.SOURCE_LABELS["gearquest"],
                "addon": gear[0].addon,
                "version": gear[0].version,
                "certainty": gear[0].certainty,
                "quests": sum(1 for q in quests.values() if "gearquest" in q["sources"]),
            }
        )
    if factoruide.status == "present":
        infos.append(
            {
                "source": "factoruide",
                "label": qs.SOURCE_LABELS["factoruide"],
                "addon": "Factoruide (cache local)",
                "version": factoruide.provenance["commit"],
                "certainty": "suppose",
                "quests": len(seen_only),
            }
        )
    book = QuestBook(quests, infos, fingerprint, False, notes, completo.zone_names if completo else {})
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(json.dumps(_to_json(book), ensure_ascii=False).encode("utf-8"))
    return book


def routable(quest: Quest) -> bool:
    """Vrai si une route peut placer la quête (RX1) : jamais une quête vue seulement chez Factoruide, jamais une
    quête sans donneur positionné."""
    if quest.get("status") == SEEN_ONLY:
        return False
    giver = value(quest, "giver")
    return isinstance(giver, dict) and isinstance(giver.get("map"), int)


def value(quest: Quest, field: str) -> Any:
    """Valeur retenue d'un champ (None si aucune source ne le donne)."""
    entry = quest["fields"].get(field)
    return None if entry is None else entry["value"]


def _summary(quest: Quest, zone_names: dict[int, str]) -> dict[str, Any]:
    fields = {k: v["value"] for k, v in quest["fields"].items()}
    return {
        "id": quest["id"],
        "name": quest["name"],
        "status": quest["status"],
        "certainty": quest["certainty"],
        "level": fields.get("level"),
        "min_level": fields.get("min_level"),
        "faction": fields.get("faction"),
        "zone": zone_names.get(fields["map"]) if isinstance(fields.get("map"), int) else None,
        "dungeon": fields.get("dungeon"),
        "xp": fields.get("xp"),
        "xp_source": quest["fields"].get("xp", {}).get("source"),
        "changed_fields": quest["changed_fields"],
        "discrepancies": quest["discrepancies"],
        "fields": quest["fields"],
        "sources": quest["sources"],
    }


def lookup_quests(
    deps: Deps,
    *,
    level: int | None = None,
    zone: str | None = None,
    status: str | None = None,
    faction: str | None = None,
    quest_id: int | None = None,
    dungeon: str | None = None,
    limit: int = 20,
    offset: int = 0,
    wow_dir: Path | None = None,
) -> dict[str, Any]:
    """Quêtes filtrées (niveau du personnage : quêtes accessibles et non grises ; zone ; statut ; camp ; donjon ;
    identifiant), paginées, avec la provenance (`forever lookup quests`, `forever_lookup(kind="quests")`)."""
    from forever.engine.leveling import gray_level
    from forever.freshness import freshness_for_version
    from forever.gamedata import build_game_data
    from forever.provenance import make_provenance
    from forever.store import load_version

    if status is not None and status not in STATUSES:
        raise InvalidArgumentError(f"Statut inconnu : {status}.", f"choisir parmi : {', '.join(STATUSES)}")
    if faction is not None and faction not in FACTIONS:
        raise InvalidArgumentError(f"Camp inconnu : {faction}.", "choisir horde ou alliance")
    book = build_quests(deps, wow_dir=wow_dir)
    data = load_version(deps)
    gray = gray_level(build_game_data(data), level) if level is not None else None
    rows: list[Quest] = []
    for quest in book.quests.values():
        lvl, min_level, side = value(quest, "level"), value(quest, "min_level"), value(quest, "faction")
        if quest_id is not None and quest["id"] != quest_id:
            continue
        if status is not None and quest["status"] != status:
            continue
        if faction is not None and side not in (faction, "both", None):
            continue
        if level is not None and (
            min_level is None or min_level > level or lvl is None or (gray is not None and lvl <= gray)
        ):
            continue
        if dungeon is not None and dungeon.lower() not in str(value(quest, "dungeon") or "").lower():
            continue
        if zone is not None:
            name = book.zone_names.get(value(quest, "map"), "")
            if zone.lower() not in (name.lower(), str(value(quest, "map"))):
                continue
        rows.append(quest)
    rows.sort(key=lambda q: (value(q, "level") or 0, q["id"]))
    page = rows[offset : offset + limit]
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    labels = [f"{s['label']} {s['version'] or ''}".strip() for s in book.sources]
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty="suppose",
        assumptions=[
            *fresh["assumptions"],
            f"sources lues en local : {', '.join(labels)}",
            "priorité par champ : client > relevé du joueur > addons de Forever > Questie Classic",
            *book.notes,
        ],
    )
    return {
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "quests": [_summary(q, book.zone_names) for q in page],
        "sources": book.sources,
        "fingerprint": book.fingerprint,
        "provenance": provenance,
    }


def order_quests(book: QuestBook, ids: list[int]) -> OrderResult:
    """Ordre valide des quêtes `ids` (prérequis et chaînes respectés), stable par position puis niveau ; un cycle
    est signalé, les prérequis hors de la sélection sont listés."""
    selected = [i for i in dict.fromkeys(ids) if i in book.quests]
    chosen = set(selected)
    needs_all: dict[int, set[int]] = {}
    needs_any: dict[int, list[set[int]]] = {}
    missing: dict[int, list[int]] = {}
    for quest_id in selected:
        quest = book.quests[quest_id]
        all_of = set(value(quest, "prereq_all") or [])
        any_of = set(value(quest, "prereq_any") or [])
        chain = value(quest, "chain") or {}
        gone = sorted((all_of - chosen) | (any_of - chosen if any_of and not any_of & chosen else set()))
        if gone:
            missing[quest_id] = gone
        needs_all[quest_id] = all_of & chosen
        groups = [any_of & chosen] if any_of & chosen else []
        after = set(chain.get("after") or []) & chosen
        if after:
            groups.append(after)
        needs_any[quest_id] = groups

    def key(quest_id: int) -> tuple[Any, ...]:
        place = value(book.quests[quest_id], "giver") or {}
        return (
            place.get("map") or 0,
            place.get("x") or 0,
            place.get("y") or 0,
            value(book.quests[quest_id], "level") or 0,
            quest_id,
        )

    done: list[int] = []
    left = sorted(selected, key=key)
    while left:
        ready = [q for q in left if needs_all[q] <= set(done) and all(group & set(done) for group in needs_any[q])]
        if not ready:
            return OrderResult(done, [left], missing)
        done.append(ready[0])
        left.remove(ready[0])
    return OrderResult(done, [], missing)


CLASSIC_ONLY = frozenset({"questie"})  # source de la Classic Era : jamais comptée seule (décision 294)


def zones_from_book(
    book: QuestBook, gd: Any, level: int, *, faction: str | None = None, player_class: str = "mage"
) -> Any:
    """Zones et donjons classés par quêtes utiles (vertes, jaunes, orange) au niveau `level`, d'après le livre de
    quêtes fusionné des sources Forever (décision 294) : une quête connue de la seule Classic Era de Questie n'est pas
    comptée ; camp, classe (masque du client) et niveau requis filtrent ; zone nommée par sa carte (Completo), quêtes
    de donjon au donjon. Certitude `suppose` (addons).

    Registre : I7"""
    from forever.engine.leveling import USEFUL_COLORS, level_band, quest_color
    from forever.pipeline.questie import CLASS_MASKS

    mask = CLASS_MASKS[player_class]
    grouped: dict[tuple[str, Any], list[tuple[int, int]]] = {}
    for qid, q in book.quests.items():
        if q["status"] == "absente des sources Forever" or set(q["sources"]) <= CLASSIC_ONLY:
            continue
        lvl, min_level, side = value(q, "level"), value(q, "min_level"), value(q, "faction")
        classes, map_id, dungeon = value(q, "classes"), value(q, "map"), value(q, "dungeon")
        if not isinstance(lvl, int) or (faction and side not in (None, "both", faction)):
            continue
        if isinstance(classes, int) and classes and not classes & mask:
            continue
        if isinstance(min_level, int) and min_level > level:
            continue
        if dungeon:
            grouped.setdefault(("dungeon", dungeon), []).append((qid, lvl))
        elif isinstance(map_id, int):
            grouped.setdefault(("zone", map_id), []).append((qid, lvl))
    zones: list[dict[str, Any]] = []
    dungeons: list[dict[str, Any]] = []
    for (kind, key), rows in grouped.items():
        colors = {c: 0 for c in ("gray", "green", "yellow", "orange", "red")}
        for _, lvl in rows:
            colors[quest_color(gd, level, lvl)] += 1
        levels = [lvl for _, lvl in rows]
        entry = {
            "area_id": key if isinstance(key, int) else 0,
            "name": str(key) if kind == "dungeon" else book.zone_names.get(key, f"carte {key}"),
            "kind": kind,
            "useful_quests": sum(colors[c] for c in USEFUL_COLORS),
            "by_color": colors,
            "quests": sorted(qid for qid, _ in rows),
            "quest_levels": [min(levels), max(levels)],
            "npc_levels": None,
        }
        (dungeons if kind == "dungeon" else zones).append(entry)

    def rank(e: dict[str, Any]) -> tuple[int, str]:
        return -e["useful_quests"], e["name"]

    return {
        "level": level,
        "faction": faction,
        "band": list(level_band(gd, level)),
        "zones": sorted((z for z in zones if z["useful_quests"]), key=rank),
        "dungeons": sorted((d for d in dungeons if d["useful_quests"]), key=rank),
        "certainty": "suppose",
        "source": "livre de quêtes fusionné des sources Forever (forever.quests)",
        "notes": [
            (
                "quêtes des sources Forever seulement (addons de Forever, client) ; la base Classic Era de Questie "
                "n'est plus comptée (décision 294)"
            ),
            "zones nommées par leur carte (noms de Completo, en anglais) ; niveaux des monstres non donnés",
            "couleurs de quête : règle de leveling.quest_band (valeur héritée de la Classic, marquée, suppose)",
            f"quêtes disponibles : faction {faction or 'toutes'}, classe {player_class}, niveau requis atteint",
        ],
    }
