"""`forever doctor` (LN1, bloc D, décision 271) : contrôle de toute l'installation, sans réseau, chaque problème avec
sa correction. Contrôles purs : tout ce qui touche au système (sous-processus, tâches planifiées, processus) passe par
des sondes injectées (`forever/doctor_probes.py`).

Chaque contrôle rend `Check(id, status, finding, fix)` : `ok`, `warn` (à corriger, rien ne casse encore), `fail`
(bloquant : code 7), `unknown` (non vérifiable ici) ou `info`. La correction est une commande ou un geste précis ;
aucune n'est appliquée par `forever doctor`."""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from forever import toc
from forever.config import Deps
from forever.errors import EXIT_DOCTOR, EXIT_OK, ForeverError

STATUSES = ("ok", "warn", "fail", "unknown", "info")
MARKS = {"ok": "[ok]", "warn": "[!]", "fail": "[x]", "unknown": "[?]", "info": "[i]"}
BRIDGE_TASK = "WoW Forever - pont"
UPDATE_TASK = "WoW Forever - mise à jour"
FIX_UV = 'uv sync à la racine du dépôt, puis relancer les deux tâches (schtasks /Run /TN "WoW Forever - pont")'
FIX_PLUGIN = r"powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1"
FIX_BRIDGE_TASK = "uv run forever bridge autostart install"
FIX_UPDATE_TASK = r"powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1"
FIX_LOGGER = "uv run python scripts/install_addon.py (jeu fermé)"
FIX_BRIDGE = "uv run forever bridge install (jeu fermé)"
FIX_LOGIN = "lancer claude dans un terminal, puis /login"
RECENT_LOG = timedelta(days=7)
BACKUP_MAX_AGE = timedelta(days=2)
AUTH_ERRORS = re.compile(r"oauth|session expired|/login|\b401\b", re.IGNORECASE)
SV_BRIDGES = ("ForeverSVBridge",)  # addons tiers de contournement des SavedVariables de la bêta (non modélisé)
ENV_VARS = (
    "FOREVER_WOW_DIR",
    "FOREVER_HOME",
    "FOREVER_CACHE_DIR",
    "FOREVER_PROFILE",
    "FOREVER_WOW_FORCE",
    "FOREVER_WOW_ROOTS",
    "FOREVER_BACKUP_DIR",
)


@dataclass(frozen=True)
class Check:
    """Un contrôle : identifiant stable, état, constat et correction (commande ou geste précis)."""

    id: str
    status: str
    finding: str
    fix: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "finding": self.finding,
            "fix": self.fix,
            "certainty": "suppose" if self.status == "unknown" else "certain",
        }

    def lines(self) -> list[str]:
        out = [f"{MARKS[self.status]} {self.id} : {self.finding}"]
        if self.fix and self.status in ("warn", "fail", "unknown"):
            out.append(f"      correction : {self.fix}")
        return out


@dataclass(frozen=True)
class Probes:
    """Sondes du système, injectées (tests : simulées ; production : `doctor_probes.default_probes`)."""

    windows: bool
    system_drive: str
    repo: Path
    gh_version: Callable[[], str | None]
    gh_token: Callable[[], bool | None]
    claude_path: Callable[[], str | None]
    claude_auth: Callable[[], dict[str, Any] | None]
    uv_check: Callable[[Path], tuple[bool | None, str]]
    python_check: Callable[[], str | None]
    task: Callable[[str], dict[str, str | None] | None]
    supervisor_pid: Callable[[Path], int | None]
    bridge_pid: Callable[[Path], int | None]


class _Context:
    """Ce que plusieurs contrôles lisent : choix de l'installation, journal du pont, sauvegardes."""

    def __init__(self, deps: Deps, probes: Probes) -> None:
        from forever.backup import default_root, list_backups
        from forever.bridge.journal import Journal
        from forever.installs import survey

        self.deps, self.probes = deps, probes
        self.choice, self.installs = survey(
            deps.environ, drives=deps.drives, cache_dir=deps.cache_dir, data_dir=deps.data_dir
        )
        self.wow = self.choice.folder if self.choice.folder is not None else deps.wow_dir
        self.journal = Journal(deps.cache_dir / "bridge" / "journal", deps.now)
        self.backup_root, self.backup_warning = default_root(deps)
        self.backups = list_backups(self.backup_root)

    @property
    def addons(self) -> Path | None:
        return self.wow / "Interface" / "AddOns" if self.wow is not None else None


