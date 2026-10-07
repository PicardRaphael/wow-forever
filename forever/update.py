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
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict

from forever.carry import CarryReport, carry_apply, carry_check
from forever.config import CACHE_TTL, REPO_ROOT, UPDATE_CI_TIMEOUT, UPDATE_LOCK_STALE, Deps, utc_now
from forever.engine_inputs import ENGINES, InputsDiff, ValueChange, compare_inputs, targeted_replay
from forever.errors import EXIT_OK, EXIT_PENDING, ForeverError, InvalidArgumentError, PathNotFoundError
from forever.pipeline.tables import ColumnNamesError
from forever.timefmt import format_utc, parse_utc

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
OPEN_STATES = ("en_attente", "approuvée")
SESSION_KINDS = ("column_names",)
SELF_CLEARING_KINDS = ("hotfixes_unread",)  # attentes levées seules par un passage, jamais approuvables
AUTO_ORIGINS = frozenset({"client", "correctif_serveur"})  # installation seule d'un moteur qui recopie (décision 207)
INSTALL_KINDS = ("install_version", "install_revision")
GUARD_REASON = (
    "garde-fou : première écriture git de `forever update --auto`, en attente de l'accord de l'utilisateur jusqu'à "
    "l'approbation d'un premier passage réel"
)  # attentes qu'aucune approbation ne résout : une édition en session est nécessaire
KEPT_STATES = ("approuvée", "faite", "rejetée")  # un passage qui recalcule la même attente ne les écrase pas
HISTORY_KEPT = 30
COMMIT_MESSAGE = "Veille : {version} r{revision} installée par forever update ({motif})"
INVENTORY_DOC = "docs/research/valeurs-ecrites-a-la-main.md"  # rendu de `forever origins inventory` (version courante)
PASS_PATHS = ("forever/data/", "docs/research/data-", INVENTORY_DOC)  # seuls chemins du clone écrits par `_publish`
DATA_BRANCH_RE = re.compile(r"data/(?P<version>\d+\.\d+\.\d+\.\d+)-r(?P<revision>\d+)")
BLOCKED_BY = ("uv_sync", "verify", "ci")  # écriture arrêtée en route : pas de nouvel essai tant que main n'a pas bougé
AUTO_COMMAND = "forever update --auto"
CARRY_FR = ("gardé", "réappliqué", "remplacé", "perdu")

Replay = Callable[[str, str, Path], Any]
"""(moteur, cas, dossier des données) -> résultat du cas ; appelé avant puis après, pour les seuls moteurs touchés."""
Measure = Callable[[Deps, Path, Sequence[Path]], Mapping[str, Any]]
"""(deps, dossier des données, journaux) -> {"changed": [{"file", "pointer"}…], …} ; simulation, rien n'est écrit."""
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


class PendingNotFoundError(PathNotFoundError):
    def __init__(self, pending_id: str) -> None:
        super().__init__("Attente", pending_id, "lister les attentes : forever update status")


# --- Fichiers du dossier de travail --------------------------------------------------------------------------


def update_dir(cache_dir: Path) -> Path:
    """Dossier de travail de `forever update` dans le cache."""
    return cache_dir / UPDATE_DIR


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


def decide(
    verify_ok: bool,
    carry: CarryReport,
    inputs: Mapping[str, InputsDiff],
    kind: str,
    *,
    install_ok: bool = True,
    hotfix_losses: Sequence[ValueChange] = (),
) -> Verdict:
    """Règle d'automatisme (décision 180), pure : `écrire`, `attente` (clauses non tenues) ou `bloqué` (`verify`
    rouge, installation refusée, ou valeur faite à la main perdue)."""
    changed = sorted(name for name, d in inputs.items() if not d.identical)
    clauses = {
        "verify": verify_ok,
        "install": install_ok,
        "manual": not carry.superseded and not carry.lost,
        "inputs": not changed,
    }
    reasons: list[str] = []
    if not verify_ok:
        reasons.append("verify rouge : une session est nécessaire")
    if not install_ok:
        reasons.append("installation refusée par les règles de fusion (forever install) : une session est nécessaire")
    for value in carry.lost:
        reasons.append(f"valeur faite à la main perdue : {value.file} {value.pointer} ({value.origin})")
    for value, now in carry.superseded:
        reasons.append(f"valeur faite à la main remplacée : {value.file} {value.pointer} ({value.origin}) → {now!r}")
    if changed:
        reasons.append(f"moteurs aux entrées changées : {', '.join(changed)}")
    if not verify_ok or not install_ok or carry.lost:
        action = "bloqué"
    elif not all(clauses.values()):
        action = "attente"
    else:
        action = "écrire"
    return Verdict(action, clauses, reasons)


