"""Correctifs du serveur lus dans `Logs/Hotfix.log` du client (T08b, bloc E), lecture locale seulement.

Le client réécrit `Hotfix.log` à chaque démarrage : chaque ligne vue est gardée dans un journal en ajout seul,
`<cache>/hotfixes.json` (poussée, table, enregistrement, résultat, date de la ligne, première vue, build du client).
Seules les tables que le projet décode ou lit sont retenues (`decode_rules.json` : `tables`, `class_tables`,
`character_tables`, plus `hotfix_related_tables`), lignes de poussée et réponses `DBReply` ; une ligne répétée compte une fois ; `VALIDATION_RESULT_INVALID` est gardé et compté à part (sens non
établi, `docs/OPEN_QUESTIONS.md`), `NOTPUBLIC` est ignoré. Les valeurs des correctifs (`DBCache.bin`) ne sont pas
lues (T08). Aucun chiffre de jeu ici."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

JOURNAL_NAME = "hotfixes.json"
SCHEMA_VERSION = 1
HOTFIX_LOG = ("Logs", "Hotfix.log")
KEPT = ("VALID", "DELETE", "INVALID")
_LINE = re.compile(
    r"^(?P<month>\d{1,2})/(?P<day>\d{1,2}) (?P<time>\d\d:\d\d:\d\d(?:\.\d+)?)\s+(?P<push>\d+|DBReply) Table "
    r"(?P<table>\w+) RecID (?P<rec>\d+) VALIDATION_RESULT_(?P<result>\w+)"
)


class HotfixLine(NamedTuple):
    at: str  # date et heure locales de la ligne, ISO sans fuseau
    push: str
    table: str
    rec_id: int
    result: str


def parse_hotfix_log(text: str, year: int) -> list[HotfixLine]:
    """Lignes de table du journal ; `year` : année du fichier (le journal n'en porte pas)."""
    out = []
    for line in text.splitlines():
        m = _LINE.match(line)
        if m is None:
            continue
        at = f"{year:04d}-{int(m['month']):02d}-{int(m['day']):02d}T{m['time']}"
        out.append(HotfixLine(at, m["push"], m["table"], int(m["rec"]), m["result"]))
    return out


def read_log(path: Path) -> list[HotfixLine]:
    raise NotImplementedError


def log_year(path: Path) -> int:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).year