# --- Environnement du projet ---------------------------------------------------------------------------------------


def _repo(ctx: _Context) -> Check:
    repo = ctx.probes.repo
    missing = [name for name in ("pyproject.toml", "uv.lock", ".venv", "forever") if not (repo / name).exists()]
    if missing:
        return Check("repo", "fail", f"dépôt {repo} incomplet : {', '.join(missing)} absent(s)", f"uv sync dans {repo}")
    return Check("repo", "ok", f"dépôt {repo}, environnement .venv présent")


def _env_python(ctx: _Context) -> Check:
    error = ctx.probes.python_check()
    if error is None:
        return Check("env.python", "ok", "l'interpréteur du pont et des tâches charge forever et ses paquets")
    return Check("env.python", "fail", f"l'interpréteur du pont ne charge pas forever : {error}", FIX_UV)


def _env_state(ctx: _Context) -> Check:
    from forever.spawn import environment_line, read_environment

    found = []
    for name in ("bridge", "update"):
        doc = read_environment(ctx.deps.cache_dir / name)
        if doc is not None:
            found.append(f"{name} : {environment_line(doc)}")
    if found:
        return Check("env.state", "fail", " ; ".join(found), FIX_UV)
    return Check("env.state", "ok", "aucun échec de démarrage noté par le pont ou la tâche de mise à jour")


def _env_uv(ctx: _Context) -> Check:
    ok, detail = ctx.probes.uv_check(ctx.probes.repo)
    if ok is None:
        return Check(
            "env.uv", "unknown", f".venv face à uv.lock non vérifiable : {detail}", f"uv sync dans {ctx.probes.repo}"
        )
    if not ok:
        return Check("env.uv", "fail", f".venv ne suit pas uv.lock : {detail}", f"uv sync dans {ctx.probes.repo}")
    return Check("env.uv", "ok", ".venv suit uv.lock (uv sync --dry-run --offline : rien à changer)")


# --- Installation du client ----------------------------------------------------------------------------------------


def _wow_installs(ctx: _Context) -> Check:
    if not ctx.installs:
        return Check(
            "wow.installs",
            "fail",
            "aucune installation du client trouvée (racines usuelles, FOREVER_WOW_ROOTS, FOREVER_WOW_DIR)",
            "déclarer la racine « World of Warcraft » dans FOREVER_WOW_ROOTS, puis forever wow list",
        )
    found = ", ".join(f"{i.folder} ({i.role})" for i in ctx.installs)
    return Check("wow.installs", "ok", f"{len(ctx.installs)} installation(s) : {found}")


def _wow_choice(ctx: _Context) -> Check:
    if ctx.choice.folder is None:
        return Check("wow.choice", "fail", f"aucune installation lue ({ctx.choice.reason})", "forever wow list")
    return Check("wow.choice", "ok", f"installation lue : {ctx.choice.folder} ({ctx.choice.reason})")


def _wow_unknown(ctx: _Context) -> Check:
    unknown = [i for i in ctx.installs if i.role == "unknown"]
    if not unknown:
        return Check("wow.unknown", "ok", "aucun produit inconnu")
    first = unknown[0]
    what = ", ".join(f"{i.product or 'produit illisible'} dans {i.folder}" for i in unknown)
    if first.product is None:
        return Check(
            "wow.unknown", "warn", f"produit inconnu : {what}", f"FOREVER_WOW_FORCE={first.folder} si c'est le bon"
        )
    return Check(
        "wow.unknown",
        "warn",
        f"produit inconnu : {what} (version finale ? à adopter une fois)",
        f"forever wow adopt {first.folder}",
    )


def _wow_env(ctx: _Context) -> Check:
    from forever.installs import same_folder

    configured = ctx.deps.environ.get("FOREVER_WOW_DIR", "").strip()
    if ctx.choice.folder is None:
        return Check("wow.env", "unknown", "aucune installation lue : FOREVER_WOW_DIR non comparée", FIX_PLUGIN)
    if not configured:
        return Check(
            "wow.env", "warn", f"FOREVER_WOW_DIR non fixée (installation lue : {ctx.choice.folder})", FIX_PLUGIN
        )
    if not same_folder(Path(configured), ctx.choice.folder):
        return Check(
            "wow.env",
            "fail",
            f"FOREVER_WOW_DIR vise {configured}, forever lit {ctx.choice.folder} ({ctx.choice.reason})",
            FIX_PLUGIN,
        )
    return Check("wow.env", "ok", f"FOREVER_WOW_DIR = installation lue ({configured})")