def hotfix_gate(archived: bool, seen_at: datetime | None, now: datetime, wait: timedelta) -> str:
    """Porte des correctifs d'une nouvelle version (décision 207), pure : `lire`, `attendre` ou `sans_correctifs`."""
    raise NotImplementedError


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
    _write(path, {**doc, "step": current, "updated_at": at, "steps": done})


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

    def say(self, line: str) -> None:
        """Ligne du journal du passage, écrite tout de suite (au fil de l'eau, pas à la fin)."""
        if self.progress is not None:
            self.progress(f"{self.now} {line}")

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
    from forever.pipeline.client_builds import read_build_info
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
    product, prefix = (sources or {}).get("product"), (sources or {}).get("version_prefix")
    if not (isinstance(product, str) and isinstance(prefix, str)):
        return Step("jeu", "erreur", f"produit inconnu : sources.json incomplet pour {installed}", data), None
    published = {b.version for b in list_builds(run.deps, product, prefix)}
    newer = [v for v in published if version_key(v) > version_key(client)]
    data["newer_on_wago"] = max(newer, key=version_key) if newer else None
    note = f" ; {data['newer_on_wago']} publiée, plus récente que le client (suivie par build-watch)" if newer else ""
    if client not in published:
        return Step("jeu", "rien", f"client {client} en attente de wago{note}", data), None
    data["target"] = client
    return Step("jeu", "fait", f"cible : {client} (build du client, publié){note}", data), client


def _fetch_version(run: _Run, version: str, rules: Mapping[str, Any]) -> None:
    from forever.pipeline.fetch import fetch_gametables, fetch_tables

    deps = run.deps_on(run.base_data)
    enus: list[str] = []
    localized: dict[str, list[str]] = {}
    for key in ("tables", "class_tables", "character_tables", "pet_tables"):
        enus += [t for t in rules.get(key, []) if t not in enus]
    for key in ("localized_tables", "localized_class_tables", "localized_pet_tables"):
        for locale, names in (rules.get(key) or {}).items():
            localized.setdefault(locale, [])
            localized[locale] += [t for t in names if t not in localized[locale]]
    fetch_tables(deps, version, enus)
    for locale, names in localized.items():
        fetch_tables(deps, version, names, locales=[locale])
    if rules.get("gametables"):
        fetch_gametables(deps, version, rules["gametables"])


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
    return hotfix_source(archive, layouts, dbd, journal, version, rules, run.now)


def _stage(run: _Run, version: str) -> Path:
    """Copie de préparation des données de base, dans le cache (jamais le clone ni la session)."""
    from forever.manifest import VERSION_DIR_RE

    stage = update_dir(run.deps.cache_dir) / f"stage-{version}"
    if stage.exists():
        shutil.rmtree(stage)
    installed = set(installed_versions(run.base_data))

    def ignored(folder: str, names: list[str]) -> set[str]:
        stray = {n for n in names if Path(folder) == run.base_data and VERSION_DIR_RE.match(n) and n not in installed}
        return stray | {n for n in names if n == "__pycache__"}  # dossier de version hors du manifeste : non copié

    shutil.copytree(run.base_data, stage / "data", ignore=ignored)
    return stage / "data"


def _carry_counts(report: CarryReport) -> dict[str, int]:
    return dict(zip(CARRY_FR, (len(report.kept), len(report.reapplied), len(report.superseded), len(report.lost))))


def _inputs_doc(inputs: Mapping[str, InputsDiff]) -> dict[str, Any]:
    return {name: {"identical": d.identical, "items": d.items} for name, d in inputs.items()}


def first_write_guard(cache_dir: Path) -> bool:
    """Vrai tant qu'aucun passage réel n'a été approuvé : une écriture de `--auto` reste alors en attente
    (demande de l'utilisateur du 2026-10-06)."""
    state = _read(update_dir(cache_dir) / "state.json")
    return not (isinstance(state, dict) and state.get("first_write_approved_at"))


def _lift_guard(cache_dir: Path, pending_id: str, at: str) -> None:
    path = update_dir(cache_dir) / "state.json"
    state = _read(path)
    state = state if isinstance(state, dict) else {}
    if not state.get("first_write_approved_at"):
        _write(path, {**state, "first_write_approved_at": at, "first_write_approved_id": pending_id})


