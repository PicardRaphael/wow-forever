"""Mise à jour automatique des données (`forever update`, T08d, bloc E, décisions 178 à 181).

Un passage enchaîne, sans calcul de combat, des fonctions existantes : archivage des fichiers du client, clone dédié
(`<cache>/update/repo`), version du jeu (build du client publié sur wago.tools), nouvelle version ou correctifs du
serveur (téléchargement, décodage, `verify`, installation dans une copie de préparation, report des valeurs faites à
la main, preuve d'entrées par moteur ; rejeu ciblé après l'installation), journaux de combat de la version installée, addons de données.

Règle d'automatisme (`decide`, décision 295, qui remplace 180, 198, 207 et 230) : la veille écrit d'elle-même, sauf
quand l'installation casserait l'intégrité (`verify` rouge, écart de fusion que la décision 296 ne tranche pas) ou perdrait une valeur faite à la
main ou une valeur d'un correctif du serveur non relue (`bloqué`, dit, session nécessaire). Ce qui change sans bloquer
(entrées de moteur, valeur faite à la main remplacée) est noté pour la carte « Mis à jour ». Une nouvelle version
attend le `DBCache.bin` de son build (`hotfix_gate`, attente `hotfixes_unread` levée seule). Chaque installation
laisse une fiche (`forever.update_installed`, `<cache>/update/installed/<id>.json`) que « Annuler »
(`forever update undo <id>`) défait par le même chemin. L'écriture passe par le clone et le chemin git de
`forever/pipeline/gitops.py` ; l'arbre de travail de la session n'est jamais touché.

La preuve d'entrées et le report à la main comparent la version installée à la version **après installation** dans
la copie de préparation (`<cache>/update/stage-<version>/data`), jamais à la candidate brute : la candidate porte la
lecture du client avant la fusion des talents et des sorts, et diffère toujours de la version installée.

Le réseau (wago.tools, WoWDBDefs, git et `gh`) passe par `forever/pipeline/` et par le `Runner` injecté : ce module
n'importe aucun module réseau ni `subprocess`."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import os
import re
import shutil
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict

from forever.carry import CarryReport, carry_apply, carry_check
from forever.config import (
    CACHE_TTL,
    REPO_ROOT,
    UPDATE_CI_TIMEOUT,
    UPDATE_HOTFIX_WAIT,
    UPDATE_LOCK_STALE,
    Deps,
    utc_now,
)
from forever.engine_inputs import (
    ABSENT,
    ENGINES,
    EngineDeclarationError,
    InputsDiff,
    ValueChange,
    cases_to_replay,
    compare_inputs,
    hotfix_losses,
    metadata_keys,
    monster_contexts,
    targeted_replay,
)
from forever.errors import (
    EXIT_OK,
    EXIT_PENDING,
    DataSchemaError,
    FetchFailedError,
    ForeverError,
    InvalidArgumentError,
    PathNotFoundError,
)
from forever.pipeline.tables import ColumnNamesError
from forever.store import current_identity
from forever.timefmt import format_utc, parse_utc
from forever.update_installed import save_installed, undone

if TYPE_CHECKING:
    from forever.pipeline.gitops import Runner

SCHEMA_VERSION = 1
UPDATE_DIR = "update"
STEPS = (
    "verrou",
    "archivage",
    "clone",
    "jeu",
    "nouvelle_version",
    "correctifs",
    "journaux",
    "addons",
    "guides",
    "simulateurs",
    "fin",
)
ONLY = ("jeu", "correctifs", "journaux", "addons", "guides", "simulateurs")
KINDS = ("install_version", "install_revision", "measures", "addon_data", "network_dbd", "network")
STATUSES = ("fait", "rien", "attente", "arrêt", "erreur")
ACTIONS = ("écrire", "attente", "bloqué", "relecture")  # attente : se lève seule ; relecture : rappel, sans accord
STATES = ("en_attente", "approuvée", "rejetée", "périmée", "faite")
OPEN_STATES = ("en_attente", "approuvée")
SESSION_KINDS = ("column_names",)
# Attentes levées seules par un passage, jamais approuvables ; « network » : téléchargement en échec après ses essais,
# retenté au passage suivant (décision 230).
SELF_CLEARING_KINDS = ("hotfixes_unread", "network")
AUTO_ORIGINS = frozenset({"client", "correctif_serveur"})  # installation seule d'un moteur qui recopie (décision 207)
INSTALL_KINDS = ("install_version", "install_revision")
LEGACY_REASON = "décision 295 : plus d'accord, la veille installe d'elle-même (annulable)"
# Addons dont les données du dépôt se relisent d'elles-mêmes (décision 295) : la mesure des journaux lit Questie.
REMEASURED_ADDONS = ("Questie",)
KEPT_STATES = ("approuvée", "faite", "rejetée")  # un passage qui recalcule la même attente ne les écrase pas
HISTORY_KEPT = 30
# Délai maximal de chaque étape (sonde en jeu H du 2026-10-10) : au-delà, le passage s'arrête proprement (verrou
# rendu, attente « erreur » `pass_error`). Les étapes qui attendent la CI (jusqu'à 60 min) gardent une marge.
STEP_LIMITS_S: dict[str, float] = {
    "archivage": 15 * 60,
    "clone": 75 * 60,
    "jeu": 10 * 60,
    "nouvelle_version": 150 * 60,
    "correctifs": 120 * 60,  # décision 295 : écriture (CI jusqu'à 60 min) puis rejeu des builds (environ 15 min)
    "journaux": 120 * 60,
    "addons": 120 * 60,  # Questie relu : mesure, écriture et CI comme l'étape des journaux
    "guides": 15 * 60,
    "simulateurs": 45 * 60,
}
STEP_GIT_TIMEOUT_S = 300.0  # délai d'une commande git des guides de Polestar
PASS_TIMEOUT_EXIT = 7
PASS_ERROR_KIND = "pass_error"  # passage arrêté (délai) ou étape en erreur : attente visible, levée au passage réussi
COMMIT_MESSAGE = "Veille : {version} r{revision} installée par forever update ({motif})"
INVENTORY_DOC = "docs/research/valeurs-ecrites-a-la-main.md"  # rendu de `forever origins inventory` (version courante)
PASS_PATHS = ("forever/data/", "docs/research/data-", INVENTORY_DOC)  # seuls chemins du clone écrits par `_publish`
UNDO_BRANCH_PREFIX = "data/undo-"  # branche d'une annulation (`forever update undo`, décision 295)
DATA_BRANCH_RE = re.compile(r"data/(?P<version>\d+\.\d+\.\d+\.\d+)-r(?P<revision>\d+)")
BLOCKED_BY = (
    "uv_sync",
    "verify",
    "ci",
    "gh",
)  # écriture arrêtée en route : pas de nouvel essai tant que main n'a pas bougé
AUTO_COMMAND = "forever update --auto"
CARRY_FR = ("gardé", "réappliqué", "remplacé", "perdu")

Replay = Callable[[str, str, Path], Any]


class SameDataReplayError(ForeverError):
    """Rejeu dont « avant » et « après » désignent les mêmes données (même version, même empreinte) : la comparaison
    ne prouverait rien (défaut relevé à l'installation de 1.60.1.70291, 2026-10-09)."""

    def __init__(self, label: str) -> None:
        super().__init__(
            "same_data_replay",
            f"Rejeu refusé : « avant » et « après » désignent les mêmes données ({label}).",
            "rejouer « après » sur la version candidate installée dans la copie de préparation",
        )


def replay_label(data_dir: Path) -> str:
    """Étiquette du cache des rejeux (`<cache>/builds/`) : version et empreinte réelle des données rejouées, jamais
    l'emplacement du dossier (« avant » et « après » se déduisaient du chemin, 2026-10-09)."""
    identity = current_identity(data_dir)
    return f"update-{identity.game_version}-{identity.data_sha}"


def check_replay_sides(before: Path, after: Path) -> None:
    """Refuse un rejeu dont les deux côtés portent la même version et la même empreinte de données."""
    a, b = current_identity(before), current_identity(after)
    if (a.game_version, a.data_sha) == (b.game_version, b.data_sha):
        raise SameDataReplayError(f"{a.game_version}, données {a.data_sha}")


"""(moteur, cas, dossier des données) -> résultat du cas ; appelé avant puis après, pour les seuls moteurs touchés."""
Measure = Callable[[Deps, Path, Sequence[Path]], Mapping[str, Any]]
"""(deps, dossier des données, journaux) -> {"changed": [{"file", "pointer"}…], "details", "hp_by_level",
"preview"} ; simulation : rien n'est écrit dans les données (`preview` : copie des données où la mesure est écrite,
côté « après » du rejeu ; `details` : `refresh.npc_details` ; `hp_by_level` : niveaux dont les PV changent)."""
Spawn = Callable[[Sequence[str]], None]
"""Lance un passage détaché (arguments de la commande) ; peut lever OSError, attrapée par l'appelant."""
Progress = Callable[[str], None]
"""Reçoit chaque ligne du journal du passage dès qu'elle est connue (la CLI l'écrit sur la sortie d'erreur)."""


class Step(NamedTuple):
    name: str
    status: str  # fait | rien | attente | arrêt | erreur
    detail: str
    data: Mapping[str, Any]


class Verdict(NamedTuple):
    action: str  # écrire | bloqué (décision 295 : plus d'attente)
    clauses: Mapping[str, bool]
    reasons: list[str]  # ce qui bloque
    notes: list[str] = []  # noqa: RUF012 (jamais modifiée en place) ; ce qui change sans bloquer (carte « Mis à jour »)


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


class PendingNotFoundError(PathNotFoundError):
    def __init__(self, pending_id: str) -> None:
        super().__init__("Attente", pending_id, "lister les attentes : forever update status")


# --- Fichiers du dossier de travail --------------------------------------------------------------------------


def update_dir(cache_dir: Path) -> Path:
    """Dossier de travail de `forever update` dans le cache."""
    return cache_dir / UPDATE_DIR


def run_log_path(cache_dir: Path, now: datetime) -> Path:
    """Journal d'un passage, `<cache>/update/run-<horodatage>.log` : passage détaché (hook de démarrage, `approve`)
    ou tâche planifiée (`--log`, décision 226)."""
    stamp = "".join(c for c in format_utc(now) if c.isalnum())
    return update_dir(cache_dir) / f"run-{stamp}.log"


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def _pending_path(cache_dir: Path, pending_id: str) -> Path:
    if not pending_id or any(c in pending_id for c in '/\\:*?"<>|') or pending_id.startswith("."):
        raise PendingNotFoundError(pending_id)
    return update_dir(cache_dir) / "pending" / f"{pending_id}.json"


# --- Règle d'automatisme --------------------------------------------------------------------------------------


def _blocking_changes(diff: InputsDiff) -> list[Any] | None:
    """Feuilles changées d'un moteur qui recopie dont une origine n'est pas permise (`AUTO_ORIGINS`) ; None : un item
    différent sans le détail des feuilles (aucune installation seule sans les origines)."""
    out = []
    for item in diff.items:
        if item.get("status") != "différent":
            continue
        if not item.get("changes"):  # détail absent, ou seulement des conteneurs vides changés
            return None
        for c in item["changes"]:
            sides = [o for o, v in ((c.origin_before, c.before), (c.origin_after, c.after)) if v is not ABSENT]
            if any(o not in AUTO_ORIGINS for o in sides):
                out.append(c)
    return out


def _first(changes: Sequence[ValueChange]) -> str:
    c = changes[0]
    origins = sorted({str(o) for o, v in ((c.origin_before, c.before), (c.origin_after, c.after)) if v is not ABSENT})
    more = f" (et {len(changes) - 1} autre(s))" if len(changes) > 1 else ""
    return f"{c.file} {c.pointer} ({' → '.join(origins) or 'sans règle'}){more}"


def decide(
    verify_ok: bool,
    carry: CarryReport,
    inputs: Mapping[str, InputsDiff],
    kind: str,
    *,
    install_ok: bool = True,
    hotfix_losses: Sequence[ValueChange] = (),
) -> Verdict:
    """Règle d'automatisme (décision 295, qui remplace 180, 198, 207 et 230), pure : `écrire`, sauf `bloqué` quand
    l'installation casserait l'intégrité (`verify` rouge, installation refusée) ou perdrait des données (valeur faite à
    la main perdue, valeur d'un correctif du serveur non relue). Une valeur faite à la main remplacée ou des entrées de
    moteur changées s'écrivent et sont notées (`notes`) pour la carte « Mis à jour ».

    Clause `inputs` : les entrées de chaque moteur qui calcule sont identiques ; celles d'un moteur qui recopie ne
    changent que par des feuilles d'origine `client` ou `correctif_serveur`. Clause `hotfixes` : aucune valeur d'un
    correctif du serveur n'est perdue."""
    for name in inputs:
        if name not in ENGINES:
            raise EngineDeclarationError(f"Moteur {name} : absent de ENGINES, mode non déclaré (décision 207).")
    computing = sorted(n for n, d in inputs.items() if not d.identical and ENGINES[n].mode == "calcule")
    copying: dict[str, list[Any] | None] = {
        n: _blocking_changes(d) for n, d in sorted(inputs.items()) if not d.identical and ENGINES[n].mode == "recopie"
    }
    noted_copies = {n: c for n, c in copying.items() if c is None or c}
    clauses = {
        "verify": verify_ok,
        "install": install_ok,
        "manual": not carry.superseded and not carry.lost,
        "inputs": not computing and not noted_copies,
        "hotfixes": not hotfix_losses,
    }
    reasons: list[str] = []
    notes: list[str] = []
    if not verify_ok:
        reasons.append("verify rouge : l'installation casserait l'intégrité des données")
    if not install_ok:
        reasons.append("installation refusée par les règles de fusion (forever install) : intégrité non garantie")
    for value in carry.lost:
        reasons.append(f"valeur faite à la main perdue : {value.file} {value.pointer} ({value.origin})")
    if hotfix_losses:
        reasons.append(
            f"correctifs du serveur non relus : {len(hotfix_losses)} valeur(s) correctif_serveur perdue(s) "
            f"({_first(hotfix_losses)})"
        )
    for value, now in carry.superseded:
        notes.append(f"valeur faite à la main remplacée : {value.file} {value.pointer} ({value.origin}) → {now!r}")
    if computing:
        notes.append(f"moteurs aux entrées changées : {', '.join(computing)}")
    for name, changes in noted_copies.items():
        if changes is None:
            notes.append(f"{name} : entrées changées sans l'origine des valeurs")
        else:
            notes.append(f"{name} : entrée d'origine {changes[0].origin_after or changes[0].origin_before} changée : "
                         f"{_first(changes)}")  # fmt: skip
    action = "bloqué" if reasons else "écrire"
    return Verdict(action, clauses, reasons, notes)


def dbcache_for_build(
    deps: Deps, build: int, product: str | None, archived: Path | None, *, notes: list[str] | None = None
) -> Path | None:
    """`DBCache.bin` des correctifs d'un build : celui du jeu archivé d'abord ; sinon le cache vérifié le plus récent
    de Raidbots, lu en lecture seule et épinglé (décision 290, certitude au plus `probable`) ; None si Raidbots est
    injoignable (délai des requêtes : `FETCH_TIMEOUT`, téléchargement `raidbots.DOWNLOAD_TIMEOUT`) ou n'a pas ce
    build, la raison ajoutée à `notes`."""
    if archived is not None:
        return archived
    from forever.pipeline import raidbots

    try:
        return raidbots.fetch_dbcache(deps, build, product or "wow_classic_beta")
    except ForeverError as exc:
        if notes is not None and exc.code != "offline":
            unreachable = isinstance(exc, FetchFailedError) and "injoignable" in exc.message
            notes.append(
                exc.message if unreachable else f"Raidbots sans cache vérifié du build {build} ({exc.message})"
            )
        return None


def hotfix_gate(archived: bool, seen_at: datetime | None, now: datetime, wait: timedelta) -> str:
    """Porte des correctifs d'une nouvelle version (décision 207), pure : `lire` (archive de `DBCache.bin` du build
    présente), `attendre` (pas d'archive, délai non écoulé ou première vue du build inconnue), `sans_correctifs`
    (pas d'archive `wait` après la première vue : installation sans correctifs, si aucun n'est perdu)."""
    if archived:
        return "lire"
    if seen_at is None or now - seen_at < wait:
        return "attendre"
    return "sans_correctifs"


# --- Verrou ---------------------------------------------------------------------------------------------------


def _lock_path(cache_dir: Path) -> Path:
    return update_dir(cache_dir) / "lock"


def _lock_dead(doc: Any) -> bool:
    """Vrai si le processus du verrou est mort (correctif du 2026-10-06 : un passage tué laisse son verrou) ; un
    verrou sans `pid`, ou dont on ne peut pas savoir si le processus tourne, suit la seule règle de l'âge."""
    from forever.spawn import pid_alive

    return isinstance(doc, dict) and pid_alive(doc.get("pid")) is False


def _lock_alive(doc: Any, now: datetime) -> bool:
    try:
        started = parse_utc(str(doc["started_at"]))
    except (KeyError, TypeError, ValueError):
        return False
    return now - started < UPDATE_LOCK_STALE and not _lock_dead(doc)


def acquire_lock(deps: Deps, command: str) -> Step | None:
    """Prend le verrou `<cache>/update/lock` ; rend l'étape `arrêt` « déjà en cours » si un verrou vivant existe
    (un verrou plus vieux que `UPDATE_LOCK_STALE`, ou dont le processus est mort, est repris et signalé dans l'étape
    rendue avec le statut `fait`)."""
    path = _lock_path(deps.cache_dir)
    now = deps.now()
    doc = {"pid": os.getpid(), "started_at": format_utc(now), "command": command}
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as f:
            f.write((json.dumps(doc, ensure_ascii=False) + "\n").encode("utf-8"))
        return None
    except FileExistsError:
        pass
    old = _read(path)
    if _lock_alive(old, now):
        held = old if isinstance(old, dict) else {}
        return Step(
            "verrou",
            "arrêt",
            f"déjà en cours depuis {held.get('started_at')} ({held.get('command')}, processus {held.get('pid')})",
            {"lock": held},
        )
    _write(path, doc)
    held = old if isinstance(old, dict) else {}
    if _lock_dead(old):
        at = f" à l'étape {held['step']}" if held.get("step") else ""
        detail = f"verrou repris : processus {held.get('pid')} mort{at} (verrou posé le {held.get('started_at')})"
        return Step("verrou", "fait", detail, {"stale": True, "dead_pid": held.get("pid"), "lock": held})
    return Step("verrou", "fait", f"verrou périmé repris (posé le {held.get('started_at')})", {"stale": True})


def _note_step(cache_dir: Path, current: str | None, steps: Sequence[Step], at: str) -> None:
    """Étape en cours et étapes finies, écrites dans le verrou au fil du passage : un passage tué laisse ainsi où il
    en était (`forever update status`, reprise du verrou)."""
    path = _lock_path(cache_dir)
    doc = _read(path)
    if not isinstance(doc, dict) or doc.get("pid") != os.getpid():
        return
    done = [{"name": s.name, "status": s.status, "detail": s.detail} for s in steps]
    fresh = {"step_at": at, "detail": "", "detail_at": at} if doc.get("step") != current else {}
    _write(path, {**doc, "step": current, "updated_at": at, "steps": done, **fresh})


def note_detail(cache_dir: Path, detail: str, at: str) -> None:
    """Dernière ligne utile du journal du passage, gardée dans le verrou avec son heure : l'étape réelle (« CI
    attendue … ») et sa durée se lisent ainsi pendant le passage (`update_summary`, ligne d'état du jeu)."""
    path = _lock_path(cache_dir)
    doc = _read(path)
    if not isinstance(doc, dict) or doc.get("pid") != os.getpid():
        return
    _write(path, {**doc, "detail": detail, "detail_at": at})


def activity_of(detail: str | None) -> str | None:
    """Activité réelle lue dans la dernière ligne du journal : « attente de la CI », « rejeu des builds »…"""
    text = (detail or "").strip()
    low = text.lower()
    if not text:
        return None
    if "ci attendue" in low:
        return "attente de la CI"
    if low.startswith("rejeu"):
        return "rejeu des builds"
    if "verify" in low:
        return "contrôle (verify)"
    if "uv sync" in low:
        return "synchronisation de l'environnement"
    return text.split(" (")[0][:60]


def release_lock(cache_dir: Path) -> None:
    _lock_path(cache_dir).unlink(missing_ok=True)


# --- Contexte d'un passage ------------------------------------------------------------------------------------


@dataclasses.dataclass
class _Run:
    deps: Deps
    options: UpdateOptions
    runner: Runner | None
    replay: Replay | None
    measure: Measure | None
    base_data: Path
    clone: Path | None = None
    writable: bool = False  # clone synchronisé, propre, sur main : une écriture est possible
    origin_main: str | None = None
    verdicts: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    pending: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    written: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    client: Any = None  # ClientBuild du `.build.info`, lu à l'étape « jeu »
    progress: Progress | None = None
    cleared: dict[str, str] = dataclasses.field(default_factory=dict)  # attente levée seule -> raison

    def say(self, line: str) -> None:
        """Ligne du journal du passage, écrite tout de suite (au fil de l'eau, pas à la fin) ; une ligne d'avancement
        d'étape (« journaux : CI attendue … ») devient le détail de l'étape dans le verrou."""
        if self.progress is not None:
            self.progress(f"{self.now} {line}")
        step, sep, rest = line.partition(" : ")
        if sep and step in STEPS and rest != "en cours" and not rest.startswith(tuple(f"{s} ·" for s in STATUSES)):
            note_detail(self.deps.cache_dir, rest, self.now)

    def wants(self, group: str) -> bool:
        return not self.options.only or group in self.options.only

    @property
    def now(self) -> str:
        return format_utc(self.deps.now())

    def deps_on(self, data_dir: Path) -> Deps:
        return dataclasses.replace(self.deps, data_dir=data_dir, offline=self.deps.offline or not self.options.network)


def installed_versions(data_dir: Path) -> list[str]:
    """Versions installées, lues dans le manifeste suivi par git (`manifest.json` : celui de `main` dans le clone
    synchronisé), jamais d'après les dossiers présents : un dossier laissé par un passage interrompu n'installe rien
    (correctif du 2026-10-06). Sans manifeste, les dossiers de version."""
    from forever.manifest import load_manifest, version_dirs
    from forever.pipeline.builds import version_key

    manifest = load_manifest(data_dir)
    if manifest is None:
        return version_dirs(data_dir)
    return sorted(manifest["versions"], key=version_key)


def _installed(data_dir: Path) -> str | None:
    """Version courante : `game_version` du manifeste (dernier dossier de version sans manifeste)."""
    from forever.manifest import load_manifest

    manifest = load_manifest(data_dir)
    if manifest is None:
        versions = installed_versions(data_dir)
        return versions[-1] if versions else None
    current = manifest.get("game_version")
    return str(current) if current else None


def _revision(data_dir: Path, version: str) -> int:
    from forever.store import read_sources

    sources = read_sources(data_dir, version) or {}
    try:
        return int(sources.get("revision") or 1)
    except (TypeError, ValueError):
        return 1


def _rules(data_dir: Path) -> dict[str, Any]:
    from forever.pipeline.decode import load_rules

    return load_rules(data_dir)[1]


def _build_number(version: str) -> str:
    return version.rsplit(".", 1)[-1]


# --- Étapes ---------------------------------------------------------------------------------------------------


def _step_archive(run: _Run) -> Step:
    step = _archive_client(run)
    if not run.options.auto or run.options.dry_run:
        return step
    # LN1 (décision 271) : sauvegarde du jour au passage automatique (tâche de 08:00, passages du pont), jeu fermé
    from forever.backup import daily

    try:
        made = daily(run.deps, run.deps.now())
    except (OSError, ValueError) as exc:
        return step._replace(detail=f"{step.detail} ; sauvegarde du jour en échec : {exc}")
    if made is None:
        return step
    data = {**step.data, "backup": str(made)}
    return step._replace(status="fait", detail=f"{step.detail} ; sauvegarde du jour : {made}", data=data)


def _archive_client(run: _Run) -> Step:
    from forever.archive import archive_client_files

    if run.deps.wow_dir is None or not run.deps.wow_dir.is_dir():
        return Step("archivage", "rien", "dossier du client absent", {})
    result = archive_client_files(run.deps)
    new = [{"kind": c.kind, "build": c.build, "file": c.path.name} for c in result.copies if c.new]
    if result.errors:
        return Step("archivage", "fait", f"{len(new)} copie(s), {len(result.errors)} fichier(s) illisible(s)", {
            "copies": new, "errors": result.errors,
        })  # fmt: skip
    return Step("archivage", "fait" if new else "rien", f"{len(new)} nouvelle(s) copie(s)", {"copies": new})


def _repo_url(run: _Run, runner: Runner) -> str:
    from forever.pipeline.gitops import origin_url

    path = update_dir(run.deps.cache_dir) / "config.json"
    config = _read(path)
    if isinstance(config, dict) and isinstance(config.get("repo_url"), str):
        return str(config["repo_url"])
    url = origin_url(runner, REPO_ROOT)
    _write(path, {"repo_url": url})
    return url


def _step_clone(run: _Run) -> Step:
    from forever.pipeline import gitops

    if run.options.dry_run:
        return Step("clone", "rien", "simulation : clone non touché, données de la session lues", {})
    if not run.options.network:
        return Step("clone", "rien", "hors ligne : clone non synchronisé, rien ne sera écrit", {})
    runner = run.runner or gitops.subprocess_runner
    clone = update_dir(run.deps.cache_dir) / "repo"
    gitops.ensure_clone(runner, _repo_url(run, runner), clone)
    resumed = _resume_branch(run, runner, clone)
    sync = gitops.sync_main(runner, clone, PASS_PATHS)
    run.clone, run.origin_main = clone, sync.origin_main
    run.base_data = clone / "forever" / "data"
    data = {"origin_main": sync.origin_main, "discarded": list(sync.discarded), "dirty": list(sync.dirty)}
    if resumed:
        data["resumed"] = resumed
    prefix = f"{resumed} ; " if resumed else ""
    if not sync.ok:
        shown = ", ".join(sync.dirty[:5]) + (f" et {len(sync.dirty) - 5} autre(s)" if len(sync.dirty) > 5 else "")
        paths = f" : {shown}" if sync.dirty else ""
        return Step("clone", "arrêt", f"{prefix}clone dédié refusé : {sync.reason}{paths} ({clone})", data)
    run.writable = True
    detail = prefix + ("clone avancé sur origin/main" if sync.advanced else "clone à jour")
    if sync.discarded:
        detail += f" ; reste d'un passage interrompu retiré ({len(sync.discarded)} chemin(s))"
    return Step("clone", "fait", detail, {**data, "advanced": sync.advanced})


def _resume_branch(run: _Run, runner: Runner, clone: Path) -> str | None:
    """Clone laissé sur une branche de données `data/<version>-r<N>` par un passage tué (réponse 3 de l'utilisateur
    du 2026-10-06) : la branche déjà fusionnée est retirée ; poussée et en avance rapide sur `origin/main`, sa CI est
    attendue puis elle est fusionnée ; sinon (jamais poussée, `main` a bougé, CI rouge), le clone revient sur `main`
    (CI rouge : attente bloquée, branche distante gardée pour l'examen). Rend la phrase du détail de l'étape, None
    si le clone n'est pas sur une branche de données."""
    from forever.pipeline import gitops

    branch = gitops.current_branch(runner, clone)
    if branch.startswith(UNDO_BRANCH_PREFIX):  # « Annuler » tué en route (décision 295) : retour sur main, à relancer
        dirty = gitops.dirty_paths(runner, clone)
        if any(not p.startswith(PASS_PATHS) for p in dirty):
            return None
        if dirty:
            gitops.discard_changes(runner, clone, dirty)
        gitops.leave_branch(runner, clone, branch)
        gitops.drop_stale_branch(runner, clone, branch)
        return f"reprise : {branch} (annulation interrompue) abandonnée, clone revenu sur main ; relancer « Annuler »"
    found = DATA_BRANCH_RE.fullmatch(branch)
    if found is None:
        return None
    version, revision = found["version"], int(found["revision"])
    gitops.fetch(runner, clone)
    dirty = gitops.dirty_paths(runner, clone)
    if any(not p.startswith(PASS_PATHS) for p in dirty):
        return None  # sale hors des chemins du passage : `sync_main` refuse et nomme la branche
    if dirty:
        gitops.discard_changes(runner, clone, dirty)
    head = gitops.head_sha(runner, clone)
    origin_main = gitops.head_sha(runner, clone, "origin/main")
    vdir = clone / "forever" / "data" / version
    pending_id = f"{version}-r{revision}-{content_fingerprint(vdir)}" if vdir.is_dir() else None
    info: dict[str, Any] = {"version": version, "revision": revision, "branch": branch, "sha": head, "resumed": True}
    if gitops.is_ancestor(runner, clone, head, "origin/main"):
        gitops.leave_branch(runner, clone, branch)
        gitops.drop_stale_branch(runner, clone, branch)  # branche distante, si elle reste
        run.written.append(info)
        return f"reprise : {branch} déjà fusionnée dans main, branche retirée"
    remote = gitops.remote_branch_sha(runner, clone, branch)
    if remote == head and gitops.is_ancestor(runner, clone, "origin/main", head):
        run.say(f"clone : reprise de {branch} ({head[:12]}), CI attendue")
        ci = gitops.wait_ci(runner, clone, branch, head, UPDATE_CI_TIMEOUT.total_seconds())
        info.update(ci=ci.url, jobs=ci.jobs)
        if ci.ok:
            merged = gitops.merge_ff_and_push(runner, clone, branch)
            if merged.ok:
                gitops.delete_branch(runner, clone, branch)
                run.written.append(info)
                return f"reprise de {branch} : CI verte, fusionnée dans main"
            reason = "main distant a bougé pendant la reprise"
        else:
            reason = f"CI {ci.status} sur {branch} ({ci.url})"
            if pending_id is not None:
                _block(
                    run, pending_id=pending_id, version=version, revision=revision, by="ci", origin_main=origin_main,
                    reason=f"{reason} : rien fusionné, branche gardée à distance", extra={"ci": ci.url, "jobs": ci.jobs},
                )  # fmt: skip
    elif remote is None:
        reason = "jamais poussée"
    else:
        reason = "main distant a bougé, ou branche distante différente"
    gitops.leave_branch(runner, clone, branch)
    return f"reprise : {branch} abandonnée ({reason}), clone revenu sur main"


def _step_game(run: _Run) -> tuple[Step, str | None]:
    from forever.pipeline.builds import list_builds, version_key
    from forever.pipeline.client_builds import read_build_info, wago_product
    from forever.store import read_sources

    if not run.wants("jeu"):
        return Step("jeu", "rien", "non demandé (--only)", {}), None
    wow = run.deps.wow_dir
    run.client = read_build_info(wow) if wow is not None and wow.is_dir() else None
    if run.client is None:
        return Step("jeu", "rien", "build du client inconnu (.build.info absent)", {}), None
    client = str(run.client.build)
    installed = _installed(run.base_data)
    data: dict[str, Any] = {"client": client, "installed": installed, "target": None, "newer_on_wago": None}
    if client in installed_versions(run.base_data):
        return Step("jeu", "rien", f"version du client {client} déjà installée", data), None
    if installed is not None and version_key(client) < version_key(installed):
        return Step("jeu", "rien", f"client {client} plus ancien que la version installée {installed}", data), None
    if not run.options.network:
        return Step("jeu", "rien", "hors ligne : builds publiés non relevés", data), None
    sources = read_sources(run.base_data, installed) if installed else None
    # LN1 : produit de la version finale adoptée quand c'est l'installation lue, sinon celui des données
    found = wago_product(run.deps.cache_dir, wow, sources)
    if found is None:
        return Step("jeu", "erreur", f"produit inconnu : sources.json incomplet pour {installed}", data), None
    product, prefix = found
    data["product"] = product
    published = {b.version for b in list_builds(run.deps, product, prefix)}
    newer = [v for v in published if version_key(v) > version_key(client)]
    data["newer_on_wago"] = max(newer, key=version_key) if newer else None
    note = f" ; {data['newer_on_wago']} publiée, plus récente que le client (suivie par build-watch)" if newer else ""
    if client not in published:
        return Step("jeu", "rien", f"client {client} en attente de wago{note}", data), None
    data["target"] = client
    return Step("jeu", "fait", f"cible : {client} (build du client, publié){note}", data), client


def _fetch_version(run: _Run, version: str, rules: Mapping[str, Any]) -> list[str]:
    """Télécharge les tables de `version` (trois essais par table, chacun noté au journal du passage, décision 230) ;
    rend les tables de noms d'une autre locale restées en échec (« frFR/ItemPetFood ») : facultatives, la version se
    décode sans elles. FetchFailedError si une table qui porte des valeurs de calcul (locale par défaut, GameTables)
    reste en échec."""
    from forever.pipeline.decode import missing_names
    from forever.pipeline.fetch import fetch_gametables, fetch_tables, wago_dir

    deps = run.deps_on(run.base_data)
    enus: list[str] = []
    localized: dict[str, list[str]] = {}
    for key in ("tables", "class_tables", "character_tables", "pet_tables"):
        enus += [t for t in rules.get(key, []) if t not in enus]
    for key in ("localized_tables", "localized_class_tables", "localized_pet_tables"):
        for locale, names in (rules.get(key) or {}).items():
            localized.setdefault(locale, [])
            localized[locale] += [t for t in names if t not in localized[locale]]
    fetch_tables(deps, version, enus, log=run.say)
    for locale, names in localized.items():
        try:
            fetch_tables(deps, version, names, locales=[locale], log=run.say)
        except FetchFailedError as exc:  # noms d'une autre locale : facultatifs (décision 230)
            run.say(f"noms {locale} facultatifs : {exc.message}")
    quest_tables = [t for t in rules.get("quest_tables", []) if t not in enus]
    if quest_tables:
        try:
            fetch_tables(deps, version, quest_tables, log=run.say)
        except FetchFailedError as exc:  # T04d : sans QuestXP, quest_rewards.json est hérité de la base
            run.say(f"tables des quêtes facultatives : {exc.message}")
    xp_tables = [t for t in rules.get("xp_bonus_tables", []) if t not in enus]
    if xp_tables:
        try:
            fetch_tables(deps, version, xp_tables, log=run.say)
        except FetchFailedError as exc:  # T04f : sans PlayerCondition, xp_bonuses.json est hérité de la base
            run.say(f"tables des bonus d'XP facultatives : {exc.message}")
    dungeon_tables = [t for t in rules.get("dungeon_tables", []) if t not in enus]
    if dungeon_tables:
        try:
            fetch_tables(deps, version, dungeon_tables, log=run.say)
        except FetchFailedError as exc:  # DJ1 : sans elles, dungeons.json est hérité de la base
            run.say(f"tables des donjons facultatives : {exc.message}")
    travel_tables = [t for t in rules.get("travel_tables", []) if t not in enus]
    if travel_tables:
        try:
            fetch_tables(deps, version, travel_tables, log=run.say)
        except FetchFailedError as exc:  # RX1 : sans elles, travel.json est hérité de la base
            run.say(f"tables des trajets facultatives : {exc.message}")
    if rules.get("gametables"):
        fetch_gametables(deps, version, rules["gametables"], log=run.say)
    run.cleared[f"network-{version}"] = "téléchargement réussi"
    return missing_names(wago_dir(deps.cache_dir, version), rules)


def _network_wait(run: _Run, step: str, version: str, err: ForeverError) -> Step:
    """Attente « réseau » (décision 230) : une table qui porte des valeurs de calcul reste en échec après ses essais.
    Non approuvable, retentée et levée seule au passage suivant."""
    pending_id = f"network-{version}"
    run.pending.append(
        {
            "id": pending_id,
            "kind": "network",
            "action": "attente",
            "version": version,
            "revision": None,
            "clauses": {},
            "reasons": [err.message],
            "created_at": run.now,
            "base": {"origin_main": run.origin_main, "version": _installed(run.base_data)},
            "commands": [NETWORK_HINT],
        }
    )
    return Step(step, "attente", f"réseau : {err.message} (nouvel essai au passage suivant)", {"id": pending_id})


class _NeedLayouts(Exception):
    def __init__(self, tables: list[str], why: str) -> None:
        super().__init__(why)
        self.tables, self.why = tables, why


def _hotfix_source(run: _Run, version: str, archive: Path, rules: Mapping[str, Any], tables: Sequence[str]) -> Any:
    """Source des correctifs de l'archive ; `_NeedLayouts` si des tables touchées n'ont pas de disposition (relevé de
    WoWDBDefs fait au besoin quand le réseau est permis, décision 179)."""
    from forever.errors import DataSchemaError
    from forever.pipeline import hotfixes
    from forever.pipeline.fetch import dbd_tables, fetch_dbd, read_dbd_index
    from forever.pipeline.hotfix_overlay import hotfix_source, load_dbd_layouts

    wanted = dbd_tables(rules)
    if read_dbd_index(run.deps.cache_dir) is None or run.options.network:
        if not run.options.network:
            raise _NeedLayouts(sorted(set(tables)), "aucun relevé de WoWDBDefs dans le cache, et passage hors ligne")
        fetch_dbd(run.deps_on(run.base_data), version, wanted)
    try:
        layouts, dbd = load_dbd_layouts(run.deps.cache_dir, version, wanted)
    except DataSchemaError as exc:
        raise _NeedLayouts(sorted(set(tables)), exc.message) from exc
    missing = sorted({t for t in tables if t not in layouts})
    if missing and run.options.network:
        # commit épinglé antérieur au build (relevé du 2026-10-06 : épinglé avant la sortie de 70235) : `master` est
        # relu et épinglé de nouveau, puis les dispositions sont rechargées ; jamais celles d'un build voisin
        fetch_dbd(run.deps_on(run.base_data), version, wanted, refresh=True)
        layouts, dbd = load_dbd_layouts(run.deps.cache_dir, version, wanted)
        missing = sorted({t for t in tables if t not in layouts})
    if missing:
        commit = str(dbd.get("commit") or "?")[:12]
        raise _NeedLayouts(missing, f"WoWDBDefs (commit {commit}) sans disposition pour le build {version}")
    journal = hotfixes.load_journal(run.deps.cache_dir)
    from forever.archive import archived_locale

    return hotfix_source(archive, layouts, dbd, journal, version, rules, run.now, locale=archived_locale(archive))


def _copy_data(base: Path, dest: Path) -> None:
    """Copie des données `base` dans `dest` (remplacée), sans les dossiers de version hors du manifeste."""
    from forever.manifest import VERSION_DIR_RE

    if dest.exists():
        shutil.rmtree(dest)
    installed = set(installed_versions(base))

    def ignored(folder: str, names: list[str]) -> set[str]:
        stray = {n for n in names if Path(folder) == base and VERSION_DIR_RE.match(n) and n not in installed}
        return stray | {n for n in names if n == "__pycache__"}  # dossier de version hors du manifeste : non copié

    shutil.copytree(base, dest, ignore=ignored)


def _stage(run: _Run, version: str) -> Path:
    """Copie de préparation des données de base, dans le cache (jamais le clone ni la session)."""
    stage = update_dir(run.deps.cache_dir) / f"stage-{version}"
    if stage.exists():
        shutil.rmtree(stage)
    _copy_data(run.base_data, stage / "data")
    return stage / "data"


def _carry_counts(report: CarryReport) -> dict[str, int]:
    return dict(zip(CARRY_FR, (len(report.kept), len(report.reapplied), len(report.superseded), len(report.lost))))


def _inputs_doc(inputs: Mapping[str, InputsDiff]) -> dict[str, Any]:
    """Entrées des moteurs pour le JSON : les feuilles changées (`changes`) restent hors du rapport, résumées par
    `values` et `summary`."""
    return {
        name: {"identical": d.identical, "items": [{k: v for k, v in i.items() if k != "changes"} for i in d.items]}
        for name, d in inputs.items()
    }


def _plain(value: Any) -> Any:
    return None if value is ABSENT else value


def _copied(base_vdir: Path, after: Path, inputs: Mapping[str, InputsDiff]) -> dict[str, list[Any]]:
    """Lignes des valeurs changées (classe, entité, champ, avant, après) de chaque moteur dont une entrée change."""
    from forever.engine_inputs import _resolve, _strip
    from forever.pipeline.value_diff import copied_lines

    metadata = metadata_keys(base_vdir, after)
    docs: dict[tuple[Path, str], Any] = {}

    def doc(folder: Path, name: str) -> Any:
        if (folder, name) not in docs:
            docs[folder, name] = _strip(_read(folder / name), metadata)
        return docs[folder, name]

    out: dict[str, list[Any]] = {}
    for name, diff in inputs.items():
        if diff.identical:
            continue
        lines: list[Any] = []
        for item in diff.items:
            if item.get("status") != "différent":
                continue
            file, pointer = str(item["file"]), item.get("pointer")
            a, b = doc(base_vdir, file), doc(after, file)
            if pointer:
                a, b = _resolve(a, pointer), _resolve(b, pointer)
            lines += copied_lines(file, a, b, pointer)
        out[name] = lines
    return out


def _summary_doc(lines: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    from forever.pipeline.value_diff import copied_summary, summary_sentence

    out = {}
    for name, found in lines.items():
        counts = copied_summary(found)
        out[name] = {"counts": counts, "sentence": summary_sentence(counts, name) if counts else ""}
    return out


def written_text(written: Mapping[str, Any]) -> str:
    """« 1.60.1.70245 r3 installée seule (fiches PvP : Warrior, …) » : écriture de la veille (décision 295) ;
    « annulée » pour un retour en arrière (`forever update undo`)."""
    if written.get("undo"):
        return f"{written['undo']} annulée : retour à la révision précédente"
    text = f"{written.get('version')} r{written.get('revision')} installée seule"
    return text + (f" ({written['summary']})" if written.get("summary") else "")


SELF_CLEARING_HINT = (
    "lancer le jeu sur ce build, se connecter au royaume puis quitter le jeu : le client écrit DBCache.bin à la "
    "déconnexion (DON14) et le pont lance alors `forever update`"
)
NETWORK_HINT = "rien à faire : le passage suivant de `forever update` retente le téléchargement"


def summary_text(summary: Mapping[str, Any] | None) -> str:
    """Phrases du résumé des valeurs changées, moteur par moteur (« fiches PvP : Warrior, … »)."""
    if not isinstance(summary, Mapping):
        return ""
    return " ; ".join(str(s.get("sentence")) for s in summary.values() if isinstance(s, Mapping) and s.get("sentence"))


def _evaluate(
    run: _Run,
    *,
    step: str,
    kind: str,
    version: str,
    revision: int,
    candidate: Path,
    new_version: bool,
    motif: str,
    gate: str = "lire",
    hotfixes_read: bool = True,
) -> Step:
    """Vérifie la candidate, l'installe dans la copie de préparation, applique la règle, puis écrit (clone et chemin
    git) ou rend une attente. `hotfixes_read` faux (candidate décodée sans correctifs du serveur) : les valeurs
    `correctif_serveur` de la version installée perdues dans la préparation gardent l'attente (décision 207)."""
    from forever.pipeline.install import InstallRefusedError, apply_install, plan_install
    from forever.pipeline.value_diff import capped_lines
    from forever.pipeline.verify import verify_version

    installed = _installed(run.base_data)
    assert installed is not None
    base_vdir = run.base_data / installed
    verify = verify_version(run.deps_on(run.base_data), str(candidate))
    stage = _stage(run, version)
    stage_deps = run.deps_on(stage)
    install_ok, plan = True, None
    observed: list[str] = []  # écarts tranchés par la décision 296 (carte « Mis à jour »)
    decoded = _read(candidate / version / "sources.json")  # relevés en jeu contredits au décodage (décision 297)
    if isinstance(decoded, dict):
        observed += [str(n) for n in decoded.get("observation_notes") or []]
    try:
        plan = plan_install(stage_deps, str(candidate), new_version=new_version)
        settled = _settle_observations(run, stage, candidate, plan, version) if plan["refused"] else None
        if settled is not None:
            candidate, observed, restore = settled
            plan = plan_install(stage_deps, str(candidate), new_version=new_version)
        if plan["refused"]:
            install_ok = False
        else:
            apply_install(stage_deps, str(candidate), motif=motif, new_version=new_version, date=run.now[:10])
            if settled is not None and restore is not None:
                restore()
    except InstallRefusedError:
        install_ok = False
    except InvalidArgumentError as exc:  # rien à installer (révision qui ne change rien)
        return Step(step, "rien", exc.message, {"version": version})
    after = stage / version if install_ok else candidate / version
    if install_ok:
        observed += _record_retired_class_spells(stage, base_vdir, version)
    carry = carry_check(base_vdir, after)
    if install_ok and carry.reapplied:
        carry_apply(base_vdir, after, carry)
    inputs = compare_inputs(base_vdir, after)
    losses = [] if hotfixes_read else hotfix_losses(base_vdir, after)
    verdict = decide(bool(verify["ok"]), carry, inputs, kind, install_ok=install_ok, hotfix_losses=losses)
    lines = _copied(base_vdir, after, inputs)
    summary = _summary_doc(lines)
    fingerprint = candidate_fingerprint(stage if install_ok else candidate)
    pending_id = f"{version}-r{revision}-{content_fingerprint(after)}"
    cancelled = undone(run.deps.cache_dir, pending_id)
    if cancelled is not None:  # décision 295 : un contenu annulé n'est pas réinstallé ; un contenu nouveau, si
        when = str(cancelled.get("undone_at") or "")[:10]
        return Step(
            step, "rien", f"{version} r{revision} : annulée par toi le {when}, pas réinstallée", {"id": pending_id}
        )
    action, reasons = verdict.action, list(verdict.reasons)
    doc = {
        "id": pending_id,
        "kind": kind,
        "version": version,
        "revision": revision,
        "action": action,
        "clauses": dict(verdict.clauses),
        "reasons": reasons,
        "notes": [*observed, *verdict.notes],
        "verify": {"ok": verify["ok"], "errors": verify.get("errors", [])[:20]},
        "carry": _carry_counts(carry),
        "superseded": [{"file": v.file, "pointer": v.pointer, "after": now} for v, now in carry.superseded],
        "lost": [{"file": v.file, "pointer": v.pointer} for v in carry.lost],
        "inputs": _inputs_doc(inputs),
        "values": {name: capped_lines(found) for name, found in lines.items()},
        "summary": summary,
        "hotfixes": {
            "gate": gate,
            "read": hotfixes_read,
            "lost": [
                {"file": c.file, "pointer": c.pointer, "before": _plain(c.before), "after": _plain(c.after)}
                for c in losses[:50]
            ],
            "lost_count": len(losses),
        },
        "replay": {},
        "refused": (plan or {}).get("refused", []) if plan else [],
    }
    run.verdicts.append(doc)
    if action == "écrire":
        changed = any(not d.identical for d in inputs.values())
        if run.options.dry_run:
            if changed:  # simulation : le rejeu qui suivrait l'installation, sur la préparation
                doc["replay"] = _replay_after_install(run, doc, inputs, run.base_data, stage, version)
            return Step(step, "fait", f"{version} r{revision} : écriture simulée (règle tenue)", {"id": pending_id})
        if not run.writable:
            return Step(step, "arrêt", f"{version} r{revision} : règle tenue, mais clone non disponible", {})
        blocked = _blocked_before(run, pending_id)
        if blocked is not None:
            run.pending.append(blocked)
            why = "; ".join(blocked.get("reasons", []))
            return Step(step, "arrêt", f"{version} r{revision} : déjà bloquée sur ce main ({why})", {"id": pending_id})
        before = update_dir(run.deps.cache_dir) / f"before-{version}"  # « avant » du rejeu, que `_publish` remplace
        if changed and run.replay is not None:
            _copy_data(run.base_data, before)
        try:
            written = _publish(
                run, step=step, version=version, revision=revision, stage=stage, plan=plan, verdict=doc, lines=lines
            )
            if written.status == "fait" and changed and run.replay is not None:
                doc["replay"] = _replay_after_install(run, doc, inputs, before, stage, version)
        finally:
            shutil.rmtree(before, ignore_errors=True)
        return written
    entry = {
        **{k: doc[k] for k in ("id", "kind", "version", "revision", "action", "clauses", "reasons")},
        "summary": summary,
        "values": doc["values"],
        "created_at": run.now,
        "staged": str(stage if install_ok else candidate),
        "staged_sha": fingerprint,
        "candidate": str(candidate),
        "base": {
            "origin_main": run.origin_main,
            "version": installed,
            "revision": _revision(run.base_data, installed),
            "client_build": getattr(run.client, "build", None),
        },
        "commands": ["session nécessaire"],
    }
    run.pending.append(entry)
    return Step(step, "arrêt", f"{version} r{revision} : bloqué ({'; '.join(reasons)})", {"id": pending_id})


def _settle_observations(
    run: _Run, stage: Path, candidate: Path, plan: Mapping[str, Any], version: str
) -> tuple[Path, list[str], Callable[[], None] | None] | None:
    """Écarts refusés par la fusion tranchés par la décision 296 (`forever.pipeline.observations`) : les observations
    plus anciennes que la version du client lui cèdent (entrées ajoutées au `confirmed_changes.json` de la copie de
    préparation), celles de la même version gardent la priorité (candidate corrigée sur une copie). Rend (candidate à
    installer, notes, remise en état après l'installation) ; None si un écart reste non tranché (installation
    refusée, intégrité). Nouvelle version : le fichier de la version précédente est remis tel quel après
    l'installation, les entrées vivent dans celui de la nouvelle version."""
    from forever.manifest import write_manifest
    from forever.pipeline.install import CONFIRMED
    from forever.pipeline.observations import keep_observations, resolve

    version_from, version_to = str(plan["version_from"]), str(plan["version_to"])
    base = stage / version_from
    names = {**_entity_names(base), **_entity_names(candidate / version)}
    out = resolve(
        plan["refused"], version_from=version_from, version_to=version_to, candidate_vdir=candidate / version,
        names=names,
    )  # fmt: skip
    if out.unresolved:
        return None
    restore = None
    if out.accepted:
        path = base / CONFIRMED
        original = path.read_bytes()
        doc = json.loads(original.decode("utf-8"))
        doc["changes"] = [*doc.get("changes", []), *out.accepted]
        path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        write_manifest(stage)
        if version_from != version_to:

            def restore() -> None:
                path.write_bytes(original)
                write_manifest(stage)

    if out.kept:
        dest = update_dir(run.deps.cache_dir) / f"candidate-gardee-{version}"
        candidate = keep_observations(candidate, version, base, out.kept, dest)
    for note in out.notes:
        run.say(f"écart tranché (décision 296) : {note}")
    return candidate, list(out.notes), restore


def _record_retired_class_spells(stage: Path, base_vdir: Path, version: str) -> list[str]:
    """Sorts des classes (`classes.json`) que la version installée portait et que le client n'a plus (décision 297) :
    notés dans `confirmed_changes.json` de la version préparée (« retiré par la version ») ; aucune recommandation ne
    les propose plus (exports et fiches lisent `classes.json`). Rend les phrases de la carte « Mis à jour »."""
    from forever.manifest import write_manifest
    from forever.pipeline.install import CONFIRMED

    before = (_read(base_vdir / "classes.json") or {}).get("classes") or {}
    now = (_read(stage / version / "classes.json") or {}).get("classes") or {}
    entries, notes = [], []
    for cls in sorted(set(before) & set(now)):
        old, new = before[cls].get("spells") or {}, now[cls].get("spells") or {}
        for key in sorted(set(old) - set(new)):
            name = str(old[key].get("name") or key)
            why = f"sort {name} ({cls}) retiré par la version {version}"
            notes.append(why)
            entries.append({"kind": "class_spell", "key": key, "class": cls, "change": "removed", "field": None,
                            "old": key, "new": None, "nature": "client", "decision": f"décision 297 : {why}"})  # fmt: skip
    if entries:
        path = stage / version / CONFIRMED
        doc = _read(path)
        if isinstance(doc, dict):
            known = {(e.get("kind"), e.get("key"), e.get("class")) for e in doc.get("changes", [])}
            doc["changes"] = [
                *doc.get("changes", []),
                *(e for e in entries if (e["kind"], e["key"], e["class"]) not in known),
            ]
            path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            write_manifest(stage)
    return notes


def _entity_names(vdir: Path) -> dict[str, str]:
    """Clé → nom des talents et des sorts de `vdir` (vide si illisibles)."""
    names: dict[str, str] = {}
    talents = _read(vdir / "talents.json")
    if isinstance(talents, dict):
        names |= {t["key"]: str(t.get("name") or t["key"]) for tr in talents.get("trees", []) for t in tr["talents"]}
    spells = _read(vdir / "spells.json")
    if isinstance(spells, dict):
        names |= {k: str(v.get("name") or k) for k, v in spells.get("spells", {}).items() if isinstance(v, dict)}
    return names


def _talent_names_of(run: _Run, data_dir: Path) -> dict[str, str]:
    """Clé de talent → nom en jeu, lus dans les données `data_dir` (vide si illisibles)."""
    try:
        from forever.gamedata import build_game_data
        from forever.store import load_version

        gd = build_game_data(load_version(run.deps_on(data_dir)))
    except Exception:  # noqa: BLE001 : les noms ne sont qu'un habillage, la clé reste lisible
        return {}
    return {k: t.name for k, t in gd.talents.items()}


def _replay_after_install(
    run: _Run, doc: dict[str, Any], inputs: Mapping[str, InputsDiff], before: Path, after: Path, version: str
) -> dict[str, Any]:
    """Rejeu ciblé fait **après** l'installation (décision 295) : il ne décide plus rien, il dit ce qui a changé en
    mots de joueur. La fiche de l'installation (`installed/<id>.json`) reçoit les phrases ; un rejeu en échec le
    dit sans rien défaire."""
    from forever.update_installed import advice_changes, update_installed

    try:
        check_replay_sides(before, after)
        replayed = _replay_sides(run, inputs, before, after, version)
        changes = advice_changes(replayed, _talent_names_of(run, after))
        state = "fait" if changes else "aucun changement"
    except SameDataReplayError as exc:
        replayed, changes, state = {"rejoué": False, "raison": exc.message}, [], f"non fait : {exc.message}"
    except Exception as exc:  # noqa: BLE001 : l'installation est faite, un rejeu en échec ne la défait pas
        why = f"{type(exc).__name__}: {exc}"
        replayed, changes, state = {"rejoué": False, "raison": why}, [], f"non fait : {why}"
    if not run.options.dry_run:
        with contextlib.suppress(InvalidArgumentError):
            update_installed(run.deps.cache_dir, str(doc["id"]), changes=changes, replay=state)
    doc["changes"] = changes
    return replayed if isinstance(replayed, dict) else {"rejoué": True, "cas": replayed}


def _step_new_version(run: _Run, target: str | None) -> Step:
    from forever.archive import archived_dbcache
    from forever.pipeline import dbcache, hotfixes
    from forever.pipeline.decode import decode_version

    if not run.wants("jeu"):
        return Step("nouvelle_version", "rien", "non demandé (--only)", {})
    if target is None:
        return Step("nouvelle_version", "rien", "aucune version à installer", {})
    product = run.client.product if run.client is not None else None  # LN1 : archives du produit lu
    archive = archived_dbcache(run.deps.cache_dir, _build_number(target), product=product)
    raidbots: list[str] = []
    archive = dbcache_for_build(run.deps, int(_build_number(target)), product, archive, notes=raidbots)  # décision 290
    for note in raidbots:
        run.say(f"nouvelle_version : {note}")
    seen = _first_seen(run, target)
    gate = hotfix_gate(archive is not None, seen, run.deps.now(), UPDATE_HOTFIX_WAIT)
    if gate == "attendre":
        return _hotfixes_wait(run, target, seen)
    run.cleared[f"hotfixes-{target}"] = (
        "DBCache.bin du build archivé et lu" if gate == "lire" else "délai écoulé sans DBCache.bin du build"
    )
    rules = _rules(run.base_data)
    try:
        absent_names = _fetch_version(run, target, rules)
    except FetchFailedError as err:
        return _network_wait(run, "nouvelle_version", target, err)
    source = None
    if archive is not None:
        pending = hotfixes.pending_hotfixes(dbcache.read_dbcache(archive), {}, rules)
        if pending:
            try:
                source = _hotfix_source(run, target, archive, rules, [t for t, _ in pending])
            except _NeedLayouts as need:
                return _need_layouts(run, "nouvelle_version", target, need, len(pending))
    try:
        candidate = decode_version(run.deps_on(run.base_data), target, force=True, hotfixes=source)
    except ColumnNamesError as err:
        return _column_wait(run, "nouvelle_version", target, err)
    motif = f"nouvelle version {target} (forever update)"
    result = _evaluate(
        run,
        step="nouvelle_version",
        kind="install_version",
        version=target,
        revision=1,
        candidate=candidate.root,
        new_version=True,
        motif=motif,
        gate=gate,
        hotfixes_read=source is not None,
    )
    data = {**result.data, "gate": gate}
    if absent_names:
        data["missing_names"] = absent_names
        result = result._replace(
            detail=f"{result.detail} ; noms manquants ({', '.join(absent_names)}), ajoutés par un passage suivant"
        )
    return result._replace(data=data)


def _first_seen(run: _Run, version: str) -> datetime | None:
    """Première vue du build sur ce poste (journal des versions du client), None si absent ou illisible."""
    from forever.pipeline.client_builds import load_builds

    try:
        found = [b.installed_at for b in load_builds(run.deps.cache_dir) if b.build == version]
    except ForeverError:
        return None
    return min(found) if found else None


def _hotfixes_wait(run: _Run, version: str, seen: datetime | None) -> Step:
    """Attente « correctifs à lire » (décision 207) : aucune archive de `DBCache.bin` du build, délai non écoulé.
    Rien n'est relevé ni décodé ; l'attente n'est pas approuvable et se lève seule."""
    until = format_utc(seen + UPDATE_HOTFIX_WAIT) if seen is not None else None
    pending_id = f"hotfixes-{version}"
    why = (
        f"correctifs du serveur à lire : aucun DBCache.bin du build {_build_number(version)} archivé ; lancer le jeu "
        "sur ce build, se connecter au royaume puis quitter le jeu (le client écrit DBCache.bin à la déconnexion)"
        + (f", sinon installation sans correctifs à partir de {until} si aucun n'est perdu" if until else "")
    )
    run.pending.append(
        {
            "id": pending_id,
            "kind": "hotfixes_unread",
            "action": "attente",
            "version": version,
            "revision": None,
            "clauses": {},
            "reasons": [why],
            "seen_at": format_utc(seen) if seen is not None else None,
            "until": until,
            "created_at": run.now,
            "base": {"origin_main": run.origin_main, "version": _installed(run.base_data)},
            "commands": [SELF_CLEARING_HINT],
        }
    )
    return Step("nouvelle_version", "attente", why, {"id": pending_id, "gate": "attendre", "until": until})


def _names_revision(
    run: _Run, version: str, rules: Mapping[str, Any], archive: Path | None, absent: Sequence[str]
) -> Step:
    """Révision qui ajoute à la version installée les noms d'une autre locale manquants (décision 230) : tables
    retéléchargées ; toutes présentes, la version est redécodée avec tous les correctifs de l'archive (jamais sans :
    les valeurs `correctif_serveur` seraient perdues) et passe par la règle d'automatisme ; les noms affichés ne sont
    pas une entrée des moteurs, la révision s'écrit seule."""
    from forever.pipeline import dbcache, hotfixes
    from forever.pipeline.decode import decode_version

    try:
        still = _fetch_version(run, version, rules)
    except FetchFailedError as err:
        return _network_wait(run, "correctifs", version, err)
    if still:
        detail = f"noms toujours manquants ({', '.join(still)}) : nouvel essai au passage suivant"
        return Step("correctifs", "rien", detail, {"missing_names": still})
    source = None
    if archive is not None:
        every = hotfixes.pending_hotfixes(dbcache.read_dbcache(archive), {}, rules)
        if every:
            try:
                source = _hotfix_source(run, version, archive, rules, [t for t, _ in every])
            except _NeedLayouts as need:
                return _need_layouts(run, "correctifs", version, need, len(every))
    try:
        candidate = decode_version(run.deps_on(run.base_data), version, force=True, hotfixes=source)
    except ColumnNamesError as err:
        return _column_wait(run, "correctifs", version, err)
    return _evaluate(
        run,
        step="correctifs",
        kind="install_revision",
        version=version,
        revision=_revision(run.base_data, version) + 1,
        candidate=candidate.root,
        new_version=False,
        motif=f"noms ajoutés ({', '.join(absent)}) (forever update)",
        hotfixes_read=source is not None,
    )


def seen_quest_gap(cache_dir: Path, data_dir: Path, version: str) -> list[int]:
    """Quêtes du `questcache.wdb` archivé du build de `version` absentes de `quest_rewards.json` installé (ou dont la
    ligne a changé) ; vide sans archive ou si le cache est illisible (T04d, bloc B)."""
    from forever.archive import archived_questcache
    from forever.pipeline.quest_rewards import QUEST_FILE, new_seen_quests
    from forever.pipeline.questcache import read_questcache

    archive = archived_questcache(cache_dir, _build_number(version))
    if archive is None:
        return []
    try:
        cache = read_questcache(archive)
    except DataSchemaError:
        return []
    installed = data_dir / version / QUEST_FILE
    doc = _read(installed) if installed.is_file() else None
    return new_seen_quests(cache, doc if isinstance(doc, dict) else None)


def _quests_revision(
    run: _Run, version: str, rules: Mapping[str, Any], archive: Path | None, gap: Sequence[int]
) -> Step:
    """Révision qui ajoute à `quest_rewards.json` les quêtes nouvellement vues par le client (T04d, bloc B) : la
    version est redécodée avec tous les correctifs de l'archive (jamais sans) et le cache des quêtes archivé, puis
    passe par la règle d'automatisme ; les quêtes vues ne changent aucun build."""
    from forever.pipeline import dbcache, hotfixes
    from forever.pipeline.decode import decode_version

    try:
        _fetch_version(run, version, rules)
    except FetchFailedError as err:
        return _network_wait(run, "correctifs", version, err)
    source = None
    if archive is not None:
        every = hotfixes.pending_hotfixes(dbcache.read_dbcache(archive), {}, rules)
        if every:
            try:
                source = _hotfix_source(run, version, archive, rules, [t for t, _ in every])
            except _NeedLayouts as need:
                return _need_layouts(run, "correctifs", version, need, len(every))
    try:
        candidate = decode_version(run.deps_on(run.base_data), version, force=True, hotfixes=source)
    except ColumnNamesError as err:
        return _column_wait(run, "correctifs", version, err)
    return _evaluate(
        run,
        step="correctifs",
        kind="install_revision",
        version=version,
        revision=_revision(run.base_data, version) + 1,
        candidate=candidate.root,
        new_version=False,
        motif=f"{len(gap)} quête(s) vue(s) par le client (questcache.wdb, forever update)",
        hotfixes_read=source is not None,
    )


def _need_layouts(run: _Run, step: str, version: str, need: _NeedLayouts, count: int) -> Step:
    pending_id = f"dbd-{version}-{len(need.tables)}t"
    run.pending.append(
        {
            "id": pending_id,
            "kind": "network_dbd",
            "action": "attente",
            "version": version,
            "revision": None,
            "clauses": {},
            "reasons": [need.why],
            "tables": need.tables,
            "created_at": run.now,
            "base": {"origin_main": run.origin_main, "version": _installed(run.base_data)},
            "commands": [f"forever fetch --version {version} --dbd", "forever update"],
        }
    )
    return Step(step, "attente", f"{count} correctif(s) en attente de dispositions : {need.why}", {
        "pending": count, "tables": need.tables, "id": pending_id,
    })  # fmt: skip


def _column_wait(run: _Run, step: str, version: str, err: ColumnNamesError) -> Step:
    """Colonne renommée par le client (aucun de ses noms dans l'en-tête) : attente `column_names` à traiter en
    session, avec le nom proposé par la place de la colonne dans le CSV de la version installée (T08d, bloc I)."""
    import csv

    from forever.pipeline.fetch import DEFAULT_LOCALE
    from forever.pipeline.tables import propose_names

    installed = _installed(run.base_data)
    old_csv = run.deps.cache_dir / "wago" / str(installed) / DEFAULT_LOCALE / f"{err.table}.csv"
    proposals: dict[str, str | None] = {}
    old_header: list[str] = []
    if old_csv.is_file():
        try:
            with old_csv.open(encoding="utf-8-sig", newline="") as f:
                old_header = next(csv.reader(f), [])
        except (OSError, UnicodeDecodeError, csv.Error):
            old_header = []
    for names in err.missing:
        proposals[names[0]] = propose_names(old_header, err.header, names) if old_header else None
    tried = " ; ".join(" ou ".join(names) for names in err.missing)
    found = [f"{n} → {p}" for n, p in proposals.items() if p]
    reason = f"{err.table} : aucun des noms {tried} dans le CSV de {version}" + (
        f" ; nom proposé par la place de la colonne dans le CSV de {installed} : {', '.join(found)}" if found else ""
    )
    digest = hashlib.sha256(f"{err.table}|{tried}|{','.join(err.header)}".encode()).hexdigest()[:12]
    pending_id = f"columns-{version}-{digest}"
    run.pending.append(
        {
            "id": pending_id,
            "kind": "column_names",
            "action": "attente",
            "version": version,
            "revision": None,
            "clauses": {},
            "reasons": [reason],
            "table": err.table,
            "missing": [list(names) for names in err.missing],
            "proposed": proposals,
            "header": list(err.header),
            "created_at": run.now,
            "base": {"origin_main": run.origin_main, "version": installed},
            "commands": [
                (
                    "en session, après accord : ajouter le nouveau nom en tête de la liste de la colonne "
                    "(forever/pipeline/tables.py et decode_rules.json), puis `forever update`"
                )
            ],
        }
    )
    return Step(step, "attente", f"colonne renommée par le client : {reason}", {"id": pending_id, "table": err.table})


def _step_hotfixes(run: _Run) -> Step:
    from forever.archive import archived_dbcache
    from forever.pipeline import dbcache, hotfixes
    from forever.pipeline.client_builds import read_build_info
    from forever.pipeline.decode import decode_version
    from forever.store import read_sources

    if not run.wants("correctifs"):
        return Step("correctifs", "rien", "non demandé (--only)", {})
    wow = run.deps.wow_dir
    client = run.client or (read_build_info(wow) if wow is not None and wow.is_dir() else None)
    if client is None:
        return Step("correctifs", "rien", "build du client inconnu", {})
    version = str(client.build)
    if version not in installed_versions(run.base_data):
        return Step("correctifs", "rien", f"version du client {version} non installée", {})
    archive = archived_dbcache(run.deps.cache_dir, _build_number(version), product=client.product)
    raidbots: list[str] = []
    archive = dbcache_for_build(run.deps, int(_build_number(version)), client.product, archive, notes=raidbots)
    for note in raidbots:
        run.say(f"correctifs : {note}")
    rules = _rules(run.base_data)
    sources = read_sources(run.base_data, version) or {}
    absent = [str(n) for n in sources.get("missing_names") or []]
    quest_gap = seen_quest_gap(run.deps.cache_dir, run.base_data, version)
    if archive is None:
        if absent:
            return _names_revision(run, version, rules, None, absent)
        if quest_gap:
            return _quests_revision(run, version, rules, None, quest_gap)
        why = f" ; {raidbots[0]}" if raidbots else ""
        return Step("correctifs", "rien", f"aucune archive de DBCache.bin pour {version}{why}", {"raidbots": raidbots})
    pending = hotfixes.pending_hotfixes(dbcache.read_dbcache(archive), sources, rules)
    if not pending:
        if absent:
            return _names_revision(run, version, rules, archive, absent)
        if quest_gap:
            return _quests_revision(run, version, rules, archive, quest_gap)
        return Step("correctifs", "rien", "aucun correctif du serveur en attente", {"pending": 0})
    try:
        source = _hotfix_source(run, version, archive, rules, [t for t, _ in pending])
    except _NeedLayouts as need:
        return _need_layouts(run, "correctifs", version, need, len(pending))
    try:
        _fetch_version(run, version, rules)
    except FetchFailedError as err:
        return _network_wait(run, "correctifs", version, err)
    try:
        candidate = decode_version(run.deps_on(run.base_data), version, force=True, hotfixes=source)
    except ColumnNamesError as err:
        return _column_wait(run, "correctifs", version, err)
    revision = _revision(run.base_data, version) + 1
    return _evaluate(
        run,
        step="correctifs",
        kind="install_revision",
        version=version,
        revision=revision,
        candidate=candidate.root,
        new_version=False,
        motif=f"{len(pending)} correctif(s) du serveur (forever update)",
    )


def _engine_files() -> set[str]:
    files: set[str] = set()
    for spec in ENGINES.values():
        files |= set(spec.files) | set(spec.pointers)
    return files


class _ProductionReplay:
    """Rejeu ciblé de production (décision 230) : les cas des builds du Mage passent par `forever/replay.py` (cache
    `<cache>/builds/update-<version>-<empreinte>/`, `replay_label`, par code du calcul ; cas répartis sur les cœurs par
    `prefetch`) ; les autres cas (simulation de leveling, fiche PvP) ne sont pas rejoués automatiquement et le disent.
    `listing` (simulation) : les cas sont nommés sans être calculés."""

    def __init__(self, deps: Deps, listing: bool) -> None:
        self.deps, self.listing = deps, listing
        self.log: Progress | None = None

    def prefetch(self, jobs: Sequence[tuple[str, str, Path]]) -> int:
        """Calcule d'un coup (en parallèle) les cas des builds du Mage de `jobs` (moteur, cas, données) absents du
        cache ; rend le nombre de cas demandés."""
        if self.listing:
            return 0
        from forever.replay import replay_cases

        cases = [(case, data_dir) for engine, case, data_dir in jobs if engine == "mage_build"]
        if cases:
            replay_cases(cases, self.deps.cache_dir, log=self.log)
        return len(cases)

    def __call__(self, engine: str, case: str, data_dir: Path) -> Any:
        if self.listing:
            return {"rejoué": False, "raison": "simulation : cas à rejouer, non calculé"}
        if engine != "mage_build":
            return {"rejoué": False, "raison": "cas sans rejeu automatique (builds du Mage seulement)"}
        from forever.replay import replay_cases

        return replay_cases([(case, data_dir)], self.deps.cache_dir, log=self.log)[case, data_dir]["advice"]


def _default_replay(deps: Deps, *, listing: bool = False) -> _ProductionReplay:
    return _ProductionReplay(deps, listing)


def _replay_sides(run: _Run, inputs: Mapping[str, InputsDiff], before: Path, after: Path, version: str) -> Any:
    """Rejeu des cas touchés, « avant » sur `before` et « après » sur `after` (dossiers des données) : seulement les
    cas concernés par ce qui change (`monster_contexts` des deux côtés), calculés d'un coup en parallèle quand le
    rejeu le permet (`prefetch`), durée notée au journal du passage (décision 230)."""
    replay = run.replay
    assert replay is not None
    installed = _installed(before) or version
    scope = monster_contexts(before / installed) | monster_contexts(after / version)
    cases = cases_to_replay(inputs, monster_scope=scope)
    start = time.monotonic()
    prefetch = getattr(replay, "prefetch", None)
    if callable(prefetch):
        if hasattr(replay, "log"):
            replay.log = run.say
        prefetch([(e, c, side) for e, c in cases for side in (before, after)])
    out = targeted_replay(
        inputs, lambda e, c: {"avant": replay(e, c, before), "après": replay(e, c, after)}, monster_scope=scope
    )
    run.say(f"rejeu : {len(cases)} cas comparés en {time.monotonic() - start:.0f} s")
    return out


def _default_measure(deps: Deps, data_dir: Path, logs: Sequence[Path]) -> Mapping[str, Any]:
    """`forever measures refresh --dry-run` sur les données de base : un changement de la table des monstres est
    une entrée des moteurs du Mage (`monsters.json`)."""
    from forever.cli import main

    # Décision 227 : la mesure est écrite dans une copie des données (côté « après » du rejeu), jamais dans les
    # données de base ni dans l'instantané du cache.
    preview = update_dir(deps.cache_dir) / "measures-preview"
    _copy_data(data_dir, preview)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(
            ["measures", "refresh", "--into", str(preview), "--json"], dataclasses.replace(deps, data_dir=data_dir)
        )
    payload = json.loads(out.getvalue() or "{}")
    diff = payload.get("diff") or {}
    npcs = diff.get("npcs") or {}
    monsters = any(npcs.get(k) for k in ("added", "changed", "removed")) or bool(diff.get("hp_by_level"))
    changed = [{"file": "monsters.json", "pointer": "/npcs"}] if code == EXIT_OK and monsters else []
    result: dict[str, Any] = {
        "changed": changed,
        "status": payload.get("status"),
        "logs": [p.name for p in logs],
        "details": diff.get("npcs_detail"),
        "hp_by_level": diff.get("hp_by_level") or {},
    }
    if changed and payload.get("status") == "aperçu":
        result["preview"] = preview
    return result


def _log_start(path: Path) -> datetime | None:
    from forever.pipeline.combatlog import read_log

    try:
        _, events = read_log(path)
        first = next(iter(events), None)
    except ForeverError:
        return None
    return first.time if first is not None else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _written_logs(cache_dir: Path, data_dir: Path, version: str) -> dict[str, set[str]]:
    """Journaux dont la mesure est écrite pour `version`, avec leurs empreintes : instantané de `forever measures
    refresh` (écrit avec les données) et sources des révisions de la version (demande du 2026-10-06 : un journal
    n'est noté comme mesuré qu'après l'écriture de sa mesure)."""
    from forever.pipeline.refresh import read_snapshot

    done: dict[str, set[str]] = {}
    snapshot = read_snapshot(cache_dir) or {}
    if snapshot.get("game_version") == version:
        for name, sha in ((snapshot.get("sources") or {}).get("logs") or {}).items():
            done.setdefault(str(name), set()).add(str(sha))
    revisions = _read(data_dir / version / "revisions.json")
    for rev in (revisions or {}).get("revisions", []) if isinstance(revisions, dict) else []:
        for name, sha in (((rev.get("sources") or {}).get("logs")) or {}).items():
            done.setdefault(str(name), set()).add(str(sha))
    return done


def _step_logs(run: _Run, *, trigger: str | None = None) -> Step:
    """Journaux de combat de la version installée mesurés (décision 230), écrits d'eux-mêmes (décision 295).
    `trigger` (addon relu, ex. « Questie 11.39.0 ») : tous les journaux de la version sont remesurés, déjà mesurés
    compris, car la mesure lit l'addon (corrections de Questie) ; l'identifiant de la mesure porte le déclencheur."""
    from forever.installs import product_of
    from forever.pipeline.client_builds import current_builds, split_by_version
    from forever.pipeline.combatlog import log_files
    from forever.pipeline.live_logs import split_live
    from forever.store import read_sources

    if not run.wants("journaux") and trigger is None:
        return Step("journaux", "rien", "non demandé (--only)", {})
    wow = run.deps.wow_dir
    installed = _installed(run.base_data)
    if wow is None or not (wow / "Logs").is_dir() or installed is None:
        return Step("journaux", "rien", "aucun dossier de journaux", {})
    _close_stale_measures(run, installed)
    builds = current_builds(run.deps.cache_dir, wow)
    # Décision 205 : un journal que le jeu ouvert écrit encore est tenu et reproposé au passage suivant.
    files, writing = split_live(log_files(wow / "Logs"), now=run.deps.now(), running=run.deps.game_running())
    sources = read_sources(run.base_data, installed) or {}
    keep, held, unknown = split_by_version(
        [(p.name, _log_start(p)) for p in files],
        builds,
        installed,
        product=product_of(wow)[0],
        data_product=sources.get("product") if isinstance(sources.get("product"), str) else None,
    )
    done = _written_logs(run.deps.cache_dir, run.base_data, installed)
    shas = {p.name: _sha256(p) for p in files if p.name in keep}
    fresh = [p for p in files if p.name in shas and (trigger or shas[p.name] not in done.get(p.name, set()))]
    keep = [p.name for p in fresh]
    data: dict[str, Any] = {
        "held_back": [h._asdict() for h in held],
        "unknown": unknown,
        "measured": keep,
        "writing": writing,
    }
    if not keep:
        detail = f"aucun nouveau journal ({len(held)} d'une autre version, en attente)"
        if writing:
            detail += f" ; {len(writing)} en cours d'écriture, reproposé(s) au passage suivant"
        return Step("journaux", "rien", detail, data)
    measure = run.measure or _default_measure
    result = measure(run.deps, run.base_data, fresh)
    engine_files = _engine_files()
    touched = [c for c in result.get("changed", []) if c.get("file") in engine_files]
    data["changed"] = list(result.get("changed", []))
    held_note = f" ; {len(writing)} en cours d'écriture, reproposé(s) au passage suivant" if writing else ""
    if not touched:
        return Step(
            "journaux",
            "fait",
            f"{len(keep)} journal(aux) mesuré(s), aucune entrée des moteurs changée{held_note}",
            data,
        )
    lines = [f"{n}:{shas[n]}" for n in sorted(keep)] + ([f"addon:{trigger}"] if trigger else [])
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:12]
    pending_id = f"measures-{installed}-{digest}"
    rebuilt = _measure_builds(run, pending_id, installed, result)
    summary = measure_summary(result.get("details") or {}, result.get("hp_by_level") or {}, rebuilt)
    if undone(run.deps.cache_dir, pending_id) is not None:
        return Step("journaux", "rien", f"mesure {pending_id} annulée par toi : pas réécrite", data)
    entry: dict[str, Any] = {
        "id": pending_id,
        "kind": "measures",
        "action": "écrire",
        "version": installed,
        "revision": None,
        "clauses": {"inputs": False, "advice": _no_advice_change(rebuilt)},
        "reasons": [],
        "notes": [f"mesure des journaux qui change une entrée des moteurs : {touched}", _advice_reason(rebuilt)],
        "summary": summary,
        "logs": keep,
        "log_shas": {n: shas[n] for n in keep},
        "created_at": run.now,
        "base": {"origin_main": run.origin_main, "version": installed},
    }
    _replace_measures(run, installed, pending_id)
    if not result.get("preview"):
        return Step("journaux", "arrêt", f"mesure {pending_id} sans copie des données mesurées : rien à écrire", data)
    written = _write_measure(run, entry, result)
    if held_note:
        written = written._replace(detail=written.detail + held_note)
    return written._replace(data={**data, **written.data})


def _no_advice_change(builds: Mapping[str, Any]) -> bool:
    """Vrai si le rejeu a comparé les cas des builds du Mage et qu'aucun conseil ne change (décision 230) ; les cas de
    la simulation du leveling (`mage_leveling`) n'ont pas de rejeu automatique et ne comptent pas."""
    skipped_build = any(s.get("engine") == "mage_build" for s in builds.get("not_replayed") or [])
    return bool(builds.get("replayed")) and not builds.get("changed") and not skipped_build


def _advice_reason(builds: Mapping[str, Any]) -> str:
    if not builds.get("replayed"):
        return f"rejeu non fait ({builds.get('reason')}) : aucun conseil n'a pu être comparé"
    changed = [f"{c['engine']} {c['case']}" for c in builds.get("changed") or []]
    if changed:
        return f"conseil changé après rejeu : {', '.join(changed)}"
    return "aucun conseil ne change après rejeu"


def _replace_measures(run: _Run, installed: str, pending_id: str) -> None:
    """Attentes de mesure ouvertes de la même version, autres que `pending_id` : remplacées par celle-ci, `périmée`
    (une approbation remplacée ne reste jamais « approuvée », décision 230)."""
    if run.options.dry_run:
        return
    for old in list_pending(run.deps.cache_dir):
        same = old.get("kind") == "measures" and old.get("version") == installed and old.get("id") != pending_id
        if same and old.get("state") in OPEN_STATES:
            _set_state(run.deps.cache_dir, str(old["id"]), "périmée", stale_reason=f"remplacée par {pending_id}")


def _close_stale_measures(run: _Run, installed: str) -> None:
    """Attentes de mesure ouvertes d'une autre version que la version installée : `périmée` (leurs journaux sont
    tenus pour leur version, la table mesurée n'est plus celle de la version installée)."""
    if run.options.dry_run:
        return
    for old in list_pending(run.deps.cache_dir):
        if old.get("kind") == "measures" and old.get("state") in OPEN_STATES and old.get("version") != installed:
            _set_state(run.deps.cache_dir, str(old["id"]), "périmée", stale_reason=f"version installée : {installed}")


def _measure_revision(data: Path, version: str, logs: Mapping[str, str], *, date: str, command: str) -> int:
    """Révision de `version` dans la copie `data` où la mesure est écrite (décision 230) : `sources.json` (révision,
    date) et une entrée de `revisions.json` qui garde les journaux mesurés et leurs empreintes (`_written_logs` les
    reconnaît au passage suivant) ; manifeste réécrit. Rend le numéro de la révision."""
    from forever.manifest import write_manifest

    vdir = data / version
    n = _revision(data, version) + 1
    sources = _read(vdir / "sources.json")
    if isinstance(sources, dict):
        sources.update(revision=n, revised_at=date)
        (vdir / "sources.json").write_bytes((json.dumps(sources, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    history = _read(vdir / "revisions.json")
    if not isinstance(history, dict):
        history = {"schema_version": 1, "version": version, "revisions": []}
    history.setdefault("revisions", []).append(
        {
            "revision": n,
            "date": date,
            "motif": "mesure des journaux de combat (table des monstres, forever update)",
            "command": command,
            "sources": {"logs": dict(logs)},
            "changes": [{"file": "monsters.json", "rule": "measure"}],
        }
    )
    (vdir / "revisions.json").write_bytes((json.dumps(history, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(data)
    return n


def _measure_report(verdict: Mapping[str, Any]) -> str:
    builds = ((verdict.get("summary") or {}).get("measures") or {}).get("builds") or {}
    lines = [
        f"# Mesure des journaux : {verdict['version']} r{verdict['revision']}",
        "",
        summary_text(verdict.get("summary")) + ".",
        "",
        f"Journaux mesurés : {', '.join(verdict.get('logs') or [])}.",
        "",
        (
            f"Rejeu : {builds.get('unchanged', 0)} cas inchangé(s), {len(builds.get('changed') or [])} changé(s) ; "
            f"{_advice_reason(builds)}."
        ),
        "",
        "Règle d'automatisme : tenue (décision 295 : installée d'elle-même, annulable).",
        "",
    ]
    return "\n".join(lines)


def _write_measure(run: _Run, entry: Mapping[str, Any], result: Mapping[str, Any]) -> Step:
    """Écrit la mesure (décision 230) : la copie où elle est écrite (`preview`) devient une révision de la version
    installée, publiée comme une version par le clone (vérification des données, CI, fusion)."""
    version = str(entry["version"])
    revision = _revision(run.base_data, version) + 1
    preview = Path(result["preview"])
    inputs = compare_inputs(run.base_data / version, preview / version)
    doc = {
        **{k: entry[k] for k in ("id", "kind", "version", "logs", "summary")},
        "revision": revision,
        "action": "écrire",
        "clauses": dict(entry["clauses"]),
        "reasons": [],
        "notes": list(entry["notes"]),
        "carry": {},
        "superseded": [],
        "inputs": _inputs_doc(inputs),
        "hotfixes": {"gate": "lire", "read": True, "lost": [], "lost_count": 0},
    }
    run.verdicts.append(doc)
    pending_id = str(entry["id"])
    if run.options.dry_run:
        return Step("journaux", "fait", f"mesure {pending_id} : écriture simulée ({_rule(doc)})", {"id": pending_id})
    if not run.writable:
        return Step("journaux", "arrêt", f"mesure {pending_id} : {_rule(doc)}, mais clone non disponible", {})
    blocked = _blocked_before(run, pending_id)
    if blocked is not None:
        run.pending.append(blocked)
        why = "; ".join(blocked.get("reasons", []))
        return Step("journaux", "arrêt", f"mesure {pending_id} : déjà bloquée sur ce main ({why})", {"id": pending_id})
    command = AUTO_COMMAND if run.options.auto else "forever update"
    _measure_revision(preview, version, entry["log_shas"], date=run.now[:10], command=command)
    return _publish(
        run, step="journaux", version=version, revision=revision, stage=preview, plan=None, verdict=doc,
        report=_measure_report(doc),
    )  # fmt: skip


def _rule(doc: Mapping[str, Any]) -> str:
    return "règle tenue" if doc.get("clauses", {}).get("advice") else "conseil changé, règle tenue (décision 295)"


def _measure_builds(run: _Run, pending_id: str, installed: str, result: Mapping[str, Any]) -> dict[str, Any]:
    """Cas des moteurs qui changeraient après rejeu d'une mesure (décision 227) : « avant » sur les données de base,
    « après » sur la copie où la mesure est écrite (`preview`). Fait une fois par attente : un rejeu déjà fait pour
    la même attente sur la même base est repris (plusieurs minutes par cas du build du Mage)."""
    base = replay_label(run.base_data)
    old = _read(_pending_path(run.deps.cache_dir, pending_id))
    kept = ((old.get("summary") or {}).get("measures") or {}).get("builds") if isinstance(old, dict) else None
    if isinstance(kept, dict) and kept.get("replayed") and kept.get("base") == base:
        return kept
    preview = result.get("preview")
    if preview is None or run.replay is None:
        return {"replayed": False, "base": base, "reason": "aperçu des données mesurées absent : rejeu non fait"}
    after = Path(preview)
    try:
        check_replay_sides(run.base_data, after)
        inputs = compare_inputs(run.base_data / installed, after / installed)
        replayed = _replay_sides(run, inputs, run.base_data, after, installed)
    except SameDataReplayError as exc:
        return {"replayed": False, "base": base, "reason": exc.message}
    except Exception as exc:  # noqa: BLE001 : un rejeu en échec ne doit pas perdre l'attente de mesure
        return {"replayed": False, "base": base, "reason": f"rejeu en échec : {type(exc).__name__}: {exc}"}
    changed: list[dict[str, str]] = []
    after_advice: dict[str, Any] = {}
    skipped: list[dict[str, Any]] = []
    unchanged = 0
    for engine, cases in replayed.items():
        for case, sides in cases.items():
            not_run = next(
                (s for s in (sides["avant"], sides["après"]) if isinstance(s, Mapping) and s.get("rejoué") is False),
                None,
            )
            if not_run is not None:
                skipped.append({"engine": engine, "case": case, "reason": not_run.get("raison")})
            elif sides["avant"] != sides["après"]:
                changed.append({"engine": engine, "case": case})
                after_advice[f"{engine}:{case}"] = _plain(sides["après"])
            else:
                unchanged += 1
    if not changed and not unchanged:  # aucun cas comparé (simulation, moteurs sans rejeu automatique)
        reason = str(skipped[0]["reason"]) if skipped else "aucun cas à rejouer"
        return {"replayed": False, "base": base, "reason": reason, "not_replayed": skipped}
    return {
        "replayed": True,
        "base": base,
        "changed": changed,
        "after": after_advice,  # conseil après de chaque cas changé : approbation reprise (décision 230)
        "unchanged": unchanged,
        "not_replayed": skipped,
    }


def measure_summary(
    details: Mapping[str, Any], hp_by_level: Mapping[str, Any], builds: Mapping[str, Any]
) -> dict[str, Any]:
    """Résumé d'une attente de mesure (décision 227), au format de `summary_text` (phrase par moteur) : PNJ ajoutés,
    changés, retirés et écartés de la courbe (avec la raison), niveaux dont les PV changent, cas des builds qui
    changeraient après rejeu."""
    npcs = {k: list(details.get(k) or []) for k in ("added", "changed", "removed", "excluded")}
    counts = ", ".join(
        f"{len(npcs[key])} {label}"
        for key, label in (("added", "ajouté(s)"), ("changed", "changé(s)"), ("removed", "retiré(s)"))
    )
    fresh = sum(1 for n in npcs["excluded"] if n.get("new"))
    parts = [f"PNJ : {counts}, {fresh} nouvellement écarté(s) ({len(npcs['excluded'])} écarté(s) en tout)"]
    if hp_by_level:
        parts.append(f"PV par niveau : {len(hp_by_level)} niveau(x)")
    if builds.get("replayed"):
        parts.append(f"builds : {len(builds.get('changed') or [])} cas changerai(en)t après rejeu")
    else:
        parts.append(f"builds : non rejoués ({builds.get('reason')})")
    return {
        "measures": {
            "sentence": " ; ".join(parts),
            "npcs": npcs,
            "hp_by_level": dict(hp_by_level),
            "builds": dict(builds),
        }
    }


MEASURE_LIST_MAX = 20  # PNJ nommés par ligne du résumé (au-delà : « … et N autre(s) »)


def _listed(items: Sequence[str]) -> str:
    shown = " ; ".join(items[:MEASURE_LIST_MAX])
    return shown + (f" ; … et {len(items) - MEASURE_LIST_MAX} autre(s)" if len(items) > MEASURE_LIST_MAX else "")


def _levels_text(levels: Mapping[str, Any]) -> str:
    out = []
    for level, value in sorted(levels.items(), key=lambda kv: int(kv[0])):
        if isinstance(value, Mapping):
            out.append(f"niv. {level} : {value.get('before')} → {value.get('after')} PV")
        else:
            out.append(f"niv. {level} : {value} PV")
    return ", ".join(out)


def measure_summary_lines(summary: Mapping[str, Any] | None) -> list[str]:
    """Lignes du résumé d'une attente de mesure pour `forever update status` ; [] sans résumé de mesure."""
    doc = (summary or {}).get("measures") if isinstance(summary, Mapping) else None
    if not isinstance(doc, Mapping):
        return []
    npcs = doc.get("npcs") or {}
    lines = []
    for key, label in (("added", "PNJ ajoutés"), ("changed", "PNJ changés")):
        found = [
            f"{n.get('name')} ({n.get('npc_id')}) {_levels_text(n.get('levels') or {})}" for n in npcs.get(key, [])
        ]
        if found:
            lines.append(f"{label} : {_listed(found)}")
    removed = [f"{n.get('name')} ({n.get('npc_id')})" for n in npcs.get("removed", [])]
    if removed:
        lines.append(f"PNJ retirés : {_listed(removed)}")
    # écartés de la courbe : les nouveaux seulement, avec leur raison (les autres sont déjà dans monsters.json)
    excluded = [
        f"{n.get('name')} ({n.get('npc_id')}) : {n.get('reason')} (nouveau)"
        for n in npcs.get("excluded", [])
        if n.get("new")
    ]
    kept = sum(1 for n in npcs.get("excluded", []) if not n.get("new"))
    if excluded:
        lines.append(f"PNJ écartés : {_listed(excluded)}" + (f" ; {kept} déjà écarté(s), non listé(s)" if kept else ""))
    levels = doc.get("hp_by_level") or {}
    if levels:
        shown = [
            f"niv. {lv} : {v.get('before')} → {v.get('after')}"
            for lv, v in sorted(levels.items(), key=lambda kv: int(kv[0]))
        ]
        lines.append(f"PV par niveau : {_listed(shown)}")
    builds = doc.get("builds") or {}
    if builds.get("replayed"):
        changed = [f"{c['engine']} {c['case']}" for c in builds.get("changed") or []]
        tail = f" ({builds.get('unchanged', 0)} inchangé(s))"
        if changed:
            lines.append(f"builds qui changeraient après rejeu : {', '.join(changed)}{tail}")
        else:
            lines.append(f"builds : aucun ne changerait après rejeu{tail}")
        skipped = [f"{s['engine']} {s['case']} ({s.get('reason')})" for s in builds.get("not_replayed") or []]
        if skipped:
            lines.append(f"non rejoué(s) : {', '.join(skipped)}")
    elif builds:
        lines.append(f"builds : non rejoués ({builds.get('reason')})")
    return lines


def _step_addons(run: _Run) -> Step:
    from forever.addons import addons_status

    if not run.wants("addons"):
        return Step("addons", "rien", "non demandé (--only)", {})
    if run.deps.wow_dir is None or not run.deps.wow_dir.is_dir():
        return Step("addons", "rien", "dossier du client absent", {})
    report = addons_status(run.deps, save=not run.options.dry_run)
    changed = [a for a in report["addons"] if a.get("status") in ("changé", "nouveau")]
    proposals = [u for u in report.get("untracked", []) if u.get("status") == "non_inventorié"]
    remeasured: list[str] = []
    for addon in changed:
        proposal = addon.get("proposal")
        if not proposal or proposal.get("kind") != "addon_data":
            continue
        if addon["name"] in REMEASURED_ADDONS:  # décision 295 : relu d'elle-même par la veille
            trigger = f"{addon['name']} {addon.get('version') or str(addon.get('fingerprint'))[:12]}"
            done = _step_logs(run, trigger=trigger)
            remeasured.append(f"{addon['name']} relu ({done.status} : {done.detail})")
            continue
        run.pending.append(
            {
                "id": f"addon-{addon['name']}-{str(addon.get('fingerprint'))[:12]}",
                "kind": "addon_data",
                "action": "relecture",  # rappel d'une relecture en session : n'attend aucun accord, ne bloque rien
                "addon": addon["name"],
                "version": addon.get("version"),
                "revision": None,
                "clauses": {},
                "reasons": [
                    f"{addon['name']} : aucun inventaire précédent, relecture complète : "
                    f"{', '.join(proposal.get('depends', []))}"
                    if proposal.get("first")
                    else f"{addon['name']} changé : {', '.join(proposal.get('depends', []))}"
                ],
                "files": addon.get("files"),
                "previous_version": addon.get("previous_version"),
                "first": bool(proposal.get("first")),
                "uses": list(proposal.get("uses") or []),
                "created_at": run.now,
                "base": {"origin_main": run.origin_main, "fingerprint": addon.get("fingerprint")},
                "commands": [str(proposal.get("action"))],
            }
        )
    data = {
        "changed": [{"name": a["name"], "status": a["status"], "version": a.get("version")} for a in changed],
        "untracked": proposals,
        "remeasured": remeasured,
    }
    review = sum(1 for p in run.pending if p["kind"] == "addon_data")
    if changed or proposals:
        detail = f"{len(changed)} addon(s) changé(s), {len(proposals)} à inventorier"
        if remeasured:
            detail += " ; " + " ; ".join(remeasured)
        if review:
            detail += f" ; {review} relecture(s) en session signalée(s), rien n'est bloqué"
        return Step("addons", "fait", detail, data)
    return Step("addons", "rien", "aucun addon changé", data)


def _step_guides(run: _Run) -> Step:
    """Clone en cache des guides de Polestar remis sur leur dernier commit (décision 289 ; lecture seule, réseau) :
    seulement s'il existe déjà (créé à la main par `forever route polestar`), jamais en simulation ni hors réseau ; un
    échec garde la copie existante (attente, nouvel essai au passage suivant), sans bloquer le passage."""
    from forever.compare import polestar_clone, polestar_commit
    from forever.pipeline import gitops
    from forever.pipeline.polestar_fetch import update_polestar

    if not run.wants("guides"):
        return Step("guides", "rien", "non demandé (--only)", {})
    clone = polestar_clone(run.deps.cache_dir)
    if not (clone / ".git").is_dir():
        return Step("guides", "rien", "aucun clone de Polestar (le créer une fois : `forever route polestar`)", {})
    before = polestar_commit(clone)
    if run.options.dry_run or not run.options.network or run.deps.offline:
        return Step(
            "guides", "rien", f"Polestar non mis à jour (simulation ou hors réseau), commit {_short(before)}", {}
        )
    runner = run.runner or gitops.subprocess_runner

    def git(args: Sequence[str], cwd: Path | None = None) -> Any:
        return gitops._run(runner, args, cwd or clone, timeout=STEP_GIT_TIMEOUT_S)

    try:
        update_polestar(run.deps.cache_dir, run=git)
    except gitops.GitOpsError as exc:
        detail = (
            f"Polestar injoignable ({exc.message}) : copie du commit {_short(before)} gardée, nouvel essai au "
            "passage suivant"
        )
        return Step("guides", "rien", detail, {"commit": before, "unreachable": True})
    after = polestar_commit(clone)
    moved = "inchangé" if after == before else f"{_short(before)} → {_short(after)}"
    return Step("guides", "fait", f"guides de Polestar à jour : commit {_short(after)} ({moved})", {"commit": after})


def _step_simulators(run: _Run) -> Step:
    """wowsims/forever tenu à jour (décisions 293 et 294) : seulement s'il a déjà été compilé (`forever sims update`),
    jamais en simulation ni hors réseau ; au nouveau commit, recompilation épinglée puis cas de référence rejoués et
    écarts notés (`veille.json`) ; un échec garde le binaire épinglé (attente, nouvel essai au passage suivant)."""
    from forever.pipeline import gitops, wowsims_build
    from forever.sims import wowsims

    if not run.wants("simulateurs"):
        return Step("simulateurs", "rien", "non demandé (--only)", {})
    pin = wowsims_build.pinned(run.deps.cache_dir)
    if pin is None:
        return Step(
            "simulateurs", "rien", "wowsims/forever jamais compilé (le faire une fois : `forever sims update`)", {}
        )
    before = str(pin.get("commit"))
    if run.options.dry_run or not run.options.network or run.deps.offline:
        detail = f"wowsims/forever non mis à jour (simulation ou hors réseau), commit {_short(before)}"
        return Step("simulateurs", "rien", detail, {})
    try:
        new = wowsims_build.update_wowsims(run.deps.cache_dir, runner=run.runner)
    except gitops.GitOpsError as exc:
        detail = (
            f"wowsims/forever injoignable ou non compilé ({exc.message}) : binaire du commit {_short(before)} gardé, "
            "nouvel essai au passage suivant"
        )
        return Step("simulateurs", "rien", detail, {"commit": before, "unreachable": True})
    if new.get("status") != "compilé":
        return Step("simulateurs", "rien", f"wowsims/forever à jour : commit {_short(before)}", {"commit": before})
    report = wowsims.replay_reference(run.deps.cache_dir, _playable_races(run.deps))
    detail = (
        f"wowsims/forever compilé au commit {_short(str(new['commit']))} ; {len(report['cases'])} cas rejoués, "
        f"{len(report['gaps'])} écart(s) au-delà du seuil"
    )
    return Step("simulateurs", "fait", detail, {"commit": new["commit"], "gaps": report["gaps"]})


def _playable_races(deps: Deps) -> dict[str, str]:
    """Une race jouable par classe, lue dans les données de Forever (`races.json`), nom du proto de wowsims."""
    from forever.sims.wowsims import race_enum
    from forever.store import load_version

    races = load_version(deps).read_json("races.json")["races"]
    out: dict[str, str] = {}
    for name in sorted(races):
        for cls in races[name].get("classes", []):
            out.setdefault(str(cls), race_enum(name))
    return out


def _short(commit: str | None) -> str:
    return commit[:12] if commit else "inconnu"


# --- Écriture par le clone et le chemin git ------------------------------------------------------------------


def _annotate_revision(vdir: Path, verdict: Mapping[str, Any], command: str) -> None:
    from forever.manifest import write_manifest

    path = vdir / "revisions.json"
    doc = _read(path)
    if not isinstance(doc, dict) or not doc.get("revisions"):
        return
    last = doc["revisions"][-1]
    last["command"] = command
    last["automated"] = True
    last["rule"] = {"clauses": verdict["clauses"], "carry": verdict["carry"], "inputs": {
        name: all(i["status"] == "identique" for i in d["items"]) for name, d in verdict["inputs"].items()
    }}  # fmt: skip
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(vdir.parent)


def _cell(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _research_report(plan: Any, verdict: Mapping[str, Any], values: Mapping[str, Sequence[Any]] | None = None) -> str:
    from forever.pipeline.install import render_install_report

    lines = [render_install_report(plan).rstrip(), "", "## Report à la main", ""]
    lines += [f"- {k} : {n}" for k, n in verdict["carry"].items()]
    lines += [f"- remplacé : {s['file']} {s['pointer']}" for s in verdict["superseded"]]
    lines += ["", "## Entrées des moteurs", ""]
    for name, d in verdict["inputs"].items():
        state = "identiques" if d["identical"] else "différentes"
        lines.append(f"- {name} : {state}")
    lines += ["", "## Valeurs changées", ""]
    found = [(name, rows) for name, rows in (values or {}).items() if rows]
    if not found:
        lines.append("Aucune valeur changée dans les entrées des moteurs.")
    for name, rows in found:
        sentence = (verdict.get("summary") or {}).get(name, {}).get("sentence") or name
        lines += [f"{sentence}.", "", "| Classe | Entité | Champ | Avant | Après |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {' | '.join(_cell(v) for v in row)} |" for row in rows]
        lines.append("")
    fixes = verdict.get("hotfixes") or {}
    lines += ["", "## Correctifs du serveur", ""]
    if fixes.get("read", True):
        lines.append(f"Porte : {fixes.get('gate', 'lire')} ; correctifs du serveur lus avec la candidate.")
    else:
        lines.append(
            f"Porte : {fixes.get('gate')} ; candidate décodée sans correctifs du serveur, "
            f"{fixes.get('lost_count', 0)} valeur(s) correctif_serveur perdue(s)."
        )
        lines += [f"- {c['file']} {c['pointer']} : {c['before']!r} → {c['after']!r}" for c in fixes.get("lost", [])]
    lines += [
        "",
        f"Règle d'automatisme : {verdict['action']} (décision 295 : installée d'elle-même, annulable).",
        *[f"- {note}" for note in verdict.get("notes") or []],
        "",
    ]
    return "\n".join(lines)


def _publish(
    run: _Run,
    *,
    step: str,
    version: str,
    revision: int,
    stage: Path,
    plan: Any,
    verdict: Mapping[str, Any],
    lines: Mapping[str, Sequence[Any]] | None = None,
    report: str | None = None,
    name: str | None = None,
    message: str | None = None,
) -> Step:
    """Écrit `stage` par le clone : copie, `verify --data`, branche `data/<version>-r<N>` (ou `data/<name>`), CI,
    fusion en avance rapide. `name` et `message` : annulation (`forever update undo`), qui ne touche pas l'historique
    des révisions de la version."""
    from forever.pipeline import gitops

    assert run.clone is not None
    runner = run.runner or gitops.subprocess_runner
    clone = run.clone
    missing = _gh_missing(runner, clone)
    if missing is not None:  # décision 244 : rien n'est copié ni poussé sans pouvoir attendre la CI
        _block(run, pending_id=str(verdict["id"]), version=version, revision=revision, by="gh", reason=missing)
        return Step(step, "arrêt", f"{version} r{revision} : {missing}", {"id": verdict["id"]})
    data = clone / "forever" / "data"
    run.say(f"{step} : copie de {version} r{revision} dans le clone")
    shutil.rmtree(data)
    shutil.copytree(stage, data)
    if name is None:
        _annotate_revision(data / version, verdict, AUTO_COMMAND if run.options.auto else "forever update")
    report_rel = f"docs/research/data-{name or f'{version}-r{revision}'}.md"
    (clone / report_rel).parent.mkdir(parents=True, exist_ok=True)
    text = report if report is not None else _research_report(plan, verdict, lines)
    (clone / report_rel).write_bytes(text.encode("utf-8"))
    _render_inventory(data, clone / INVENTORY_DOC)
    run.say(f"{step} : uv sync dans le clone")
    synced = runner(["uv", "sync", "--frozen", "--offline"], clone, None)
    if synced.returncode != 0:
        gitops.discard_changes(runner, clone)
        log = _save_output(run, f"uv-sync-{version}-r{revision}", ["uv", "sync", "--frozen", "--offline"], synced)
        reason = f"environnement du clone : `uv sync --frozen` en échec dans {clone} (sortie : {log.name})"
        _block(run, pending_id=str(verdict["id"]), version=version, revision=revision, by="uv_sync", reason=reason,
               extra={"log": str(log)})  # fmt: skip
        return Step(step, "arrêt", reason, {"id": verdict["id"], "log": str(log)})
    # Seules les données changent dans le clone : vérification des données (intégrité, origines, registre, chiffres,
    # tests des données et des moteurs aux entrées changées) au lieu de la suite complète ; la CI complète de la
    # branche reste le juge avant la fusion (décision 206).
    engines = sorted(name for name, d in verdict["inputs"].items() if not d["identical"])
    run.say(f"{step} : tasks.py verify --data dans le clone (moteurs : {', '.join(engines) or 'aucun'})")
    command = ["uv", "run", "--frozen", "--offline", "tasks.py", "verify", "--data", f"--engines={','.join(engines)}"]
    checked = runner(command, clone, None)
    if checked.returncode != 0:
        gitops.discard_changes(runner, clone)
        log = _save_output(run, f"verify-{version}-r{revision}", command, checked)
        reason = f"`tasks.py verify` rouge dans le clone : session nécessaire (sortie : {log.name})"
        _block(run, pending_id=str(verdict["id"]), version=version, revision=revision, by="verify", reason=reason,
               extra={"log": str(log)})  # fmt: skip
        return Step(step, "arrêt", f"{version} r{revision} : {reason}", {"id": verdict["id"], "log": str(log)})
    branch = f"data/{name or f'{version}-r{revision}'}"
    motif = str(verdict.get("motif") or "règle tenue")
    message = message or COMMIT_MESSAGE.format(version=version, revision=revision, motif=motif)
    run.say(f"{step} : verify vert ; commit et poussée de {branch}")
    if gitops.drop_stale_branch(runner, clone, branch):
        run.say(f"{step} : branche {branch} d'un essai abandonné retirée")
    sha = gitops.commit_branch(runner, clone, branch, ["forever/data", report_rel, INVENTORY_DOC], message)
    gitops.push(runner, clone, branch)
    run.say(f"{step} : CI attendue sur {branch} ({sha[:12]}, jusqu'à {UPDATE_CI_TIMEOUT.total_seconds() / 60:.0f} min)")
    ci = gitops.wait_ci(runner, clone, branch, sha, UPDATE_CI_TIMEOUT.total_seconds())
    info = {
        "version": version,
        "revision": revision,
        "branch": branch,
        "sha": sha,
        "ci": ci.url,
        "jobs": ci.jobs,
        "summary": summary_text(verdict.get("summary")),
    }
    if not ci.ok:
        gitops.leave_branch(runner, clone, branch)  # clone remis sur main ; branche distante gardée pour l'examen
        reason = f"CI {ci.status} sur {branch} ({ci.url}) : rien fusionné, branche gardée à distance"
        _block(run, pending_id=str(verdict["id"]), version=version, revision=revision, by="ci", reason=reason,
               extra={"ci": ci.url, "jobs": ci.jobs})  # fmt: skip
        return Step(step, "arrêt", reason, info)
    run.say(f"{step} : CI verte ; fusion de {branch} dans main en avance rapide")
    merged = gitops.merge_ff_and_push(runner, clone, branch)
    if not merged.ok:
        return Step(step, "arrêt", f"main distant a bougé : relancer `forever update` (branche {branch} poussée)", info)
    gitops.delete_branch(runner, clone, branch)
    run.written.append(info)
    _close_installed(run.deps.cache_dir, version, revision, str(verdict["id"]), run.now)
    if verdict.get("kind") != "undo":
        _record_installed(run, verdict, info, base=run.origin_main)
    run.origin_main = sha  # avance rapide : main distant est maintenant ce commit
    return Step(
        step, "fait", f"{version} r{revision} installée par le clone ({sha[:12]}) : `git pull` dans la session", info
    )


def _record_installed(run: _Run, verdict: Mapping[str, Any], info: Mapping[str, Any], *, base: str | None) -> None:
    """Fiche de l'historique des installations (décision 295) : écrite à la fusion, avant le rejeu (un arrêt pendant
    le rejeu laisse la fiche et sa carte) ; `changes` arrive après le rejeu."""
    measures = (verdict.get("summary") or {}).get("measures") if verdict.get("kind") == "measures" else None
    save_installed(
        run.deps.cache_dir,
        {
            "id": verdict["id"],
            "kind": verdict.get("kind"),
            "version": info["version"],
            "revision": info["revision"],
            "installed_at": run.now,
            "sha": info["sha"],
            "base": base,
            "branch": info["branch"],
            "ci": info.get("ci"),
            "summary": summary_text(verdict.get("summary")),
            "measures": measure_summary_lines(verdict.get("summary")) if measures else [],
            "notes": list(verdict.get("notes") or []),
            "changes": [],
            "replay": "en cours" if any(not d["identical"] for d in verdict["inputs"].values()) else "sans objet",
            "state": "installée",
            "by": AUTO_COMMAND if run.options.auto else "forever update",
            "undo": f"forever update undo {verdict['id']}",
        },
    )


GH_MISSING = (
    "GitHub CLI (gh) introuvable sur ce PC : rien n'a été poussé ; installer GitHub CLI "
    "(winget install --id GitHub.cli), puis `gh auth login`"
)


def _gh_missing(runner: Runner, clone: Path) -> str | None:
    """Raison d'arrêt si GitHub CLI manque (la CI de la branche ne pourrait pas être attendue), sinon None."""
    try:
        done = runner(["gh", "--version"], clone, 30)
    except OSError:
        return GH_MISSING
    return None if done.returncode == 0 else GH_MISSING


def _close_installed(cache_dir: Path, version: str, revision: int, written_id: str, at: str) -> None:
    """Attentes closes par une écriture (sa version est installée) : celle qui vient d'être écrite (approuvée ou non) et
    l'attente « correctifs à lire » de la version passent à `faite` ; une autre attente d'installation de la même
    version jusqu'à cette révision, dont le contenu n'a pas été écrit, passe à `périmée`."""
    done = f"{version} r{revision} installée"
    for entry in list_pending(cache_dir):
        if entry.get("state") not in OPEN_STATES:
            continue
        rev = entry.get("revision")
        same_version = entry.get("version") == version and (rev is None or (isinstance(rev, int) and rev <= revision))
        if entry.get("id") == written_id or (same_version and entry.get("kind") in SELF_CLEARING_KINDS):
            _set_state(cache_dir, str(entry["id"]), "faite", done_at=at, done_by=done)
        elif same_version and entry.get("kind") in INSTALL_KINDS:
            _set_state(cache_dir, str(entry["id"]), "périmée", stale_reason=f"remplacée : {done}")


def _render_inventory(data: Path, doc: Path) -> None:
    """Inventaire committé des valeurs écrites à la main, rendu pour la version courante après l'installation
    (fichier dérivé : `test_origins_inventory` le compare au rendu de la commande, décision 192)."""
    from forever.origins import inventory, render_inventory

    version = _installed(data)
    if version is None:
        return
    rows, pending = inventory(data, version)
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(render_inventory(version, rows, pending).encode("utf-8"))


def _save_output(run: _Run, name: str, command: Sequence[str], out: Any) -> Path:
    """Sortie complète d'une commande du clone en échec, gardée dans `<cache>/update/<name>-<horodatage>.log`."""
    stamp = "".join(c for c in run.now if c.isalnum())
    path = update_dir(run.deps.cache_dir) / f"{name}-{stamp}.log"
    lines = [
        f"$ {' '.join(command)}",
        f"code de sortie : {out.returncode}",
        "",
        "--- sortie standard ---",
        out.stdout or "",
        "--- sortie d'erreur ---",
        out.stderr or "",
    ]
    text = "\n".join(lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _block(
    run: _Run,
    *,
    pending_id: str,
    version: str,
    revision: int,
    by: str,
    reason: str,
    origin_main: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """Attente bloquée d'une écriture arrêtée en route (`by` : uv_sync, verify ou ci) : jamais approuvable, une
    session est nécessaire ; visible dans `forever update status` et la ligne de démarrage, code de sortie 6."""
    run.pending.append(
        {
            "id": pending_id,
            "kind": "install_version" if revision == 1 else "install_revision",
            "version": version,
            "revision": revision,
            "action": "bloqué",
            "blocked_by": by,
            "clauses": {},
            "reasons": [reason],
            "created_at": run.now,
            "base": {"origin_main": origin_main or run.origin_main, "version": _installed(run.base_data)},
            "commands": ["session nécessaire : lire la sortie gardée, corriger sur main, puis `forever update`"],
            **(extra or {}),
        }
    )


def _blocked_before(run: _Run, pending_id: str) -> dict[str, Any] | None:
    """Attente bloquée de la même écriture (même contenu) sur le même `origin/main` : la refaire rejouerait le même
    échec (13 min de `verify`, ou la même CI) ; un nouvel essai attend que main bouge."""
    found = [p for p in run.pending if p.get("id") == pending_id]
    doc = found[-1] if found else _read(_pending_path(run.deps.cache_dir, pending_id))
    if not isinstance(doc, dict) or doc.get("action") != "bloqué" or doc.get("blocked_by") not in BLOCKED_BY:
        return None
    if doc.get("state", "en_attente") != "en_attente":
        return None
    if (doc.get("base") or {}).get("origin_main") != run.origin_main:
        return None
    if found:
        run.pending.remove(doc)
    return {k: v for k, v in doc.items() if k != "state"}


# --- Passage --------------------------------------------------------------------------------------------------


def _guard(name: str, fn: Callable[[], Step]) -> Step:
    try:
        return fn()
    except ForeverError as exc:
        return Step(name, "erreur", f"{exc.code} : {exc.message}", {"code": exc.code, "action": exc.action})
    except OSError as exc:
        return Step(name, "erreur", f"{type(exc).__name__} : {exc}", {})


def close_pass_errors(cache_dir: Path, at: str) -> None:
    """Attentes « erreur » levées par un passage réussi."""
    for entry in list_pending(cache_dir):
        if entry.get("kind") == PASS_ERROR_KIND and entry.get("state") in OPEN_STATES:
            _set_state(cache_dir, str(entry["id"]), "faite", done_at=at, done_by="passage suivant réussi")


def _record_pass_error(cache_dir: Path, started: str, at: str, reasons: list[str], commands: list[str]) -> None:
    for entry in list_pending(cache_dir):
        if entry.get("kind") == PASS_ERROR_KIND and entry.get("state") in OPEN_STATES:
            _set_state(cache_dir, str(entry["id"]), "périmée", stale_reason="remplacée par un passage plus récent")
    record_pending(
        cache_dir,
        {
            "id": "pass-error-" + "".join(c for c in started if c.isdigit()),
            "kind": PASS_ERROR_KIND,
            "action": "bloqué",
            "version": None,
            "revision": None,
            "clauses": {},
            "reasons": reasons,
            "commands": commands or ["forever update status", "forever update --auto"],
            "created_at": at,
        },
    )


def run_update(
    deps: Deps,
    options: UpdateOptions,
    *,
    runner: Runner | None = None,
    replay: Replay | None = None,
    measure: Measure | None = None,
    progress: Progress | None = None,
    max_seconds: float | None = None,
    on_timeout: Callable[[int], None] | None = None,
) -> UpdateReport:
    """Un passage complet (étapes `STEPS`) ; `dry_run` : tout est calculé, seul l'archivage écrit (et la préparation
    dans le cache), les attentes sont rendues sans être enregistrées. `progress` reçoit le journal au fil de l'eau
    (début et fin de chaque étape) ; le verrou garde aussi l'étape en cours et les étapes finies."""
    from forever.provenance import local_provenance

    started = format_utc(deps.now())
    command = AUTO_COMMAND if options.auto else "forever update"
    run = _Run(deps, options, runner, replay or _default_replay(deps, listing=options.dry_run), measure, deps.data_dir)
    run.progress = progress
    lock = acquire_lock(deps, command)
    steps: list[Step] = []

    def done(step: Step) -> None:
        steps.append(step)
        run.say(f"{step.name} : {step.status} · {step.detail}")

    current: dict[str, Any] = {"step": "verrou", "at": time.monotonic()}
    expired = threading.Event()
    stop = threading.Event()

    def advance(name: str, fn: Callable[[], Step]) -> None:
        current.update(step=name, at=time.monotonic())
        _note_step(deps.cache_dir, name, steps, run.now)
        run.say(f"{name} : en cours")
        done(_guard(name, fn))

    def watch() -> None:
        """Délai maximal de l'étape en cours : au-delà, attente « erreur », verrou rendu, arrêt du passage."""
        interval = 0.05 if max_seconds is not None and max_seconds < 5 else 5.0
        while not stop.wait(interval):
            limit = max_seconds if max_seconds is not None else STEP_LIMITS_S.get(str(current["step"]))
            elapsed = time.monotonic() - float(current["at"])
            if limit is None or elapsed <= limit:
                continue
            expired.set()
            reason = (
                f"passage arrêté au bout de {round(elapsed / 60)} min, à l'étape {current['step']} (délai maximal "
                f"de l'étape : {round(limit / 60)} min) : bloqué ou trop long ; journal du passage dans "
                f"{update_dir(deps.cache_dir)}"
            )
            run.say(f"arrêt : {reason}")
            _record_pass_error(deps.cache_dir, started, run.now, [reason], [])
            release_lock(deps.cache_dir)
            (on_timeout or os._exit)(PASS_TIMEOUT_EXIT)
            return

    if lock is not None and lock.status == "arrêt":
        done(lock)
    else:
        done(lock or Step("verrou", "fait", "verrou pris", {"stale": False}))
        if not options.dry_run:
            close_legacy_waits(deps.cache_dir, run.now)
        watchdog = threading.Thread(target=watch, daemon=True)
        watchdog.start()
        try:
            advance("archivage", lambda: _step_archive(run))
            advance("clone", lambda: _step_clone(run))
            target: list[str | None] = [None]

            def game() -> Step:
                found, target[0] = _step_game(run)
                return found

            advance("jeu", game)
            advance("nouvelle_version", lambda: _step_new_version(run, target[0]))
            advance("correctifs", lambda: _step_hotfixes(run))
            advance("journaux", lambda: _step_logs(run))
            advance("addons", lambda: _step_addons(run))
            advance("guides", lambda: _step_guides(run))
            advance("simulateurs", lambda: _step_simulators(run))
            done(_end_step(run))
        finally:
            stop.set()
            if not expired.is_set():
                release_lock(deps.cache_dir)
    report: UpdateReport = {
        "schema_version": SCHEMA_VERSION,
        "started_at": started,
        "finished_at": format_utc(deps.now()),
        "steps": [s._asdict() for s in steps],
        "verdicts": run.verdicts,
        "written": run.written,
        "pending": run.pending,
        "origin_main": run.origin_main,
        "provenance": dict(local_provenance(deps, certainty="probable", assumptions=_assumptions(run))),
    }
    if expired.is_set():
        return report  # arrêté par son délai : l'attente « erreur » est écrite, rien d'autre
    if not options.dry_run and len(steps) > 1:
        errors = [s for s in steps if s.status == "erreur"]
        if errors:
            reasons = [f"étape {s.name} : {s.detail}" for s in errors]
            commands = [str(s.data["action"]) for s in errors if isinstance(s.data, dict) and s.data.get("action")]
            _record_pass_error(deps.cache_dir, started, run.now, reasons, commands)
        else:
            close_pass_errors(deps.cache_dir, run.now)
        for entry in run.pending:
            record_pending(deps.cache_dir, entry)
        for pending_id, why in run.cleared.items():
            doc = _read(_pending_path(deps.cache_dir, pending_id))
            if isinstance(doc, dict) and doc.get("state") in OPEN_STATES:
                _set_state(deps.cache_dir, pending_id, "faite", done_at=run.now, done_by=why)
        _close_stale_hotfix_waits(run)
        save_report(deps.cache_dir, report)
    return report


def close_legacy_waits(cache_dir: Path, at: str) -> list[str]:
    """Attentes d'accord d'avant la décision 295 (installation ou mesure d'action `attente`) : `périmée`, car la
    veille installe désormais d'elle-même ; le passage recalcule et écrit ce qu'elles proposaient. Rend leurs
    identifiants."""
    closed = []
    for entry in list_pending(cache_dir):
        legacy = entry.get("kind") in (*INSTALL_KINDS, "measures") and entry.get("action") == "attente"
        if legacy and entry.get("state") in OPEN_STATES:
            _set_state(cache_dir, str(entry["id"]), "périmée", stale_reason=LEGACY_REASON, closed_at=at)
            closed.append(str(entry["id"]))
    return closed


def _close_stale_hotfix_waits(run: _Run) -> None:
    """Attentes « correctifs à lire » sans objet : version installée par ailleurs (`faite`), ou client passé à un
    autre build (`périmée`, le build attendu ne se lance plus)."""
    installed = set(installed_versions(run.base_data))
    client = str(run.client.build) if run.client is not None else None
    for entry in list_pending(run.deps.cache_dir):
        if entry.get("kind") != "hotfixes_unread" or entry.get("state") not in OPEN_STATES:
            continue  # attente « réseau » : levée par le téléchargement réussi (`run.cleared`), jamais ici
        version = entry.get("version")
        if version in installed:
            _set_state(run.deps.cache_dir, str(entry["id"]), "faite", done_at=run.now, done_by=f"{version} installée")
        elif client is not None and version != client:
            _set_state(run.deps.cache_dir, str(entry["id"]), "périmée", stale_reason=f"client passé à {client}")


def _assumptions(run: _Run) -> list[str]:
    notes = ["passage de forever update : enchaînement d'outils, aucun calcul de combat"]
    if run.options.dry_run:
        notes.append("simulation : rien n'est écrit dans le clone, les attentes ne sont pas enregistrées")
    return notes


def _end_step(run: _Run) -> Step:
    parts = [f"{len(run.written)} écriture(s)", f"{len(run.pending)} attente(s)"]
    data = {"written": len(run.written), "pending": [p["id"] for p in run.pending], "origin_main": run.origin_main}
    return Step("fin", "fait", ", ".join(parts), data)


def exit_code(report: Mapping[str, Any]) -> int:
    """`EXIT_PENDING` si le passage laisse au moins une attente, `EXIT_OK` sinon."""
    return EXIT_PENDING if report.get("pending") else EXIT_OK


def save_report(cache_dir: Path, report: Mapping[str, Any]) -> Path:
    """Écrit le rapport d'un passage (`last.json`, `report-<horodatage>.json`, historique des 30 derniers) ; la base
    des approbations (`origin_main`) est lue dans `last.json`."""
    folder = update_dir(cache_dir)
    stamp = "".join(c for c in str(report.get("started_at", "")) if c.isalnum()) or "inconnu"
    _write(folder / f"report-{stamp}.json", report)
    _write(folder / "last.json", report)
    history = _read(folder / "history.json")
    entries = history if isinstance(history, list) else []
    entries.append(
        {
            "started_at": report.get("started_at"),
            "finished_at": report.get("finished_at"),
            "origin_main": report.get("origin_main"),
            "verdicts": [(v.get("id"), v.get("action")) for v in report.get("verdicts", [])],
            "pending": len(report.get("pending", [])),
            "written": len(report.get("written", [])),
        }
    )
    _write(folder / "history.json", entries[-HISTORY_KEPT:])
    return folder / "last.json"


def candidate_fingerprint(root: Path) -> str:
    """Empreinte courte (12 caractères) de tous les fichiers d'une candidate ou d'une préparation : une candidate
    réécrite change d'empreinte, et son attente devient périmée."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()[:12]


def content_fingerprint(version_dir: Path) -> str:
    """Empreinte courte du **contenu** d'une version (JSON triés, sans métadonnées ni fichiers de provenance) : elle
    nomme une attente et reste la même d'un passage à l'autre si le client ne change rien (les dates de lecture et
    de révision n'y entrent pas), pour qu'une approbation soit consommée par le passage suivant."""
    from forever.engine_inputs import PROVENANCE_FILES, canonical_sha, metadata_keys

    metadata = metadata_keys(version_dir)
    digest = hashlib.sha256()
    for path in sorted(version_dir.glob("*.json")):
        if path.name in PROVENANCE_FILES:
            continue
        digest.update(path.name.encode("utf-8") + b"\0" + canonical_sha(_read(path), None, metadata).encode("ascii"))
    return digest.hexdigest()[:12]


# --- Attentes -------------------------------------------------------------------------------------------------


def record_pending(cache_dir: Path, entry: Mapping[str, Any]) -> Path:
    """Enregistre une attente (`<cache>/update/pending/<id>.json`) ; une entrée déjà approuvée ou faite est gardée."""
    path = _pending_path(cache_dir, str(entry["id"]))
    old = _read(path)
    if isinstance(old, dict) and old.get("state") in KEPT_STATES:
        return path
    _write(path, {**entry, "state": "en_attente"})
    return path


def list_pending(cache_dir: Path) -> list[dict[str, Any]]:
    """Attentes enregistrées, de la plus ancienne à la plus récente."""
    folder = update_dir(cache_dir) / "pending"
    docs = [d for p in sorted(folder.glob("*.json")) if isinstance(d := _read(p), dict)] if folder.is_dir() else []
    return sorted(docs, key=lambda d: (str(d.get("created_at") or ""), str(d.get("id"))))


def _load(cache_dir: Path, pending_id: str) -> dict[str, Any]:
    doc = _read(_pending_path(cache_dir, pending_id))
    if not isinstance(doc, dict):
        raise PendingNotFoundError(pending_id)
    return doc


def _set_state(cache_dir: Path, pending_id: str, state: str, **extra: Any) -> dict[str, Any]:
    doc = {**_load(cache_dir, pending_id), "state": state, **extra}
    _write(_pending_path(cache_dir, pending_id), doc)
    return doc


def _base_moved(cache_dir: Path, entry: Mapping[str, Any]) -> str | None:
    last = _read(update_dir(cache_dir) / "last.json")
    origin = last.get("origin_main") if isinstance(last, dict) else None
    base = entry.get("base") or {}
    if base.get("origin_main") != origin:
        return f"main distant a bougé ({str(base.get('origin_main'))[:12]} → {str(origin)[:12]})"
    staged = entry.get("staged")
    if staged:
        path = Path(str(staged))
        if not path.is_dir() or candidate_fingerprint(path) != entry.get("staged_sha"):
            return "préparation réécrite ou absente depuis l'attente"
    return None


def approve(
    deps: Deps,
    pending_id: str,
    *,
    wait: bool = False,
    runner: Runner | None = None,
    spawn: Spawn | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Approuve une attente si sa base n'a pas bougé (sinon `périmée`) et lance un passage (détaché, ou dans ce
    processus avec `wait`) ; une entrée `bloqué` n'est pas approuvable (refus, code 2)."""
    entry = _load(deps.cache_dir, pending_id)
    if entry.get("kind") in SELF_CLEARING_KINDS:
        raise InvalidArgumentError(
            f"L'attente {pending_id} ({entry.get('kind')}) se lève seule : elle n'est pas approuvable.",
            NETWORK_HINT if entry.get("kind") == "network" else SELF_CLEARING_HINT,
        )
    if entry.get("kind") in SESSION_KINDS:
        raise InvalidArgumentError(
            f"L'attente {pending_id} ({entry.get('kind')}) se traite en session : {'; '.join(entry.get('reasons', []))}.",
            "; ".join(entry.get("commands", [])) or "traiter le cas en session",
        )
    if entry.get("action") == "bloqué":
        raise InvalidArgumentError(
            f"L'attente {pending_id} est bloquée ({'; '.join(entry.get('reasons', []))}) : elle n'est pas approuvable.",
            "traiter le cas en session (verify rouge, installation refusée ou valeur perdue)",
        )
    if entry.get("state") not in OPEN_STATES:
        raise InvalidArgumentError(
            f"L'attente {pending_id} est {entry.get('state')} : elle n'est plus approuvable.",
            "relancer `forever update` : le passage recalcule les attentes",
        )
    moved = _base_moved(deps.cache_dir, entry)
    if moved is not None:
        doc = _set_state(deps.cache_dir, pending_id, "périmée", stale_reason=moved)
        return {"id": pending_id, "state": doc["state"], "detail": f"{moved} : relancer `forever update`"}
    _set_state(deps.cache_dir, pending_id, "approuvée", approved_at=format_utc(deps.now()))
    if wait:
        report = run_update(deps, UpdateOptions(auto=True), runner=runner, progress=progress)
        return {"id": pending_id, "state": _load(deps.cache_dir, pending_id)["state"], "detail": "passage fait",
                "report": report}  # fmt: skip
    from forever.spawn import spawn_detached, update_command

    log = run_log_path(deps.cache_dir, deps.now())
    launch = spawn or (lambda args: spawn_detached(args, log))
    try:
        launch(update_command())
    except OSError as exc:
        detail = f"approuvée, mais passage non lancé ({exc}) : lancer `forever update --auto`"
    else:
        detail = "approuvée : passage lancé en arrière-plan (`forever update status` pour suivre)"
    return {"id": pending_id, "state": "approuvée", "detail": detail}


UNDO_STEP = "annuler"


def undo(
    deps: Deps, record_id: str, *, runner: Runner | None = None, progress: Progress | None = None
) -> dict[str, Any]:
    """« Annuler » (décision 295) : revient à la révision précédente par le même chemin qu'une installation (clone,
    `git revert` du commit de l'installation, `verify --data`, branche `data/undo-<id>`, CI, fusion en avance
    rapide), sans jeu ouvert. La fiche passe à `annulée` : la veille ne réinstalle pas ce contenu, un contenu nouveau
    s'installe normalement. Une installation plus récente qui touche les mêmes fichiers empêche l'annulation (le
    dire : annuler d'abord la plus récente)."""
    from forever.pipeline import gitops
    from forever.update_installed import load_installed, update_installed

    record = load_installed(deps.cache_dir, record_id)
    if record.get("state") == "annulée":
        raise InvalidArgumentError(f"L'installation {record_id} est déjà annulée.", "rien à faire")
    command = f"forever update undo {record_id}"
    run = _Run(deps, UpdateOptions(), runner, None, None, deps.data_dir)
    run.progress = progress
    lock = acquire_lock(deps, command)
    if lock is not None and lock.status == "arrêt":
        return {"id": record_id, "state": record.get("state"), "status": "arrêt", "detail": lock.detail}
    try:
        cloned = _step_clone(run)
        if not run.writable or run.clone is None:
            return {"id": record_id, "state": record.get("state"), "status": "arrêt", "detail": cloned.detail}
        git = run.runner or gitops.subprocess_runner
        clone, sha = run.clone, str(record.get("sha"))
        if not gitops.is_ancestor(git, clone, sha, "HEAD"):
            detail = f"le commit {sha[:12]} n'est pas dans main : rien à annuler"
            return {"id": record_id, "state": record.get("state"), "status": "arrêt", "detail": detail}
        reverted = git(["git", "revert", "--no-commit", sha], clone, STEP_GIT_TIMEOUT_S)
        stage = update_dir(deps.cache_dir) / "undo-stage"
        try:
            if reverted.returncode == 0:
                _copy_data(clone / "forever" / "data", stage)
        finally:
            git(["git", "revert", "--abort"], clone, STEP_GIT_TIMEOUT_S)
            gitops.discard_changes(git, clone)
        if reverted.returncode != 0:
            detail = (
                "une installation plus récente touche les mêmes fichiers : annuler d'abord la plus récente "
                "(`forever update status`)"
            )
            return {"id": record_id, "state": record.get("state"), "status": "arrêt", "detail": detail}
        current, previous = _installed(run.base_data), _installed(stage)
        if current is None or previous is None:
            raise InvalidArgumentError("Version installée illisible dans le clone.", "relancer `forever update`")
        inputs = compare_inputs(run.base_data / current, stage / previous)
        name = f"undo-{record_id}"
        back = _revision(stage, previous)
        verdict: dict[str, Any] = {
            "id": name,
            "kind": "undo",
            "version": previous,
            "revision": back,
            "inputs": _inputs_doc(inputs),
            "summary": {},
            "notes": [],
        }
        text = (
            f"# Annulation de {record_id}\n\nDemandée par le joueur (« Annuler », décision 295) : `git revert` de "
            f"{sha[:12]}, retour à {previous} r{verdict['revision']}.\n"
        )
        message = f"Veille : annulation de {record_id} (retour à {previous} r{verdict['revision']}, décision 295)"
        step = _publish(
            run, step=UNDO_STEP, version=previous, revision=back, stage=stage, plan=None,
            verdict=verdict, report=text, name=name, message=message,
        )  # fmt: skip
        shutil.rmtree(stage, ignore_errors=True)
        if step.status != "fait":
            return {"id": record_id, "state": record.get("state"), "status": step.status, "detail": step.detail}
        doc = update_installed(
            deps.cache_dir, record_id, state="annulée", undone_at=run.now, undo_sha=step.data.get("sha")
        )
        report: UpdateReport = {
            "schema_version": SCHEMA_VERSION,
            "started_at": run.now,
            "finished_at": run.now,
            "steps": [cloned._asdict(), step._asdict()],
            "verdicts": [],
            "written": [{**step.data, "undo": record_id}],
            "pending": [],
            "origin_main": run.origin_main,
            "provenance": {},
        }
        save_report(deps.cache_dir, {**report, "kind": "undo"})
        detail = f"annulée : retour à {previous} r{verdict['revision']} (`git pull` dans la session)"
        return {"id": record_id, "state": doc["state"], "status": "fait", "detail": detail}
    finally:
        release_lock(deps.cache_dir)


REVIEW_KINDS = ("addon_data", "column_names")  # relectures faites en session, closes par `forever update done`


def mark_done(cache_dir: Path, pending_id: str, note: str, at: str) -> dict[str, Any]:
    """Clôt une relecture faite en session (décision 244) : `faite`, avec sa note ; refusé pour une autre attente
    (installation, mesure : Valider, Refuser ou le passage suivant les closent)."""
    entry = _load(cache_dir, pending_id)
    if entry.get("kind") not in REVIEW_KINDS:
        raise InvalidArgumentError(
            f"L'attente {pending_id} ({entry.get('kind')}) n'est pas une relecture faite en session.",
            "`forever update approve` ou `forever update reject` pour une installation ou une mesure",
        )
    if entry.get("state") not in OPEN_STATES:
        raise InvalidArgumentError(f"L'attente {pending_id} est déjà {entry.get('state')}.", "rien à faire")
    doc = _set_state(cache_dir, pending_id, "faite", done_at=at, done_by=note)
    return {"id": pending_id, "state": doc["state"], "note": note}


def reject(cache_dir: Path, pending_id: str, reason: str | None) -> dict[str, Any]:
    """Rejette une attente en gardant la raison."""
    _load(cache_dir, pending_id)
    doc = _set_state(cache_dir, pending_id, "rejetée", reason=reason)
    return {"id": pending_id, "state": doc["state"], "reason": reason}


def update_summary(cache_dir: Path, now: datetime | None = None) -> dict[str, Any]:
    """Dernier passage et attentes, en lecture seule (bloc `update` de `forever_status`, ligne de démarrage)."""
    last = _read(update_dir(cache_dir) / "last.json")
    summary_last = None
    if isinstance(last, dict):
        summary_last = {
            "started_at": last.get("started_at"),
            "finished_at": last.get("finished_at"),
            "origin_main": last.get("origin_main"),
            "written": last.get("written", []),
            "verdicts": [{"id": v.get("id"), "action": v.get("action")} for v in last.get("verdicts", [])],
            "steps": [{"name": s.get("name"), "status": s.get("status")} for s in last.get("steps", [])],
        }
    pending = [
        {**{k: e.get(k) for k in ("id", "kind", "action", "version", "state", "created_at")},
         "summary": summary_text(e.get("summary"))}
        for e in list_pending(cache_dir)
        if e.get("state") in OPEN_STATES
    ]  # fmt: skip
    lock = _read(_lock_path(cache_dir))
    when = now or utc_now()
    running = _lock_alive(lock, when)
    doc = lock if running and isinstance(lock, dict) else {}
    detail = str(doc.get("detail") or "") or None
    since = doc.get("detail_at") if detail else doc.get("step_at")
    try:
        minutes: int | None = int((when - parse_utc(str(since))).total_seconds() // 60) if since else None
    except ValueError:
        minutes = None
    return {
        "last": summary_last,
        "pending": pending,
        "running": running,
        "running_step": doc.get("step"),
        "running_started_at": doc.get("started_at"),
        "running_detail": detail,
        "running_activity": activity_of(detail),
        "running_minutes": minutes,
    }


def due(cache_dir: Path, now: datetime) -> bool:
    """Vrai si le dernier passage a plus de `CACHE_TTL` (6 h) ou n'existe pas, et qu'aucun verrou n'est vivant."""
    if _lock_alive(_read(_lock_path(cache_dir)), now):
        return False
    last = _read(update_dir(cache_dir) / "last.json")
    try:
        finished = parse_utc(str(last["finished_at"]))
    except (KeyError, TypeError, ValueError):
        return True
    return now - finished >= CACHE_TTL


def launch_pass(cache_dir: Path, now: datetime, spawn: Spawn) -> bool:
    """Passage `forever update --auto` détaché, sans la règle des 6 h, lancé quand le client vient d'écrire ses
    fichiers (fermeture du jeu, `DBCache.bin` d'un build archivé : décision 227). Rien si un verrou est vivant (le
    passage prendrait le même verrou et s'arrêterait) ; vrai si lancé. OSError du lancement : à l'appelant."""
    if _lock_alive(_read(_lock_path(cache_dir)), now):
        return False
    from forever.spawn import update_command

    spawn(update_command())
    return True