def tracked_tables(rules: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("tables", "class_tables", "character_tables", "hotfix_related_tables"):
        value = rules.get(key, [])
        names |= set(value if isinstance(value, list) else value.keys())
    return names


def _key(e: Mapping[str, Any]) -> str:
    return f"{e['push']}|{e['table']}|{e['rec_id']}|{e['result']}"  # une ligne répétée au démarrage compte une fois


def load_journal(cache_dir: Path) -> list[dict[str, Any]]:
    path = cache_dir / JOURNAL_NAME
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = doc.get("entries") if isinstance(doc, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def update_journal(
    cache_dir: Path, lines: Iterable[HotfixLine], tracked: set[str], client_build: str | None, seen_at: datetime
) -> list[dict[str, Any]]:
    """Ajoute les lignes nouvelles des tables suivies ; rend les entrées ajoutées. Rien n'est écrit sans ajout."""
    entries = load_journal(cache_dir)
    known = {_key(e) for e in entries}
    new: list[dict[str, Any]] = []
    for ln in lines:
        if ln.table not in tracked or ln.result not in KEPT:
            continue
        entry = {
            "at": ln.at,
            "push": ln.push,
            "table": ln.table,
            "rec_id": ln.rec_id,
            "result": ln.result,
            "first_seen": seen_at.isoformat(timespec="seconds"),
            "client_build": client_build,
        }
        if _key(entry) in known:
            continue
        known.add(_key(entry))
        new.append(entry)
    if new:
        path = cache_dir / JOURNAL_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"schema_version": SCHEMA_VERSION, "entries": [*entries, *new]}
        path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return new


def group_ranges(ids: Iterable[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for i in sorted(set(ids)):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def summarize(entries: Sequence[Mapping[str, Any]], since: str | None = None) -> dict[str, Any]:
    """Par table : nombre de `VALID` et de `DELETE`, plages d'enregistrements ; `INVALID` à part. `since` : date
    (AAAA-MM-JJ) à partir de laquelle une ligne compte (date de la ligne)."""
    kept = [e for e in entries if since is None or str(e["at"])[:10] >= since]
    tables: dict[str, Any] = {}
    invalid: dict[str, int] = {}
    for e in kept:
        if e["result"] == "INVALID":
            invalid[e["table"]] = invalid.get(e["table"], 0) + 1
            continue
        t = tables.setdefault(e["table"], {"valid": 0, "delete": 0, "ids": set(), "last": ""})
        t["valid" if e["result"] == "VALID" else "delete"] += 1
        t["ids"].add(int(e["rec_id"]))
        t["last"] = max(t["last"], str(e["at"]))
    return {
        "since": since,
        "lines": len(kept),
        "tables": {
            name: {"valid": t["valid"], "delete": t["delete"], "ranges": group_ranges(t["ids"]), "last": t["last"]}
            for name, t in sorted(tables.items())
        },
        "invalid": dict(sorted(invalid.items())),
    }


def _csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def touched_entities(entries: Sequence[Mapping[str, Any]], csv_dir: Path, version_dir: Path) -> list[dict[str, Any]]:
    """Entités du projet touchées par un correctif `VALID` ou `DELETE`, reliées par les CSV du client : sort
    (`SpellMisc`, `SpellName`, `SpellEffect`, `SpellLevels`… par `SpellID` ou `ID`), talent (`CurvePoint` -> courbe ->
    `TraitDefinitionEffectPoints` -> `TraitDefinition.SpellID`, ou `Curve`), bijou PvP (`Item*`)."""
    by_table: dict[str, dict[int, str]] = {}
    for e in entries:
        if e["result"] in ("VALID", "DELETE"):
            day = str(e["at"])[:10]
            prev = by_table.setdefault(str(e["table"]), {}).get(int(e["rec_id"]), "")
            by_table[str(e["table"])][int(e["rec_id"])] = max(prev, day)
    spells = _json(version_dir / "spells.json").get("spells", {})
    spell_of: dict[int, str] = {}
    for key, s in spells.items():
        for sid in (s.get("source") or {}).get("rank_spell_ids", []) or []:
            spell_of[int(sid)] = key
    talent_of: dict[int, str] = {}
    for tree in _json(version_dir / "talents.json").get("trees", []):
        for t in tree.get("talents", []):
            for sid in t.get("spellIds", []) or []:
                talent_of[int(sid)] = str(t["key"])
    found: dict[tuple[str, str], str] = {}

    def hit(kind: str, key: str, day: str) -> None:
        found[(kind, key)] = max(found.get((kind, key), ""), day)

    def spell_hit(spell_id: int, day: str) -> None:
        if spell_id in spell_of:
            hit("spell", spell_of[spell_id], day)
        if spell_id in talent_of:
            hit("talent", talent_of[spell_id], day)

    for table, recs in by_table.items():
        if table in ("SpellName", "Spell"):
            for rec, day in recs.items():
                spell_hit(rec, day)
        elif table.startswith("Spell"):
            for row in _csv(csv_dir / f"{table}.csv"):
                rec = int(row.get("ID", 0) or 0)
                if rec in recs and row.get("SpellID"):
                    spell_hit(int(row["SpellID"]), recs[rec])
    curves: dict[int, str] = dict(by_table.get("Curve", {}))
    if "CurvePoint" in by_table:
        for row in _csv(csv_dir / "CurvePoint.csv"):
            rec = int(row["ID"])
            if rec in by_table["CurvePoint"]:
                cid = int(row["CurveID"])
                curves[cid] = max(curves.get(cid, ""), by_table["CurvePoint"][rec])
    if curves:
        defs = {r["ID"]: int(r["SpellID"]) for r in _csv(csv_dir / "TraitDefinition.csv")}
        for row in _csv(csv_dir / "TraitDefinitionEffectPoints.csv"):
            cid = int(row["CurveID"])
            if cid in curves and row["TraitDefinitionID"] in defs:
                spell_hit(defs[row["TraitDefinitionID"]], curves[cid])
    items = {str(t.get("item_id")) for t in _json(version_dir / "pvp_items.json").get("trinkets", [])}
    for table in ("Item", "ItemSparse"):
        for rec, day in by_table.get(table, {}).items():
            if str(rec) in items:
                hit("item", str(rec), day)
    return [{"kind": k, "key": key, "date": day} for (k, key), day in sorted(found.items())]


def entity_assumptions(cache_dir: Path, version: str, version_dir: Path, kind: str, key: str) -> list[str]:
    """Hypothèse « corrigé par le serveur » pour une entité touchée d'après le journal du cache ; vide sans journal.
    Ne lève jamais (la consultation ne dépend pas du journal)."""
    try:
        entries = load_journal(cache_dir)
        if not entries:
            return []
        from forever.pipeline.fetch import DEFAULT_LOCALE, wago_dir

        csv_dir = wago_dir(cache_dir, version) / DEFAULT_LOCALE
        found = [e for e in touched_entities(entries, csv_dir, version_dir) if e["kind"] == kind and e["key"] == key]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [hotfix_assumption(e) for e in found]


def hotfix_assumption(entity: Mapping[str, Any]) -> str:
    return f"corrigé par le serveur le {entity['date']}, valeur du correctif non lue (T08)"