def _wow_paths(ctx: _Context) -> Check:
    wow = ctx.wow
    if wow is None or not wow.is_dir():
        return Check("wow.paths", "fail", f"dossier du client absent : {wow}", "forever wow list")
    if not (wow / "Interface" / "AddOns").is_dir():
        return Check(
            "wow.paths", "fail", f"{wow / 'Interface' / 'AddOns'} absent", "lancer le jeu une fois, puis le fermer"
        )
    missing = [name for name in ("Logs", "WTF") if not (wow / name).is_dir()]
    if not list((wow / "WTF").glob("Account/*/SavedVariables")):
        missing.append(r"WTF\Account\*\SavedVariables")
    if missing:
        return Check(
            "wow.paths", "warn", f"absent(s) dans {wow} : {', '.join(missing)}", "se connecter une fois, puis quitter"
        )
    return Check("wow.paths", "ok", f"Interface\\AddOns, Logs et SavedVariables présents dans {wow}")


# --- Addons --------------------------------------------------------------------------------------------------------


def _differs(installed: Path, source: Path) -> list[str]:
    out = []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source)
        try:
            same = (installed / rel).read_bytes() == path.read_bytes()
        except OSError:
            same = False
        if not same:
            out.append(rel.as_posix())
    return out


def _addons_logger(ctx: _Context) -> Check:
    from forever.bridge.install import REPO_ROOT

    if ctx.addons is None or not (ctx.addons / "ForeverLogger").is_dir():
        return Check("addons.logger", "fail", "ForeverLogger absent de l'installation lue", FIX_LOGGER)
    stale = _differs(ctx.addons / "ForeverLogger", REPO_ROOT / "addon" / "ForeverLogger")
    if stale:
        return Check("addons.logger", "fail", f"ForeverLogger différent du dépôt : {', '.join(stale[:5])}", FIX_LOGGER)
    seen = _interface_seen(ctx)
    if seen is not None and seen not in toc.INTERFACES:
        return Check(
            "addons.logger",
            "fail",
            f"le jeu annonce l'interface {seen} (ForeverLogger), absente des .toc ({', '.join(toc.INTERFACES)}) : "
            "addons « périmés » pour ce client",
            "ajouter la valeur à forever.toc.INTERFACES puis réinstaller les addons (docs/LANCEMENT.md)",
        )
    return Check("addons.logger", "ok", "ForeverLogger identique au dépôt")


def _interface_seen(ctx: _Context) -> str | None:
    """Interface du client notée par ForeverLogger 0.7.0 dans l'instantané le plus récent (tous les comptes)."""
    from forever.pipeline.addon_sv import read_logger_db

    if ctx.wow is None:
        return None
    latest: tuple[int, str] | None = None
    for path in sorted((ctx.wow / "WTF" / "Account").glob("*/SavedVariables/ForeverLogger.lua")):
        try:
            db = read_logger_db(path)
        except (OSError, ForeverError):  # une sauvegarde illisible ne cache pas les autres
            continue
        for character in db.characters.values():
            for snap in character.snapshots:
                interface = (snap.client or {}).get("interface")
                if interface is not None and (latest is None or (snap.time or 0) >= latest[0]):
                    latest = (snap.time or 0, str(interface))
    return latest[1] if latest else None


def _addons_bridge(ctx: _Context) -> Check:
    from forever.bridge.install import ADDON, PROBE2_ADDON, PROBE_ADDON, addon_outdated
    from forever.bridge.slots import SLOTS, slot_name

    addons = ctx.addons
    if addons is None or not (addons / ADDON).is_dir():
        return Check("addons.bridge", "fail", "ForeverBridge absent de l'installation lue", FIX_BRIDGE)
    stale = addon_outdated(addons)
    if stale:
        return Check("addons.bridge", "fail", f"ForeverBridge différent du dépôt : {', '.join(stale[:5])}", FIX_BRIDGE)
    slots = sum(1 for i in range(1, SLOTS + 1) if (addons / slot_name(i) / f"{slot_name(i)}.toc").is_file())
    probes = sum(1 for name in (PROBE_ADDON, PROBE2_ADDON) if (addons / name / f"{name}.toc").is_file())
    if slots != SLOTS or probes != 2:
        return Check(
            "addons.bridge", "fail", f"réserve incomplète : {slots}/{SLOTS} emplacements, {probes}/2 sondes", FIX_BRIDGE
        )
    return Check("addons.bridge", "ok", f"ForeverBridge identique au dépôt, réserve complète ({SLOTS} emplacements)")


