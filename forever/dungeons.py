"""Livre des donjons de Forever (DJ1, bloc C) : client, addons et relevés du joueur fusionnés champ par champ.

Clé d'un donjon : identifiant d'instance (`Map.ID`, `"389"`) ; une aile (Scarlet Monastery, Dire Maul, Blackrock
Spire, Stratholme) : `"189:graveyard"` ; un donjon que seuls des addons connaissent : `"name:<nom normalisé>"`. Une
source qui n'a qu'un nom est rattachée par la table des noms (noms du client, des entrées de recherche de groupe et
des sources qui donnent l'instance) ; un nom non rattaché ou ambigu est signalé, jamais deviné.

Chaque champ porte sa valeur, sa source, sa certitude et les valeurs des autres sources (`others`) ; un champ où les
sources divergent est listé dans `discrepancies`. Ordre des sources (décision 265) : relevé du joueur, puis client
(rencontres, niveau de contenu), puis Naowh Forever, FojjiCore, ForeverDungeonJournal, Forever Guide, Forever
Companion, AtlasLoot, Zone Info: Forever. Niveau d'un boss : journal de combat (`monsters.json`, bloc avancé,
`certain`) d'abord ; une valeur copiée (FojjiCore = ForeverDungeonJournal) compte pour une seule source. Taux :
relevé (lâchés ÷ victoires) d'abord, puis Naowh, FojjiCore, puis un taux Classic (Forever Guide, Forever Companion,
AtlasLoot) seulement pour un donjon que personne ne dit nouveau, étiqueté `classic`. Prérequis : les listes des
addons sont des chaînes ordonnées (chaque quête exige la précédente ; une sous-liste : l'une suffit, la première est
retenue).

La liste fusionnée vit dans le cache local (`<cache>/dungeons/`), rebâtie quand une empreinte change ; seuls des
agrégats entrent dans le dépôt (`render_report`, décision 133). Aucun chiffre de jeu ici."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.pipeline.dungeon_sources import DUNGEON_SOURCE_LABELS, SourceDungeons
from forever.pipeline.questie import CLASS_MASKS

ORDER = ("client", "naowh_dj", "fojji", "fdj", "forever_guide", "companion", "atlasloot", "zoneinfo")
LOOT_ORDER = ("naowh_dj", "fojji", "fdj", "forever_guide", "companion", "atlasloot")
COPY_FAMILY = frozenset({"fojji", "fdj"})  # niveaux des nouveaux boss recopiés d'une source à l'autre (plan de DJ1)
GENERIC_WORDS = frozenset({"spire"})  # mots du nom d'instance qu'une aile peut omettre (« Lower Spire »)
CACHE_DIR = "dungeons"
MERGE_FORMAT = 1
DUNGEON_FILE = "dungeons.json"
MONSTERS_FILE = "monsters.json"
LOGGED_SOURCE = "journal"
OFFICIAL_SOURCE = "officiel"  # note officielle de la bêta (mechanics.json, dungeon.official)
OFFICIAL_KEY = "dungeon.official"
RECORD_SOURCE = "relevé"
CERTAIN, PROBABLE, SUPPOSE = "certain", "probable", "suppose"
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_PUNCT = re.compile(r"[:\-–,.()/]")


class DungeonBook(NamedTuple):
    dungeons: dict[str, dict[str, Any]]
    sources: list[dict[str, Any]]
    notes: list[str]
    fingerprint: str
    from_cache: bool


def norm(name: str) -> str:
    """Nom comparable : CamelCase séparé, minuscules, apostrophes ôtées, ponctuation en espace, « the » initial ôté."""
    s = _CAMEL.sub(" ", name).lower().replace("'", "").replace("’", "")
    s = " ".join(_PUNCT.sub(" ", s).split())
    return s.removeprefix("the ")


def _wing(name: str, instance_name: str) -> str | None:
    base = set(norm(instance_name).split()) | GENERIC_WORDS
    rest = [w for w in norm(name).split() if w not in base]
    return " ".join(rest) or None


def logged_boss_levels(monsters: Mapping[str, Any] | None) -> dict[int, list[int]]:
    """Niveaux relevés dans un journal de combat (`monsters.json`, certitude `certain`), par PNJ. Registre : H12"""
    out: dict[int, list[int]] = {}
    for npc, row in ((monsters or {}).get("npcs") or {}).items():
        levels = [
            int(level)
            for level, entry in (row.get("levels") or {}).items()
            if isinstance(entry, dict) and entry.get("certainty") == CERTAIN and str(level).isdigit()
        ]
        if levels and str(npc).isdigit():
            out[int(npc)] = sorted(levels)
    return out


# --- rattachement -------------------------------------------------------------------------------------------------


class _Index:
    """Table des noms : nom normalisé -> (instance, aile) ; zones (AreaTable) -> instance."""

    def __init__(self, client: Mapping[str, Any] | None) -> None:
        self.names: dict[str, set[tuple[int, str | None]]] = {}
        self.instance_names: dict[int, str] = {}
        self.areas: dict[int, int] = {}
        for key, inst in ((client or {}).get("instances") or {}).items():
            map_id = int(key)
            self.instance_names[map_id] = inst["name"]
            self.add(inst["name"], map_id, None)
            for entry in inst.get("lfg", []):
                wing = _wing(entry["name"], inst["name"])
                self.add(entry["name"], map_id, wing)
            for area in inst.get("areas", []):
                self.areas[int(area)] = map_id

    def add(self, name: str | None, map_id: int, wing: str | None) -> None:
        if isinstance(name, str) and name:
            self.names.setdefault(norm(name), set()).add((map_id, wing))

    def wing_of(self, map_id: int, name: str | None) -> str | None:
        base = self.instance_names.get(map_id)
        return _wing(name, base) if base and isinstance(name, str) else None

    def resolve(self, name: str) -> tuple[int, str | None] | None:
        n = norm(name)
        hits = self.names.get(n)
        if hits and len(hits) == 1:
            return next(iter(hits))
        if hits:
            return None  # ambigu
        found = {
            (map_id, _wing(name, base))
            for map_id, base in self.instance_names.items()
            if n.startswith(norm(base) + " ") or n == norm(base)
        }
        return next(iter(found)) if len(found) == 1 else None


def _book_key(map_id: int | None, wing: str | None, name: str | None) -> str:
    if map_id is None:
        return f"name:{norm(name or '')}"
    return f"{map_id}:{wing}" if wing else str(map_id)


# --- fusion ---------------------------------------------------------------------------------------------------------


def _certainty(source: str) -> str:
    return {"client": CERTAIN, LOGGED_SOURCE: CERTAIN, RECORD_SOURCE: CERTAIN, OFFICIAL_SOURCE: PROBABLE}.get(
        source, SUPPOSE
    )


def _field(candidates: Sequence[tuple[str, Any]]) -> dict[str, Any] | None:
    """Valeur de la première source (ordre déclaré), avec celles des autres."""
    present = [(s, v) for s, v in candidates if v is not None]
    if not present:
        return None
    (source, value), rest = present[0], present[1:]
    return {
        "value": value,
        "source": source,
        "certainty": _certainty(source),
        "others": [{"source": s, "value": v} for s, v in rest],
    }


def _diverges(entry: Mapping[str, Any] | None) -> bool:
    return bool(entry) and any(o["value"] != entry["value"] for o in entry["others"])  # type: ignore[index]


def _ranked(contribs: Sequence[tuple[str, Mapping[str, Any]]]) -> list[tuple[str, Mapping[str, Any]]]:
    return sorted(contribs, key=lambda c: ORDER.index(c[0]) if c[0] in ORDER else len(ORDER))


def _boss_level(
    npc: int | None, matched: Sequence[tuple[str, Mapping[str, Any]]], logged: Mapping[int, Sequence[int]]
) -> dict[str, Any] | None:
    candidates: list[tuple[str, Any]] = []
    if npc is not None and npc in logged:
        levels = sorted(set(logged[npc]))
        candidates.append((LOGGED_SOURCE, levels[0] if len(levels) == 1 else {"min": levels[0], "max": levels[-1]}))
    candidates += [(s, b.get("level")) for s, b in matched]
    entry = _field(candidates)
    if entry is None:
        return None
    agree = [entry["source"], *(o["source"] for o in entry["others"] if o["value"] == entry["value"])]
    families = {("copy" if s in COPY_FAMILY else s) for s in agree}
    return {**entry, "sources": agree, "independent": len(families)}


def _loot(
    matched: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    new_dungeon: bool,
    observed: Mapping[int, dict[str, int]],
) -> list[dict[str, Any]]:
    items: dict[int, list[tuple[str, Mapping[str, Any]]]] = {}
    for source, b in matched:
        for entry in b.get("loot", []):
            items.setdefault(int(entry["item"]), []).append((source, entry))
    for item in observed:
        items.setdefault(item, [])
    out = []
    for item, cands in items.items():
        cands = sorted(cands, key=lambda c: LOOT_ORDER.index(c[0]) if c[0] in LOOT_ORDER else len(LOOT_ORDER))
        rated = [(s, e) for s, e in cands if e.get("rate") is not None]
        forever = [(s, e) for s, e in rated if not e.get("classic")]
        classic = [(s, e) for s, e in rated if e.get("classic") and not new_dungeon]
        row: dict[str, Any] = {"item": item, "rate": None, "rate_source": None, "certainty": None}
        obs = observed.get(item)
        chosen: tuple[str, Mapping[str, Any]] | None = None
        if obs and obs["kills"] > 0:
            row.update(rate=obs["drops"] / obs["kills"], rate_source=RECORD_SOURCE, certainty=CERTAIN, observed=obs)
        elif forever or classic:
            chosen = (forever or classic)[0]
            row.update(rate=chosen[1]["rate"], rate_source=chosen[0], certainty=SUPPOSE)
            if chosen[1].get("classic"):
                row["classic"] = True
        row["others"] = [
            {"source": s, "rate": e["rate"], **({"classic": True} if e.get("classic") else {})}
            for s, e in rated
            if chosen is None or s != chosen[0]
        ]
        row["sources"] = sorted({s for s, _ in cands})
        out.append(row)
    return out


def _bosses(
    client_encounters: Sequence[Mapping[str, Any]],
    contribs: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    logged: Mapping[int, Sequence[int]],
    new_dungeon: bool,
    records: Mapping[str, Any],
    discrepancies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_source = [(s, b) for s, f in contribs for b in f.get("bosses", [])]
    bases: list[dict[str, Any]] = [
        {"name": e["name"], "encounter": e["id"], "order": e["order"], "from": "client"} for e in client_encounters
    ]
    if not bases:  # sans le client : union des boss des sources, dans l'ordre des sources
        seen: set[str] = set()
        for _, b in by_source:
            if norm(b["name"]) not in seen:
                seen.add(norm(b["name"]))
                bases.append({"name": b["name"], "encounter": b.get("encounter"), "order": None, "from": "addons"})
    used: set[int] = set()
    out = []
    kills = records.get("kills") or {}
    loot_records = records.get("loot") or []
    for base in bases:
        matched = []
        for i, (s, b) in enumerate(by_source):
            same_encounter = base["encounter"] is not None and b.get("encounter") == base["encounter"]
            if same_encounter or norm(b["name"]) == norm(base["name"]):
                matched.append((s, b))
                used.add(i)
        npc_field = _field([(s, b.get("npc")) for s, b in matched])
        npc = npc_field["value"] if npc_field else None
        encounter = base["encounter"] or next((b.get("encounter") for _, b in matched if b.get("encounter")), None)
        observed: dict[int, dict[str, int]] = {}
        n_kills = int((kills.get(encounter) or {}).get("n") or 0) if encounter is not None else 0
        for rec in loot_records:
            if (rec.get("boss") and norm(rec["boss"]) == norm(base["name"])) or (npc and rec.get("npc") == npc):
                slot = observed.setdefault(int(rec["item"]), {"drops": 0, "kills": n_kills})
                slot["drops"] += 1
        level = _boss_level(npc, matched, logged)
        if _diverges(level):
            discrepancies.append({"field": f"boss:{base['name']}:level", "values": _values(level)})
        out.append(
            {
                "name": base["name"],
                "encounter": encounter,
                "order": base["order"],
                "npc": npc,
                "level": level,
                "sources": sorted({"client"} if base["from"] == "client" else set()) + sorted({s for s, _ in matched}),
                "loot": _loot(matched, new_dungeon=new_dungeon, observed=observed),
            }
        )
    if client_encounters:
        for i, (s, b) in enumerate(by_source):
            if i not in used:
                discrepancies.append(
                    {"field": "bosses", "values": [{"source": s, "value": b["name"]}], "note": "absent du client"}
                )
    return out


def _values(entry: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not entry:
        return []
    return [{"source": entry["source"], "value": entry["value"]}, *entry["others"]]


def _chains(sources: Sequence[SourceDungeons], book: Any) -> dict[int, list[list[Any]]]:
    """Quête -> chaînes de prérequis (listes ordonnées), toutes sources réunies."""
    out: dict[int, list[list[Any]]] = {}
    for s in sources:
        for quest, chain in s.prereqs.items():
            out.setdefault(int(quest), []).append(list(chain))
    if book is not None:
        from forever.quests import value

        for quest_id, quest in book.quests.items():
            pre = [*(value(quest, "prereq_all") or []), *(value(quest, "prereq_any") or [])[:1]]
            if pre:
                out.setdefault(int(quest_id), []).append(pre)
    return out


def _first_steps(quests: Sequence[int], chains: Mapping[int, list[list[Any]]]) -> list[int]:
    """Prérequis hors du donjon, chaque quête après celles qu'elle exige (chaînes ordonnées)."""
    inside = set(quests)
    requires: dict[int, list[int]] = {}

    def link(chain: list[Any], last: int) -> None:
        previous: int | None = None
        for step in [*chain, last]:
            node = step[0] if isinstance(step, list) and step else step
            if not isinstance(node, int):
                continue
            if previous is not None and previous != node:
                requires.setdefault(node, [])
                if previous not in requires[node]:
                    requires[node].append(previous)
            previous = node

    pending = list(quests)
    done: set[int] = set()
    while pending:
        q = pending.pop(0)
        if q in done:
            continue
        done.add(q)
        for chain in chains.get(q, []):
            link(chain, q)
            pending += [s[0] if isinstance(s, list) else s for s in chain if isinstance(s, int | list) and s]
    order: list[int] = []
    seen: set[int] = set()

    def visit(node: int) -> None:
        if node in seen:
            return
        seen.add(node)
        for pre in requires.get(node, []):
            visit(pre)
        if node not in inside:
            order.append(node)

    for q in quests:
        visit(q)
    return order


