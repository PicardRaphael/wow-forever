"""Mise à jour automatique des données (`forever update`, T08d, bloc E, décisions 178 à 181).

Un passage enchaîne, sans calcul de combat, des fonctions existantes : archivage des fichiers du client, clone dédié
(`<cache>/update/repo`), version du jeu (build du client publié sur wago.tools), nouvelle version ou correctifs du
serveur (téléchargement, décodage, `verify`, installation dans une copie de préparation, report des valeurs faites à
la main, preuve d'entrées par moteur, rejeu ciblé), journaux de combat de la version installée, addons de données.

Règle d'automatisme (`decide`, décision 180) : une écriture se fait seulement si `verify` est vert, si aucune valeur
faite à la main n'est perdue ni remplacée et si les entrées de chaque moteur calculé sont identiques. Sinon, attente
d'accord (`<cache>/update/pending/<id>.json`), approuvée par `forever update approve <id>` tant que sa base n'a pas
bougé. L'écriture passe par le clone et le chemin git de `forever/pipeline/gitops.py` ; l'arbre de travail de la
session n'est jamais touché.

Le réseau (wago.tools, WoWDBDefs, git et `gh`) passe par `forever/pipeline/` et par le `Runner` injecté : ce module
n'importe aucun module réseau."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict

from forever.carry import CarryReport
from forever.config import Deps
from forever.engine_inputs import InputsDiff

if TYPE_CHECKING:
    from forever.pipeline.gitops import Runner

SCHEMA_VERSION = 1
UPDATE_DIR = "update"
STEPS = ("verrou", "archivage", "clone", "jeu", "nouvelle_version", "correctifs", "journaux", "addons", "fin")
ONLY = ("jeu", "correctifs", "journaux", "addons")
KINDS = ("install_version", "install_revision", "measures", "addon_data", "network_dbd")
STATUSES = ("fait", "rien", "attente", "arrêt", "erreur")
ACTIONS = ("écrire", "attente", "bloqué")
STATES = ("en_attente", "approuvée", "rejetée", "périmée", "faite")
HISTORY_KEPT = 30

Replay = Callable[[str, str, Path], Any]
"""(moteur, cas, dossier des données) -> résultat du cas ; appelé avant puis après, pour les seuls moteurs touchés."""
Measure = Callable[[Deps, Path, Sequence[Path]], Mapping[str, Any]]
"""(deps, dossier des données, journaux) -> {"changed": [{"file", "pointer"}…], …} ; simulation, rien n'est écrit."""
Spawn = Callable[[Sequence[str]], None]
"""Lance un passage détaché (arguments de la commande) ; ne lève jamais."""


class Step(NamedTuple):
    name: str
    status: str  # fait | rien | attente | arrêt | erreur
    detail: str
    data: Mapping[str, Any]


class Verdict(NamedTuple):
    action: str  # écrire | attente | bloqué
    clauses: Mapping[str, bool]
    reasons: list[str]


class UpdateOptions(NamedTuple):
    auto: bool = False
    dry_run: bool = False
    network: bool = True
    only: frozenset[str] = frozenset()


class UpdateReport(TypedDict):
    schema_version: int
    started_at: str
    finished_at: str
    steps: list[dict[str, Any]]
    verdicts: list[dict[str, Any]]
    written: list[dict[str, Any]]
    pending: list[dict[str, Any]]
    origin_main: str | None
    provenance: dict[str, Any]


def update_dir(cache_dir: Path) -> Path:
    """Dossier de travail de `forever update` dans le cache."""
    return cache_dir / UPDATE_DIR


def decide(
    verify_ok: bool,
    carry: CarryReport,
    inputs: Mapping[str, InputsDiff],
    kind: str,
    *,
    install_ok: bool = True,
) -> Verdict:
    """Règle d'automatisme (décision 180), pure : `écrire`, `attente` (clauses non tenues) ou `bloqué` (`verify`
    rouge, installation refusée, ou valeur faite à la main perdue)."""
    raise NotImplementedError


def acquire_lock(deps: Deps, command: str) -> Step | None:
    """Prend le verrou `<cache>/update/lock` ; rend l'étape `arrêt` « déjà en cours » si un verrou vivant existe
    (un verrou plus vieux que `UPDATE_LOCK_STALE` est repris et signalé dans l'étape rendue avec le statut `fait`)."""
    raise NotImplementedError


def release_lock(cache_dir: Path) -> None:
    raise NotImplementedError


def run_update(
    deps: Deps,
    options: UpdateOptions,
    *,
    runner: Runner | None = None,
    replay: Replay | None = None,
    measure: Measure | None = None,
) -> UpdateReport:
    """Un passage complet (étapes `STEPS`) ; `dry_run` : tout est calculé, seul l'archivage écrit (et la préparation
    dans le cache), les attentes sont rendues sans être enregistrées."""
    raise NotImplementedError


def save_report(cache_dir: Path, report: Mapping[str, Any]) -> Path:
    """Écrit le rapport d'un passage (`last.json`, `report-<horodatage>.json`, historique des 30 derniers) ; la base
    des approbations (`origin_main`) est lue dans `last.json`."""
    raise NotImplementedError


def candidate_fingerprint(root: Path) -> str:
    """Empreinte courte (12 caractères) de tous les fichiers d'une candidate ou d'une préparation : une candidate
    réécrite change d'empreinte, et son attente devient périmée."""
    raise NotImplementedError


def exit_code(report: Mapping[str, Any]) -> int:
    """`EXIT_PENDING` si le passage laisse au moins une attente, `EXIT_OK` sinon."""
    raise NotImplementedError


def record_pending(cache_dir: Path, entry: Mapping[str, Any]) -> Path:
    """Enregistre une attente (`<cache>/update/pending/<id>.json`) ; une entrée déjà approuvée ou faite est gardée."""
    raise NotImplementedError


def list_pending(cache_dir: Path) -> list[dict[str, Any]]:
    """Attentes enregistrées, de la plus ancienne à la plus récente."""
    raise NotImplementedError


def approve(
    deps: Deps,
    pending_id: str,
    *,
    wait: bool = False,
    runner: Runner | None = None,
    spawn: Spawn | None = None,
) -> dict[str, Any]:
    """Approuve une attente si sa base n'a pas bougé (sinon `périmée`) et lance un passage (détaché, ou dans ce
    processus avec `wait`) ; une entrée `bloqué` n'est pas approuvable (UsageError)."""
    raise NotImplementedError


def reject(cache_dir: Path, pending_id: str, reason: str | None) -> dict[str, Any]:
    """Rejette une attente en gardant la raison."""
    raise NotImplementedError


def update_summary(cache_dir: Path) -> dict[str, Any]:
    """Dernier passage et attentes, en lecture seule (bloc `update` de `forever_status`, ligne de démarrage)."""
    raise NotImplementedError