def _combatlog(ctx: _Context) -> Check:
    from forever.errors import UnsupportedLogError
    from forever.pipeline.combatlog import log_files, read_log

    fix = "activer ForeverLogger (il active le journal avancé à chaque connexion), puis se connecter et jouer"
    wow = ctx.wow
    logs = log_files(wow / "Logs") if wow is not None and (wow / "Logs").is_dir() else []
    config = wow / "WTF" / "Config.wtf" if wow is not None else None
    advanced_set = (
        config is not None
        and config.is_file()
        and re.search(r'SET advancedCombatLogging "1"', config.read_text(encoding="utf-8", errors="replace"))
    )
    if not logs:
        return Check("combatlog", "warn", "aucun journal de combat dans Logs", fix)
    newest = max(logs, key=lambda p: p.stat().st_mtime)
    when = datetime.fromtimestamp(newest.stat().st_mtime, tz=ctx.deps.now().tzinfo)
    try:
        read_log(newest)
    except UnsupportedLogError as exc:
        return Check("combatlog", "fail", f"{newest.name} illisible : {exc.message}", fix)
    if ctx.deps.now() - when > RECENT_LOG:
        return Check("combatlog", "warn", f"aucun journal de combat depuis 7 jours (dernier : {newest.name})", fix)
    if not advanced_set:
        return Check("combatlog", "warn", 'advancedCombatLogging "1" absent de WTF\\Config.wtf', fix)
    return Check("combatlog", "ok", f"journal avancé récent : {newest.name}")


def _addons_data(ctx: _Context) -> Check:
    from forever.addons import addons_status

    if ctx.addons is None:
        return Check("addons.data", "unknown", "aucune installation lue", "forever wow list")
    report = addons_status(ctx.deps, addons_dir=ctx.addons)
    absent = [a["name"] for a in report["addons"] if a["status"] == "absent"]
    if absent:
        return Check("addons.data", "info", f"addons de données absents (facultatifs) : {', '.join(absent)}")
    return Check("addons.data", "ok", "addons de données présents")


def _env_vars(ctx: _Context) -> Check:
    environ = ctx.deps.environ
    problems = []
    values = []
    for name in ENV_VARS:
        value = environ.get(name, "").strip()
        if not value:
            continue
        values.append(f"{name}={value}")
        paths = [p for p in value.split(";") if p.strip()] if name == "FOREVER_WOW_ROOTS" else [value]
        if name != "FOREVER_PROFILE" and any(not Path(p).exists() for p in paths):
            problems.append(f"{name} vise un dossier absent ({value})")
    home = environ.get("FOREVER_HOME", "").strip()
    if home and Path(home).resolve() != ctx.probes.repo.resolve():
        problems.append(f"FOREVER_HOME vise {home}, le dépôt est {ctx.probes.repo}")
    if problems:
        return Check("env.vars", "warn", " ; ".join(problems), FIX_PLUGIN)
    return Check("env.vars", "ok", " ; ".join(values) or "aucune variable FOREVER_* fixée")


# --- Outils --------------------------------------------------------------------------------------------------------


def _gh(ctx: _Context) -> Check:
    version = ctx.probes.gh_version()
    if version is None:
        return Check(
            "gh",
            "fail",
            "gh introuvable (forever update ne peut pas pousser ni attendre la CI)",
            "winget install --id GitHub.cli",
        )
    if ctx.probes.gh_token() is False:
        return Check("gh", "fail", f"{version} : aucun jeton GitHub", "gh auth login")
    return Check("gh", "ok", f"{version}, jeton présent (validité non contrôlée : il faudrait le réseau)")


def _last(entries: list[dict[str, Any]]) -> str:
    return max((str(e.get("at", "")) for e in entries), default="")