def _quests(ids: Iterable[int], book: Any, min_levels: Mapping[int, int]) -> list[dict[str, Any]]:
    from forever.quests import value

    out = []
    for quest_id in dict.fromkeys(ids):
        quest = book.quests.get(quest_id) if book is not None else None
        xp = quest["fields"].get("xp") if quest else None
        out.append(
            {
                "id": quest_id,
                "name": quest["name"] if quest else None,
                "level": value(quest, "level") if quest else None,
                "min_level": min_levels.get(quest_id, value(quest, "min_level") if quest else None),
                "faction": value(quest, "faction") if quest else None,
                "giver": value(quest, "giver") if quest else None,
                "xp": xp["value"] if xp else None,
                "xp_source": xp["source"] if xp else None,
            }
        )
    return out


def merge_dungeons(
    client: Mapping[str, Any] | None,
    sources: Sequence[SourceDungeons],
    *,
    book: Any = None,
    logged_levels: Mapping[int, Sequence[int]] | None = None,
    runs: Sequence[Mapping[str, Any]] = (),
    records: Mapping[str, Any] | None = None,
    official: Mapping[str, Mapping[str, Any]] | None = None,
) -> DungeonBook:
    """Livre des donjons fusionné (sans cache) ; `official` : note officielle par instance (`mechanics.json`,
    `dungeon.official`), placée après le client et avant les addons. Registre : H12, I14, I17"""
    index = _Index(client)
    logged = logged_levels or {}
    notes: list[str] = list((client or {}).get("notes", [])[:1])
    # 1. noms des sources qui donnent l'instance (rattachement des sources qui n'ont qu'un nom)
    raids: set[str] = set()
    for s in sources:
        for key, facts in s.dungeons.items():
            if facts.get("raid"):
                raids.add(str(facts.get("name")))
            elif not key.startswith(("name:", "area:")) and isinstance(facts.get("map"), int):
                wing = index.wing_of(facts["map"], facts.get("name")) if ":" in key else None
                index.add(facts.get("name"), facts["map"], wing)
    # 2. contributions par clé du livre
    contribs: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    unresolved: list[str] = []
    for s in sources:
        for key, facts in s.dungeons.items():
            if facts.get("raid") or str(facts.get("name")) in raids:
                continue
            target: tuple[int | None, str | None]
            if key.startswith("area:"):
                map_id = index.areas.get(int(key[5:]))
                if map_id is None:
                    unresolved.append(f"{s.info.key} : zone {key[5:]} sans instance du client")
                    continue
                target = (map_id, None)
            elif key.startswith("name:"):
                found = index.resolve(key[5:])
                target = found if found else (None, None)
                if not found:
                    unresolved.append(f"{s.info.key} : « {key[5:]} » non rattaché à une instance du client")
            else:
                map_id = int(key.split(":", 1)[0])
                target = (map_id, index.wing_of(map_id, facts.get("name")) if ":" in key else None)
            contribs.setdefault(_book_key(target[0], target[1], facts.get("name") or key[5:]), []).append(
                (s.info.key, facts)
            )
    instances = (client or {}).get("instances") or {}
    winged = {k.split(":", 1)[0] for k in contribs if ":" in k and not k.startswith("name:")}
    for key in instances:
        if key not in winged:
            contribs.setdefault(key, [])
    # une instance à ailes : ses contributions sans aile valent pour chaque aile (portée « instance »)
    instance_wide = {k: contribs.pop(k) for k in list(contribs) if k in winged}
    chains = _chains(sources, book)
    min_levels: dict[int, int] = {}
    for s in sources:
        for q, lv in s.min_levels.items():
            min_levels.setdefault(q, lv)
    book_by_dungeon: dict[str, list[int]] = {}
    if book is not None:
        from forever.quests import value

        for quest_id, quest in book.quests.items():
            name = value(quest, "dungeon")
            if isinstance(name, str):
                found = index.resolve(name)
                key = _book_key(found[0], found[1], name) if found else _book_key(None, None, name)
                book_by_dungeon.setdefault(key, []).append(int(quest_id))
    dungeons: dict[str, dict[str, Any]] = {}
    for key, own in contribs.items():
        map_id = None if key.startswith("name:") else int(key.split(":", 1)[0])
        wing = key.split(":", 1)[1] if map_id is not None and ":" in key else None
        inst = instances.get(str(map_id)) if map_id is not None else None
        ranked = _ranked([*own, *instance_wide.get(str(map_id), [])])
        own_ranked = _ranked(own)
        discrepancies: list[dict[str, Any]] = []
        fields: dict[str, Any] = {}
        off = (official or {}).get(str(map_id), {}) if map_id is not None and not wing else {}
        for name in ("levels", "access_level", "entrance"):
            entry = _field([(OFFICIAL_SOURCE, off.get(name)), *((s, f.get(name)) for s, f in ranked)])
            if entry:
                fields[name] = entry
                if name != "entrance" and _diverges(entry):
                    discrepancies.append({"field": name, "values": _values(entry)})
        if inst:
            lfg_levels = sorted({e["level"] for e in inst["lfg"] if e.get("level") is not None})
            if len(lfg_levels) == 1:
                fields["client_level"] = {"value": lfg_levels[0], "source": "client", "certainty": PROBABLE}
            factions = sorted({e["faction"] for e in inst["lfg"] if e.get("faction")})
            if len(factions) == 1:
                fields["faction"] = {"value": factions[0].lower(), "source": "client", "certainty": PROBABLE}
        new = any(f.get("new") for _, f in ranked)
        closing = [s for s, f in own_ranked if f.get("closed")]
        closed = bool(closing) and not off.get("open")
        if closing and off.get("open"):
            discrepancies.append(
                {
                    "field": "closed",
                    "values": [
                        {"source": OFFICIAL_SOURCE, "value": False},
                        *({"source": s, "value": True} for s in closing),
                    ],
                }
            )
        names = [str(f["name"]) for _, f in own_ranked if isinstance(f.get("name"), str)]
        if wing and map_id is not None:
            base = norm(instances.get(str(map_id), {}).get("name", ""))
            full = [n for n in names if base and base.split()[0] in norm(n).split()]
            label = full[0] if full else f"{instances.get(str(map_id), {}).get('name', map_id)}: {wing.title()}"
            name_field: dict[str, Any] | None = {"value": label}
        else:
            name_field = _field(
                [
                    ("client", inst["name"] if inst else None),
                    *(
                        (s, n)
                        for s, n in zip(
                            [s for s, f in own_ranked if isinstance(f.get("name"), str)], names, strict=True
                        )
                    ),
                ]
            )
        bosses = _bosses(
            inst["encounters"] if inst and not wing else [],
            own_ranked if wing or not inst else ranked,
            logged=logged,
            new_dungeon=new,
            records=records or {},
            discrepancies=discrepancies,
        )
        quest_ids: list[int] = []
        for _, f in own_ranked:
            quest_ids += [q for q in f.get("quests", []) if isinstance(q, int)]
        quest_ids += book_by_dungeon.get(key, [])
        quest_ids = list(dict.fromkeys(quest_ids))
        access: list[dict[str, Any]] = next((list(f["access"]) for _, f in ranked if f.get("access")), [])
        dungeons[key] = {
            "id": key,
            "instance": map_id,
            "wing": wing,
            "name": name_field["value"] if name_field else key,
            "new": new,
            "closed": closed,
            "aliases": sorted(
                {*names, *(e["name"] for e in (inst or {}).get("lfg", []))}
                - {name_field["value"] if name_field else ""}
            ),
            "fields": fields,
            "bosses": bosses,
            "quests": _quests(quest_ids, book, min_levels),
            "first_steps": _first_steps(quest_ids, chains),
            "access": access,
            "runs": [dict(r) for r in runs if r.get("instance_id") == map_id and map_id is not None],
            "sources": [*(["client"] if inst else []), *dict.fromkeys(s for s, _ in own_ranked)],
            "discrepancies": discrepancies,
        }
    infos = (
        [
            {
                "source": "client",
                "label": "client (tables Map, LFGDungeons, ContentTuning, DungeonEncounter)",
                "addon": DUNGEON_FILE,
                "version": (client or {}).get("build"),
                "certainty": CERTAIN,
                "dungeons": len(instances),
            }
        ]
        if client
        else []
    )
    infos += [
        {
            "source": s.info.key,
            "label": DUNGEON_SOURCE_LABELS.get(s.info.key, s.info.key),
            "addon": s.info.addon,
            "version": s.info.version,
            "certainty": s.info.certainty,
            "dungeons": len(s.dungeons),
        }
        for s in sources
    ]
    for s in sources:
        notes += s.notes
    notes += sorted(set(unresolved))
    if raids:
        notes.append(
            f"{len(raids)} raid(s) rangé(s) dans un journal de donjons, écarté(s) du livre : {', '.join(sorted(raids))}"
        )
    return DungeonBook(dungeons, infos, notes, "", False)


