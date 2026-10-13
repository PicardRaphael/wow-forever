"""Récompenses des quêtes décodées du client (`quest_rewards.json`, T04d, bloc B).

Deux parties, toutes deux venues du client :

- `quest_xp` : table `QuestXP` (wago.tools), XP d'une quête par niveau de quête (clé) et par difficulté (colonne) ;
- `seen_quests` : quêtes vues par le client (`questcache.wdb`, lu en local) : niveau, niveau requis, zone, suite,
  difficulté et multiplicateur d'XP, argent. Une quête vue garde sa ligne d'une révision à l'autre : une candidate
  décodée sans cache reprend celles de la version de base, un cache plus récent les remplace quête par quête.

XP d'une quête vue = `quest_xp[niveau][difficulté]` × multiplicateur (avant la règle d'écart de niveau du modèle
d'XP, `forever/engine/xp.py`). Toutes les constantes de lecture viennent de `decode_rules.json` ; aucun chiffre de
jeu ici."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CsvMissingError
from forever.pipeline.fetch import DEFAULT_LOCALE
from forever.pipeline.questcache import QuestCache, QuestRecord
from forever.pipeline.tables import Row, read_table

QUEST_FILE = "quest_rewards.json"
QUEST_FILES = (QUEST_FILE,)
SCHEMA_VERSION = 1


SEEN_FIELDS = (
    "type",
    "level",
    "min_level",
    "sort_id",
    "next_quest",
    "xp_difficulty",
    "xp_multiplier",
    "money",
    "money_difficulty",
    "money_multiplier",
)


def quest_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des quêtes (`quest_tables` de `decode_rules.json`)."""
    return [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("quest_tables", [])]


def load_quest_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    files = quest_table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {name: list(read_table(csv_dir / rel, name)) for name, rel in files}


def _seen(record: QuestRecord) -> dict[str, Any]:
    return {name: getattr(record, name) for name in SEEN_FIELDS}


def decode_quest_rewards(
    tables: Mapping[str, Sequence[Row]],
    rules: Mapping[str, Any],
    version: str,
    *,
    cache: QuestCache | None = None,
    base: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Document `quest_rewards.json` ; `cache` : cache des quêtes du client (None : aucun) ; `base` : document de la
    version de base, dont les quêtes vues sont reprises."""
    spec = rules["quest_rewards"]
    columns = [f"{spec['difficulty_prefix']}{i}" for i in range(int(spec["difficulty_columns"]))]
    quest_xp = {
        str(int(row["ID"])): [int(row[c]) for c in columns]
        for row in sorted(tables["QuestXP"], key=lambda r: int(r["ID"]))
    }
    seen: dict[str, Any] = dict((base or {}).get("seen_quests") or {})
    kept = len(seen)
    if cache is not None:
        seen.update({str(q): _seen(r) for q, r in cache.records.items()})
    seen = {k: seen[k] for k in sorted(seen, key=int)}
    notes = [
        "quest_xp : XP d'une quête par niveau de quête (clé) et par difficulté (colonne), table QuestXP du client",
        (
            "seen_quests : quêtes vues par le client (questcache.wdb lu en local) ; disposition des champs probable "
            "(recoupée par Questie, question LVL6), certitude certain après recoupement par xpReward en jeu"
        ),
        "XP d'une quête vue = quest_xp[niveau][difficulté] × multiplicateur, avant l'écart de niveau (I12)",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "build": version,
        "source": f"Client {version} : table QuestXP (wago.tools) décodée par forever decode ; quêtes vues lues dans "
        "Cache/WDB/enUS/questcache.wdb du client (lecture locale)",
        "difficulty_columns": len(columns),
        "quest_xp": quest_xp,
        "seen_quests": seen,
        "questcache": None
        if cache is None
        else {
            "build": cache.build,
            "locale": cache.locale,
            "records": len(cache.records),
            "kept_from_base": kept,
        },
        "notes": notes,
    }


def seen_quest_xp(doc: Mapping[str, Any], quest_id: int) -> float | None:
    """XP de base d'une quête vue (cellule de `quest_xp` × multiplicateur) ; None si la quête n'a pas été vue ou si
    sa cellule manque."""
    seen = (doc.get("seen_quests") or {}).get(str(quest_id))
    if not seen:
        return None
    row = (doc.get("quest_xp") or {}).get(str(seen["level"]))
    difficulty = int(seen["xp_difficulty"])
    if row is None or not 0 <= difficulty < len(row):
        return None
    return float(row[difficulty]) * float(seen["xp_multiplier"])


def new_seen_quests(cache: QuestCache, doc: Mapping[str, Any] | None) -> list[int]:
    """Quêtes du cache absentes de `seen_quests` du document installé, ou dont la ligne a changé (triées)."""
    installed = (doc or {}).get("seen_quests") or {}
    return sorted(q for q, r in cache.records.items() if installed.get(str(q)) != _seen(r))


def quest_rewards_errors(doc: Any) -> list[str]:
    """Contrôle de forme du document."""
    if not isinstance(doc, dict):
        return [f"{QUEST_FILE} : objet attendu"]
    errors: list[str] = []
    table = doc.get("quest_xp")
    if not isinstance(table, dict) or not table:
        errors.append(f"{QUEST_FILE} : quest_xp : table non vide attendue")
    else:
        width = doc.get("difficulty_columns")
        if any(not isinstance(v, list) or len(v) != width for v in table.values()):
            errors.append(f"{QUEST_FILE} : quest_xp : autant de difficultés à chaque niveau attendu")
    seen = doc.get("seen_quests")
    if not isinstance(seen, dict):
        errors.append(f"{QUEST_FILE} : seen_quests : objet attendu")
    else:
        for quest, entry in seen.items():
            if not isinstance(entry, dict) or any(k not in entry for k in SEEN_FIELDS):
                errors.append(f"{QUEST_FILE} : seen_quests {quest} : champs {', '.join(SEEN_FIELDS)} attendus")
    return errors
