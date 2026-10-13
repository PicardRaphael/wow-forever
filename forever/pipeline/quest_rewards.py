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

from forever.pipeline.questcache import QuestCache
from forever.pipeline.tables import Row

QUEST_FILE = "quest_rewards.json"
QUEST_FILES = (QUEST_FILE,)
SCHEMA_VERSION = 1


def quest_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des quêtes (`quest_tables` de `decode_rules.json`)."""
    raise NotImplementedError


def load_quest_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    raise NotImplementedError


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
    raise NotImplementedError


def seen_quest_xp(doc: Mapping[str, Any], quest_id: int) -> float | None:
    """XP de base d'une quête vue (cellule de `quest_xp` × multiplicateur) ; None si la quête n'a pas été vue ou si
    sa cellule manque."""
    raise NotImplementedError


def new_seen_quests(cache: QuestCache, doc: Mapping[str, Any] | None) -> list[int]:
    """Quêtes du cache absentes de `seen_quests` du document installé, ou dont la ligne a changé (triées)."""
    raise NotImplementedError


def quest_rewards_errors(doc: Any) -> list[str]:
    """Contrôle de forme du document."""
    raise NotImplementedError