# --- livre du joueur (cache) ----------------------------------------------------------------------------------------


def _wow(deps: Deps, wow_dir: Path | None) -> Path:
    from forever.errors import InvalidArgumentError

    wow = wow_dir or deps.wow_dir
    if wow is None:
        raise InvalidArgumentError("Dossier du client inconnu.", "définir FOREVER_WOW_DIR ou donner wow_dir")
    return wow


def _logger_records(wtf: Path) -> tuple[list[dict[str, Any]], dict[int, dict[str, int]], list[dict[str, Any]]]:
    """Passages, victoires par rencontre et butin relevés par ForeverLogger 0.6.0 (tous les comptes)."""
    from forever.errors import ForeverError
    from forever.pipeline.addon_sv import read_logger_db

    runs: list[dict[str, Any]] = []
    kills: dict[int, dict[str, int]] = {}
    loot: list[dict[str, Any]] = []
    for path in sorted(wtf.glob("Account/*/SavedVariables/ForeverLogger.lua")) if wtf.is_dir() else []:
        try:
            db = read_logger_db(path)
        except ForeverError:
            continue
        for character in db.characters.values():
            for r in character.runs:
                runs.append(
                    {
                        "instance_id": r.instance_id,
                        "entered": r.entered,
                        "left": r.left,
                        "seconds": r.seconds,
                        "level": r.level,
                        "group": r.group_size,
                        "source": "forever_logger",
                    }
                )
                for e in r.encounters:
                    if e.id is not None and e.success:
                        kills.setdefault(e.id, {"n": 0})["n"] += 1
            for event in character.loot:
                loot += [{"item": i["item"], "npc": i.get("npc")} for i in event.items if i.get("npc")]
    return runs, kills, loot