def _approved(run: _Run, pending_id: str) -> bool:
    doc = _read(_pending_path(run.deps.cache_dir, pending_id))
    return isinstance(doc, dict) and doc.get("state") == "approuvée"


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
) -> Step:
    """Vérifie la candidate, l'installe dans la copie de préparation, applique la règle, puis écrit (clone et chemin
    git) ou rend une attente."""
    from forever.pipeline.install import InstallRefusedError, apply_install, plan_install
    from forever.pipeline.verify import verify_version

    installed = _installed(run.base_data)
    assert installed is not None
    base_vdir = run.base_data / installed
    verify = verify_version(run.deps_on(run.base_data), str(candidate))
    stage = _stage(run, version)
    stage_deps = run.deps_on(stage)
    install_ok, plan = True, None
    try:
        plan = plan_install(stage_deps, str(candidate), new_version=new_version)
        if plan["refused"]:
            install_ok = False
        else:
            apply_install(stage_deps, str(candidate), motif=motif, new_version=new_version, date=run.now[:10])
    except InstallRefusedError:
        install_ok = False
    except InvalidArgumentError as exc:  # rien à installer (révision qui ne change rien)
        return Step(step, "rien", exc.message, {"version": version})
    after = stage / version if install_ok else candidate / version
    carry = carry_check(base_vdir, after)
    if install_ok and carry.reapplied:
        carry_apply(base_vdir, after, carry)
    inputs = compare_inputs(base_vdir, after)
    replayed: dict[str, Any] = {}
    if run.replay is not None and any(not d.identical for d in inputs.values()):
        replay = run.replay
        replayed = targeted_replay(
            inputs, lambda e, c: {"avant": replay(e, c, run.base_data), "après": replay(e, c, stage)}
        )
    verdict = decide(bool(verify["ok"]), carry, inputs, kind, install_ok=install_ok)
    fingerprint = candidate_fingerprint(stage if install_ok else candidate)
    pending_id = f"{version}-r{revision}-{content_fingerprint(after)}"
    approved = verdict.action == "attente" and _approved(run, pending_id)
    action = "écrire" if approved else verdict.action
    reasons = list(verdict.reasons)
    guarded = action == "écrire" and run.options.auto and first_write_guard(run.deps.cache_dir)
    if guarded and not _approved(run, pending_id):
        action = "attente"
        reasons.append(GUARD_REASON)
    doc = {
        "id": pending_id,
        "kind": kind,
        "version": version,
        "revision": revision,
        "action": action,
        "rule_action": verdict.action,
        "approved": approved,
        "clauses": dict(verdict.clauses),
        "reasons": reasons,
        "verify": {"ok": verify["ok"], "errors": verify.get("errors", [])[:20]},
        "carry": _carry_counts(carry),
        "superseded": [{"file": v.file, "pointer": v.pointer, "after": now} for v, now in carry.superseded],
        "lost": [{"file": v.file, "pointer": v.pointer} for v in carry.lost],
        "inputs": _inputs_doc(inputs),
        "replay": replayed,
        "refused": (plan or {}).get("refused", []) if plan else [],
    }
    run.verdicts.append(doc)
    if action == "écrire":
        if run.options.dry_run:
            return Step(step, "fait", f"{version} r{revision} : écriture simulée (règle tenue)", {"id": pending_id})
        if not run.writable:
            return Step(step, "arrêt", f"{version} r{revision} : règle tenue, mais clone non disponible", {})
        blocked = _blocked_before(run, pending_id)
        if blocked is not None:
            run.pending.append(blocked)
            why = "; ".join(blocked.get("reasons", []))
            return Step(step, "arrêt", f"{version} r{revision} : déjà bloquée sur ce main ({why})", {"id": pending_id})
        return _publish(run, step=step, version=version, revision=revision, stage=stage, plan=plan, verdict=doc)
    entry = {
        **{k: doc[k] for k in ("id", "kind", "version", "revision", "action", "clauses", "reasons")},
        "created_at": run.now,
        "staged": str(stage if install_ok else candidate),
        "staged_sha": fingerprint,
        "candidate": str(candidate),
        "replay": replayed,
        "base": {
            "origin_main": run.origin_main,
            "version": installed,
            "revision": _revision(run.base_data, installed),
            "client_build": getattr(run.client, "build", None),
        },
        "commands": [f"forever update approve {pending_id}"] if action == "attente" else ["session nécessaire"],
    }
    run.pending.append(entry)
    status = "attente" if action == "attente" else "arrêt"
    return Step(step, status, f"{version} r{revision} : {action} ({'; '.join(reasons)})", {"id": pending_id})