def _claude(ctx: _Context) -> Check:
    if ctx.probes.claude_path() is None:
        return Check("claude", "fail", "commande claude introuvable dans le PATH", "installer Claude Code, puis /login")
    auth = ctx.probes.claude_auth()
    errors = [e for e in ctx.journal.recent("error") if AUTH_ERRORS.search(str(e.get("error", "")))]
    if errors and _last(errors) > _last(ctx.journal.recent("reply")):
        return Check(
            "claude",
            "fail",
            "connexion de Claude Code expirée (journal du pont, depuis la dernière réponse)",
            FIX_LOGIN,
        )
    if auth is None:
        return Check("claude", "unknown", "claude auth status illisible", FIX_LOGIN)
    if not auth.get("loggedIn"):
        return Check("claude", "fail", "Claude Code non connecté (claude auth status)", FIX_LOGIN)
    return Check("claude", "ok", f"Claude Code connecté ({auth.get('authMethod')})")


# --- Tâches et pont ------------------------------------------------------------------------------------------------


def _forced_dir(arguments: str | None) -> str | None:
    if not arguments or "--wow-dir" not in arguments:
        return None
    parts = shlex.split(arguments, posix=False)
    for i, part in enumerate(parts[:-1]):
        if part == "--wow-dir":
            return parts[i + 1].strip('"')
    return None


def _task(ctx: _Context, check_id: str, name: str, fix: str) -> Check:
    from forever.installs import same_folder

    if not ctx.probes.windows:
        return Check(check_id, "unknown", "non applicable hors Windows (tâche planifiée)", fix)
    task = ctx.probes.task(name)
    if task is None:
        return Check(check_id, "fail", f"tâche « {name} » absente", fix)
    command, workdir = task.get("command"), task.get("working_directory")
    if not command or not Path(command).is_file():
        return Check(check_id, "fail", f"interpréteur de la tâche introuvable : {command}", fix)
    if not workdir or not same_folder(Path(workdir), ctx.probes.repo):
        return Check(check_id, "fail", f"la tâche lance le dépôt {workdir}, pas {ctx.probes.repo}", fix)
    forced = _forced_dir(task.get("arguments"))
    if forced is not None and (ctx.choice.folder is None or not same_folder(Path(forced), ctx.choice.folder)):
        return Check(
            check_id,
            "fail",
            f"tâche ancienne, à recréer : dossier forcé {forced}, installation lue {ctx.choice.folder}",
            fix,
        )
    return Check(check_id, "ok", f"tâche « {name} » en place ({command})")


def _bridge_running(ctx: _Context) -> Check:
    supervisor = ctx.probes.supervisor_pid(ctx.deps.cache_dir)
    bridge = ctx.probes.bridge_pid(ctx.deps.cache_dir)
    if supervisor is None:
        return Check("bridge.running", "warn", "surveillance du pont arrêtée", f'schtasks /Run /TN "{BRIDGE_TASK}"')
    if bridge is None:
        return Check(
            "bridge.running",
            "warn",
            f"surveillance en marche (pid {supervisor}), pont arrêté",
            "uv run forever bridge status",
        )
    return Check("bridge.running", "ok", f"surveillance (pid {supervisor}) et pont (pid {bridge}) en marche")


def _bridge_journal(ctx: _Context) -> Check:
    day = timedelta(days=1)
    now = ctx.deps.now()

    def recent(event: str) -> list[dict[str, Any]]:
        out = []
        for entry in ctx.journal.recent(event, days=2):
            try:
                at = datetime.fromisoformat(str(entry.get("at")))
            except ValueError:
                continue
            if now - at <= day:
                out.append(entry)
        return out

    env_errors = recent("autostart_env_error")
    if env_errors:
        return Check("bridge.journal", "fail", f"le pont ne peut pas démarrer : {env_errors[-1].get('error')}", FIX_UV)
    downs = recent("autostart_bridge_down")
    if len(downs) >= 3:
        return Check(
            "bridge.journal",
            "warn",
            f"pont mort {len(downs)} fois en 24 h",
            "uv run forever bridge status (journal du pont)",
        )
    return Check("bridge.journal", "ok", "aucune boucle d'arrêts ni échec de démarrage en 24 h")


# --- Profil et sauvegardes -----------------------------------------------------------------------------------------


def _profile(ctx: _Context) -> Check:
    from forever.profile import resolve_path

    path = resolve_path(ctx.deps)
    if not path.is_file():
        if ctx.backups:
            return Check("profile", "fail", f"profil absent ({path}), sauvegarde {ctx.backups[-1].stamp} disponible",
                         "forever backup restore --only profile")  # fmt: skip
        return Check("profile", "fail", f"profil absent ({path})", "forever profile import")
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Check("profile", "fail", f"profil illisible ({path}) : {exc}", "forever backup restore --only profile")
    return Check("profile", "ok", f"profil lisible ({path})")