def _fingerprint(files: Sequence[Path], data_id: str, quests_fp: str) -> str:
    h = hashlib.sha256(json.dumps([MERGE_FORMAT, data_id, quests_fp]).encode("utf-8"))
    for path in files:
        h.update(str(path.name).encode("utf-8"))
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def build_dungeons(deps: Deps, *, wow_dir: Path | None = None, rebuild: bool = False) -> DungeonBook:
    """Livre des donjons du dossier du client `wow_dir` (défaut : `deps.wow_dir`), relu dans le cache si aucune
    empreinte n'a changé (`rebuild` : reconstruit)."""
    from forever.pipeline import dungeon_sources as ds
    from forever.quests import build_quests
    from forever.store import load_version

    wow = _wow(deps, wow_dir)
    addons, wtf = wow / "Interface" / "AddOns", wow / "WTF"
    data = load_version(deps)
    client = data.read_json(DUNGEON_FILE) if (data.path / DUNGEON_FILE).is_file() else None
    monsters = data.read_json(MONSTERS_FILE) if (data.path / MONSTERS_FILE).is_file() else None
    quest_book = build_quests(deps, wow_dir=wow)
    logger_files = sorted(wtf.glob("Account/*/SavedVariables/ForeverLogger.lua")) if wtf.is_dir() else []
    fingerprint = _fingerprint(
        [*ds.dungeon_source_files(addons, wtf), *logger_files],
        f"{data.game_version}:{data.data_sha}",
        quest_book.fingerprint,
    )
    cache = deps.cache_dir / CACHE_DIR / f"{fingerprint}.json"
    if cache.is_file() and not rebuild:
        try:
            doc = json.loads(cache.read_text(encoding="utf-8"))
            return DungeonBook(doc["dungeons"], doc["sources"], doc["notes"], fingerprint, True)
        except (OSError, ValueError, KeyError):
            pass  # cache illisible : rebâti
    readers = (
        ds.read_naowh_journal,
        ds.read_fojji,
        ds.read_fdj_dungeons,
        ds.read_guide_dungeons,
        ds.read_atlasloot,
        ds.read_companion,
        ds.read_zoneinfo,
    )
    sources = [s for s in (r(addons) for r in readers) if s is not None]
    naowh = ds.read_naowh_runs(wtf)
    fl_runs, fl_kills, fl_loot = _logger_records(wtf)
    kills: dict[int, dict[str, int]] = {
        k: {"n": int(v.get("n") or 0)} for k, v in (naowh.kills if naowh else {}).items()
    }
    for k, v in fl_kills.items():
        kills.setdefault(k, {"n": 0})["n"] += v["n"]
    records = {"kills": kills, "loot": [*(naowh.loot if naowh else []), *fl_loot]}
    runs = [*fl_runs, *(naowh.runs if naowh else [])]
    from forever.gamedata import MECHANICS_FILE

    official = (data.read_json(MECHANICS_FILE)["values"].get(OFFICIAL_KEY) or {}).get("value") or {}
    merged = merge_dungeons(
        client,
        sources,
        book=quest_book,
        logged_levels=logged_boss_levels(monsters),
        runs=runs,
        records=records,
        official=official,
    )
    infos = list(merged.sources)
    if naowh is not None:
        infos.append(
            {
                "source": "naowh_sv",
                "label": DUNGEON_SOURCE_LABELS["naowh_sv"],
                "addon": naowh.info.addon,
                "version": None,
                "certainty": naowh.info.certainty,
                "dungeons": len({r.get("instance_id") for r in naowh.runs}),
            }
        )
    notes = list(merged.notes)
    if naowh is not None and not any(r["source"] == "instance_tracker" for r in naowh.runs):
        notes.append("InstanceTracker de Naowh Forever : aucun passage relevé (module désactivé ou pas encore joué)")
    book = DungeonBook(merged.dungeons, infos, notes, fingerprint, False)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(
        json.dumps(
            {"dungeons": book.dungeons, "sources": book.sources, "notes": book.notes}, ensure_ascii=False
        ).encode("utf-8")
    )
    return book