def _step_new_version(run: _Run, target: str | None) -> Step:
    from forever.archive import archived_dbcache
    from forever.pipeline import dbcache, hotfixes
    from forever.pipeline.decode import decode_version

    if not run.wants("jeu"):
        return Step("nouvelle_version", "rien", "non demandé (--only)", {})
    if target is None:
        return Step("nouvelle_version", "rien", "aucune version à installer", {})
    rules = _rules(run.base_data)
    _fetch_version(run, target, rules)
    source = None
    archive = archived_dbcache(run.deps.cache_dir, _build_number(target))
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
    return _evaluate(
        run,
        step="nouvelle_version",
        kind="install_version",
        version=target,
        revision=1,
        candidate=candidate.root,
        new_version=True,
        motif=motif,
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
    archive = archived_dbcache(run.deps.cache_dir, _build_number(version))
    if archive is None:
        return Step("correctifs", "rien", f"aucune archive de DBCache.bin pour {version}", {})
    rules = _rules(run.base_data)
    sources = read_sources(run.base_data, version) or {}
    pending = hotfixes.pending_hotfixes(dbcache.read_dbcache(archive), sources, rules)
    if not pending:
        return Step("correctifs", "rien", "aucun correctif du serveur en attente", {"pending": 0})
    try:
        source = _hotfix_source(run, version, archive, rules, [t for t, _ in pending])
    except _NeedLayouts as need:
        return _need_layouts(run, "correctifs", version, need, len(pending))
    _fetch_version(run, version, rules)
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


def _default_replay(deps: Deps, *, listing: bool = False) -> Replay:
    """Rejeu ciblé de production : les cas des builds du Mage passent par `scripts/replay_builds.py` (`run_cases`,
    passages `update-<version>-avant|après` dans `<cache>/builds/`) ; les autres cas (simulation de leveling, fiche
    PvP) ne sont pas rejoués automatiquement et le disent. `listing` (simulation) : les cas sont nommés sans être
    calculés (Monte Carlo de plusieurs minutes par cas)."""
    import importlib.util

    loaded: list[Any] = []

    def module() -> Any:
        if not loaded:
            spec = importlib.util.spec_from_file_location("replay_builds", REPO_ROOT / "scripts" / "replay_builds.py")
            if spec is None or spec.loader is None:
                raise OSError("scripts/replay_builds.py introuvable")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            loaded.append(mod)
        return loaded[0]

    def replay(engine: str, case: str, data_dir: Path) -> Any:
        if listing:
            return {"rejoué": False, "raison": "simulation : cas à rejouer, non calculé"}
        if engine != "mage_build":
            return {"rejoué": False, "raison": "cas sans rejeu automatique (replay_builds : builds du Mage seulement)"}
        stage = update_dir(deps.cache_dir) in data_dir.parents
        label = f"update-{data_dir.parent.name if stage else _installed(data_dir)}-{'après' if stage else 'avant'}"
        rep = module().run_cases(label, [case], data_dir=data_dir, cache_dir=deps.cache_dir)[case]["report"]
        alternative = rep.get("alternative") or {}
        return {
            "talents": rep.get("talents"),
            "choices": rep.get("choices"),
            "alternative": {k: alternative.get(k) for k in ("better", "decided_by", "diff")},
        }

    return replay


def _default_measure(deps: Deps, data_dir: Path, logs: Sequence[Path]) -> Mapping[str, Any]:
    """`forever measures refresh --dry-run` sur les données de base : un changement de la table des monstres est
    une entrée des moteurs du Mage (`monsters.json`)."""
    from forever.cli import main

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["measures", "refresh", "--dry-run", "--json"], dataclasses.replace(deps, data_dir=data_dir))
    payload = json.loads(out.getvalue() or "{}")
    diff = payload.get("diff") or {}
    npcs = diff.get("npcs") or {}
    monsters = any(npcs.get(k) for k in ("added", "changed", "removed")) or bool(diff.get("hp_by_level"))
    changed = [{"file": "monsters.json", "pointer": "/npcs"}] if code == EXIT_OK and monsters else []
    return {"changed": changed, "status": payload.get("status"), "logs": [p.name for p in logs]}


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