def _backup(ctx: _Context) -> Check:
    if not ctx.backups:
        return Check("backup", "warn", f"aucune sauvegarde dans {ctx.backup_root}", "uv run forever backup")
    last = ctx.backups[-1]
    root_drive = Path(ctx.backup_root).drive.upper()
    system = ctx.probes.system_drive.rstrip("\\/").upper()
    fix_root = "poser FOREVER_BACKUP_DIR vers un autre disque (F:\\WoW Forever\\sauvegardes par exemple)"
    if ctx.backup_warning or root_drive == system:
        return Check("backup", "warn", f"sauvegardes sur le disque système ({ctx.backup_root})", fix_root)
    try:
        made = datetime.fromisoformat(last.created_at)
    except ValueError:
        made = None
    if made is None or ctx.deps.now() - made > BACKUP_MAX_AGE:
        return Check("backup", "warn", f"dernière sauvegarde trop ancienne ({last.stamp})", "uv run forever backup")
    return Check("backup", "ok", f"dernière sauvegarde {last.stamp} dans {ctx.backup_root}")


def _antivirus(ctx: _Context) -> Check:
    fix = "docs/LANCEMENT.md, section antivirus (exclusions à poser à la main, en administrateur)"
    if not ctx.probes.windows:
        return Check("antivirus", "unknown", "non applicable hors Windows", fix)
    return Check("antivirus", "unknown", "exclusions de Defender non vérifiables sans droits d'administrateur", fix)


def _sv_bridge(ctx: _Context) -> Check:
    found = [name for name in SV_BRIDGES if ctx.addons is not None and (ctx.addons / name).is_dir()]
    if found:
        return Check(
            "info.sv_bridge",
            "info",
            f"addon tiers de contournement des SavedVariables présent ({', '.join(found)}) : non modélisé par forever",
        )
    return Check("info.sv_bridge", "ok", "aucun addon tiers de contournement des SavedVariables")


CHECKS: tuple[tuple[str, Callable[[_Context], Check]], ...] = (
    ("repo", _repo),
    ("env.python", _env_python),
    ("env.state", _env_state),
    ("env.uv", _env_uv),
    ("wow.installs", _wow_installs),
    ("wow.choice", _wow_choice),
    ("wow.unknown", _wow_unknown),
    ("wow.env", _wow_env),
    ("wow.paths", _wow_paths),
    ("addons.logger", _addons_logger),
    ("addons.bridge", _addons_bridge),
    ("combatlog", _combatlog),
    ("addons.data", _addons_data),
    ("env.vars", _env_vars),
    ("gh", _gh),
    ("claude", _claude),
    ("tasks.bridge", lambda ctx: _task(ctx, "tasks.bridge", BRIDGE_TASK, FIX_BRIDGE_TASK)),
    ("tasks.update", lambda ctx: _task(ctx, "tasks.update", UPDATE_TASK, FIX_UPDATE_TASK)),
    ("bridge.running", _bridge_running),
    ("bridge.journal", _bridge_journal),
    ("profile", _profile),
    ("backup", _backup),
    ("antivirus", _antivirus),
    ("info.sv_bridge", _sv_bridge),
)


def run_checks(deps: Deps, probes: Probes) -> list[Check]:
    """Tous les contrôles, dans l'ordre ; un contrôle qui lève devient `unknown` (jamais d'arrêt du diagnostic)."""
    ctx = _Context(deps, probes)
    out = []
    for check_id, check in CHECKS:
        try:
            out.append(check(ctx))
        except Exception as exc:  # noqa: BLE001 : un contrôle cassé ne cache pas les autres
            out.append(Check(check_id, "unknown", f"contrôle en erreur : {type(exc).__name__}: {exc}"))
    return out


def exit_code(checks: list[Check]) -> int:
    """7 dès qu'un contrôle est `fail`, 0 sinon."""
    return EXIT_DOCTOR if any(c.status == "fail" for c in checks) else EXIT_OK


def summary(checks: list[Check]) -> dict[str, int]:
    return {status: sum(1 for c in checks if c.status == status) for status in STATUSES}