# --- consultation ---------------------------------------------------------------------------------------------------


def resolve(book: DungeonBook, text: str) -> str | None:
    """Clé d'un donjon du livre d'après sa clé, son identifiant ou son nom (aile comprise) ; None sinon."""
    if text in book.dungeons:
        return text
    n = norm(text)
    exact = [k for k, d in book.dungeons.items() if norm(d["name"]) == n]
    if len(exact) == 1:
        return exact[0]
    by_alias = [k for k, d in book.dungeons.items() if any(norm(a) == n for a in d.get("aliases", []))]
    if len(by_alias) == 1:
        return by_alias[0]
    wings = [
        k for k, d in book.dungeons.items() if d["wing"] and n.endswith(" " + d["wing"]) and d["instance"] is not None
    ]
    wings = [k for k in wings if n.startswith(norm(book.dungeons[k]["name"]).split(" ")[0])]
    return wings[0] if len(wings) == 1 else (f"name:{n}" if f"name:{n}" in book.dungeons else None)


def _level_range(dungeon: Mapping[str, Any]) -> dict[str, int] | None:
    entry = dungeon["fields"].get("levels")
    return entry["value"] if entry else None


def lookup_dungeons(book: DungeonBook, *, level: int | None = None, faction: str | None = None) -> list[dict[str, Any]]:
    """Résumé des donjons, filtrés par niveau (dans la plage retenue) et par camp."""
    out = []
    for key, d in sorted(book.dungeons.items(), key=lambda kv: ((_level_range(kv[1]) or {}).get("min", 0), kv[0])):
        rng = _level_range(d)
        if level is not None and (rng is None or not rng["min"] <= level <= rng["max"]):
            continue
        own = d["fields"].get("faction")
        if faction is not None and own and own["value"] != faction:
            continue
        out.append(
            {
                "id": key,
                "name": d["name"],
                "levels": rng,
                "levels_source": (d["fields"].get("levels") or {}).get("source"),
                "client_level": (d["fields"].get("client_level") or {}).get("value"),
                "new": d["new"],
                "closed": d["closed"],
                "bosses": len(d["bosses"]),
                "quests": len(d["quests"]),
                "discrepancies": len(d["discrepancies"]),
            }
        )
    return out


