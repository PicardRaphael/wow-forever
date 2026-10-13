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

from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps

PRIORITY = ("client", "questie_forever", "forever_guide", "completo", "naowh_dj", "journeys", "fdj", "questie")
COMPARED = ("level", "min_level", "faction", "prereq_all", "prereq_any", "next", "xp")
CHANGED = ("level", "min_level", "prereq_all", "prereq_any", "xp")
STATUSES = ("nouvelle", "retouchée", "absente des sources Forever", "inchangée", "non couverte")
CACHE_DIR = "quests"

Quest = dict[str, Any]


class QuestBook(NamedTuple):
    quests: dict[int, Quest]
    sources: list[dict[str, Any]]  # source, addon, version, certitude, nombre de quêtes
    fingerprint: str
    from_cache: bool
    notes: list[str]


class OrderResult(NamedTuple):
    order: list[int]
    cycles: list[list[int]]
    missing_prereqs: dict[int, list[int]]


def build_quests(deps: Deps, *, wow_dir: Path | None = None, rebuild: bool = False) -> QuestBook:
    """Liste fusionnée des quêtes du dossier du client `wow_dir` (défaut : `deps.wow_dir`) : addons de
    `Interface/AddOns`, `QuestieForeverDB` des SavedVariables de chaque compte, quêtes vues de `quest_rewards.json`
    installé ; relue dans le cache si aucune empreinte n'a changé (`rebuild` : reconstruite)."""
    raise NotImplementedError


def value(quest: Quest, field: str) -> Any:
    """Valeur retenue d'un champ (None si aucune source ne le donne)."""
    raise NotImplementedError


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
    raise NotImplementedError


def order_quests(book: QuestBook, ids: list[int]) -> OrderResult:
    """Ordre valide des quêtes `ids` (prérequis et chaînes respectés), stable par position puis niveau ; un cycle
    est signalé, les prérequis hors de la sélection sont listés."""
    raise NotImplementedError