def _step_logs(run: _Run) -> Step:
    from forever.pipeline.client_builds import current_builds, split_by_version
    from forever.pipeline.combatlog import log_files
    from forever.pipeline.live_logs import split_live

    if not run.wants("journaux"):
        return Step("journaux", "rien", "non demandé (--only)", {})
    wow = run.deps.wow_dir
    installed = _installed(run.base_data)
    if wow is None or not (wow / "Logs").is_dir() or installed is None:
        return Step("journaux", "rien", "aucun dossier de journaux", {})
    builds = current_builds(run.deps.cache_dir, wow)
    # Décision 205 : un journal que le jeu ouvert écrit encore est tenu et reproposé au passage suivant.
    files, writing = split_live(log_files(wow / "Logs"), now=run.deps.now(), running=run.deps.game_running())
    keep, held, unknown = split_by_version([(p.name, _log_start(p)) for p in files], builds, installed)
    done = _written_logs(run.deps.cache_dir, run.base_data, installed)
    shas = {p.name: _sha256(p) for p in files if p.name in keep}
    fresh = [p for p in files if p.name in shas and shas[p.name] not in done.get(p.name, set())]
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
    digest = hashlib.sha256("\n".join(f"{n}:{shas[n]}" for n in sorted(keep)).encode("utf-8")).hexdigest()[:12]
    pending_id = f"measures-{installed}-{digest}"
    run.pending.append(
        {
            "id": pending_id,
            "kind": "measures",
            "action": "attente",
            "version": installed,
            "revision": None,
            "clauses": {"inputs": False},
            "reasons": [f"mesure des journaux qui change une entrée des moteurs : {touched}"],
            "logs": keep,
            "created_at": run.now,
            "base": {"origin_main": run.origin_main, "version": installed},
            "commands": ["forever measures refresh (session, après accord)"],
        }
    )
    return Step(
        "journaux", "attente", f"{len(keep)} journal(aux) mesuré(s) : une entrée des moteurs change{held_note}", data
    )


def _step_addons(run: _Run) -> Step:
    from forever.addons import addons_status

    if not run.wants("addons"):
        return Step("addons", "rien", "non demandé (--only)", {})
    if run.deps.wow_dir is None or not run.deps.wow_dir.is_dir():
        return Step("addons", "rien", "dossier du client absent", {})
    report = addons_status(run.deps, save=not run.options.dry_run)
    changed = [a for a in report["addons"] if a.get("status") in ("changé", "nouveau")]
    proposals = [u for u in report.get("untracked", []) if u.get("status") == "non_inventorié"]
    for addon in changed:
        proposal = addon.get("proposal")
        if not proposal or proposal.get("kind") != "addon_data":
            continue
        run.pending.append(
            {
                "id": f"addon-{addon['name']}-{str(addon.get('fingerprint'))[:12]}",
                "kind": "addon_data",
                "action": "attente",
                "addon": addon["name"],
                "version": addon.get("version"),
                "revision": None,
                "clauses": {},
                "reasons": [f"{addon['name']} changé : {', '.join(proposal.get('depends', []))}"],
                "files": addon.get("files"),
                "created_at": run.now,
                "base": {"origin_main": run.origin_main, "fingerprint": addon.get("fingerprint")},
                "commands": [str(proposal.get("action"))],
            }
        )
    data = {
        "changed": [{"name": a["name"], "status": a["status"], "version": a.get("version")} for a in changed],
        "untracked": proposals,
    }
    waiting = sum(1 for p in run.pending if p["kind"] == "addon_data")
    if waiting:
        return Step("addons", "attente", f"{waiting} addon(s) dont dépend le dépôt ont changé", data)
    if changed or proposals:
        return Step("addons", "fait", f"{len(changed)} addon(s) changé(s), {len(proposals)} à inventorier", data)
    return Step("addons", "rien", "aucun addon changé", data)


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
    if verdict.get("approved"):
        last["approval"] = verdict["id"]
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(vdir.parent)


def _research_report(plan: Any, verdict: Mapping[str, Any]) -> str:
    from forever.pipeline.install import render_install_report

    lines = [render_install_report(plan).rstrip(), "", "## Report à la main", ""]
    lines += [f"- {k} : {n}" for k, n in verdict["carry"].items()]
    lines += [f"- remplacé : {s['file']} {s['pointer']}" for s in verdict["superseded"]]
    lines += ["", "## Entrées des moteurs", ""]
    for name, d in verdict["inputs"].items():
        state = "identiques" if d["identical"] else "différentes"
        lines.append(f"- {name} : {state}")
    lines += [
        "",
        f"Règle d'automatisme : {verdict['action']} ({'approuvée' if verdict.get('approved') else 'tenue'}).",
        "",
    ]
    return "\n".join(lines)