def dungeon_info(
    book: DungeonBook,
    key: str,
    *,
    class_name: str | None = None,
    level: int | None = None,
    items: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fiche d'un donjon ; avec une classe ou un niveau, chaque objet porte `usable` (classes permises du client) et
    `level_ok` (niveau requis), None si l'objet n'est pas connu (maîtrise d'armure et d'armes non vérifiée)."""
    from forever.errors import InvalidArgumentError

    found = resolve(book, key)
    if found is None:
        raise InvalidArgumentError(f"Donjon inconnu : {key}.", "forever dungeon list donne les donjons connus")
    d = copy.deepcopy(book.dungeons[found])
    mask = CLASS_MASKS.get(class_name.strip().lower()) if class_name else None
    for b in d["bosses"]:
        for entry in b["loot"]:
            row = (items or {}).get(entry["item"])
            if mask is not None:
                allowed = int(row["AllowableClass"]) if row else None
                entry["usable"] = None if allowed is None else (allowed <= 0 or bool(allowed & mask))
            if level is not None:
                entry["level_ok"] = None if row is None else int(row["RequiredLevel"]) <= level
    return d


def where_item(book: DungeonBook, item: int) -> list[dict[str, Any]]:
    """Où trouver un objet : donjon, boss, taux retenu, source et version de la source."""
    versions = {s["source"]: s.get("version") for s in book.sources}
    out = []
    for key, d in book.dungeons.items():
        for b in d["bosses"]:
            for entry in b["loot"]:
                if entry["item"] == item:
                    out.append(
                        {
                            "dungeon": key,
                            "dungeon_name": d["name"],
                            "boss": b["name"],
                            "rate": entry["rate"],
                            "source": entry["rate_source"],
                            "version": versions.get(entry["rate_source"]),
                            "classic": bool(entry.get("classic")),
                            "certainty": entry["certainty"],
                            "sources": entry["sources"],
                        }
                    )
    return out


def render_report(book: DungeonBook) -> str:
    """Agrégats du livre pour le dépôt (`docs/research/donjons-forever.md`) : comptes par donjon et par source,
    écarts de plages et de boss ; ni taux, ni objets, ni texte d'addon (décision 133)."""
    lines = [
        "# Donjons de Forever : agrégats du livre fusionné (DJ1)",
        "",
        "Généré par `forever dungeon report` ; comptes et écarts seulement (décision 133).",
        "",
        "## Sources",
        "",
        "| Source | Addon | Version | Donjons |",
        "| --- | --- | --- | --- |",
    ]
    lines += [f"| {s['source']} | {s['addon']} | {s.get('version') or '—'} | {s['dungeons']} |" for s in book.sources]
    lines += [
        "",
        "## Donjons",
        "",
        "| Donjon | Clé | Sources | Boss | Quêtes | Objets avec un taux | Écarts |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, d in sorted(book.dungeons.items(), key=lambda kv: kv[1]["name"]):
        rated = sum(1 for b in d["bosses"] for e in b["loot"] if e["rate"] is not None)
        lines.append(
            f"| {d['name']} | `{key}` | {', '.join(d['sources'])} | {len(d['bosses'])} | {len(d['quests'])} | "
            f"{rated} | {len(d['discrepancies'])} |"
        )
    lines += ["", "## Écarts de plages de niveau", ""]
    for key, d in sorted(book.dungeons.items(), key=lambda kv: kv[1]["name"]):
        entry = d["fields"].get("levels")
        if entry and _diverges(entry):
            values = ", ".join(f"{v['source']} {v['value']['min']}-{v['value']['max']}" for v in _values(entry))
            lines.append(f"- {d['name']} : {values}")
    lines += ["", "## Notes", "", *(f"- {n}" for n in book.notes), ""]
    return "\n".join(lines)