def _publish(
    run: _Run, *, step: str, version: str, revision: int, stage: Path, plan: Any, verdict: Mapping[str, Any]
) -> Step:
    from forever.pipeline import gitops

    assert run.clone is not None
    runner = run.runner or gitops.subprocess_runner
    clone = run.clone
    data = clone / "forever" / "data"
    run.say(f"{step} : copie de {version} r{revision} dans le clone")
    shutil.rmtree(data)
    shutil.copytree(stage, data)
    _annotate_revision(data / version, verdict, AUTO_COMMAND if run.options.auto else "forever update")
    report_rel = f"docs/research/data-{version}-r{revision}.md"
    (clone / report_rel).parent.mkdir(parents=True, exist_ok=True)
    (clone / report_rel).write_bytes(_research_report(plan, verdict).encode("utf-8"))
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
    branch = f"data/{version}-r{revision}"
    motif = "approuvée" if verdict.get("approved") else "règle tenue"
    message = COMMIT_MESSAGE.format(version=version, revision=revision, motif=motif)
    run.say(f"{step} : verify vert ; commit et poussée de {branch}")
    if gitops.drop_stale_branch(runner, clone, branch):
        run.say(f"{step} : branche {branch} d'un essai abandonné retirée")
    sha = gitops.commit_branch(runner, clone, branch, ["forever/data", report_rel, INVENTORY_DOC], message)
    gitops.push(runner, clone, branch)
    run.say(f"{step} : CI attendue sur {branch} ({sha[:12]}, jusqu'à {UPDATE_CI_TIMEOUT.total_seconds() / 60:.0f} min)")
    ci = gitops.wait_ci(runner, clone, branch, sha, UPDATE_CI_TIMEOUT.total_seconds())
    info = {"version": version, "revision": revision, "branch": branch, "sha": sha, "ci": ci.url, "jobs": ci.jobs}
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
    if verdict.get("approved"):
        _set_state(run.deps.cache_dir, str(verdict["id"]), "faite")
    return Step(
        step, "fait", f"{version} r{revision} installée par le clone ({sha[:12]}) : `git pull` dans la session", info
    )


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


def run_update(
    deps: Deps,
    options: UpdateOptions,
    *,
    runner: Runner | None = None,
    replay: Replay | None = None,
    measure: Measure | None = None,
    progress: Progress | None = None,
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

    def advance(name: str, fn: Callable[[], Step]) -> None:
        _note_step(deps.cache_dir, name, steps, run.now)
        run.say(f"{name} : en cours")
        done(_guard(name, fn))

    if lock is not None and lock.status == "arrêt":
        done(lock)
    else:
        done(lock or Step("verrou", "fait", "verrou pris", {"stale": False}))
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
            done(_end_step(run))
        finally:
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
    if not options.dry_run and len(steps) > 1:
        for entry in run.pending:
            record_pending(deps.cache_dir, entry)
        save_report(deps.cache_dir, report)
    return report


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
    if entry.get("kind") in INSTALL_KINDS:
        _lift_guard(deps.cache_dir, pending_id, format_utc(deps.now()))
    if wait:
        report = run_update(deps, UpdateOptions(auto=True), runner=runner, progress=progress)
        return {"id": pending_id, "state": _load(deps.cache_dir, pending_id)["state"], "detail": "passage fait",
                "report": report}  # fmt: skip
    from forever.spawn import spawn_detached, update_command

    stamp = "".join(c for c in format_utc(deps.now()) if c.isalnum())
    launch = spawn or (lambda args: spawn_detached(args, update_dir(deps.cache_dir) / f"run-{stamp}.log"))
    try:
        launch(update_command())
    except OSError as exc:
        detail = f"approuvée, mais passage non lancé ({exc}) : lancer `forever update --auto`"
    else:
        detail = "approuvée : passage lancé en arrière-plan (`forever update status` pour suivre)"
    return {"id": pending_id, "state": "approuvée", "detail": detail}


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
        }
    pending = [
        {k: e.get(k) for k in ("id", "kind", "action", "version", "state", "created_at")}
        for e in list_pending(cache_dir)
        if e.get("state") in OPEN_STATES
    ]
    lock = _read(_lock_path(cache_dir))
    running = _lock_alive(lock, now or utc_now())
    step = lock.get("step") if running and isinstance(lock, dict) else None
    return {"last": summary_last, "pending": pending, "running": running, "running_step": step}


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
