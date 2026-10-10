"""Conversation « addons » du pont (P06b, bloc F, décision 235) : l'onglet « Addons » de la fenêtre du jeu confie une
demande à un agent `claude` sans shell, limité au dossier de RaphCompletionist (Read, Glob, Grep, Edit, Write ; ligne
de `agent.addons_argv`, règles relatives au dossier de travail vérifiées par la sonde 0.2). Le pont, et lui seul :

- refuse un dossier d'addon de la communauté, le dossier des addons lui-même et le dépôt (`check_folder`) ;
- copie le dossier dans `<cache>/bridge/addons/backups/<horodatage>/` avant chaque tour (`snapshot`) ;
- committe après le tour dans un dépôt git local du dossier (`commit` : `init` au premier usage, `add -A`,
  `commit` avec l'identité ForeverBridge ; sous-commandes de `GIT_SUBCOMMANDS` seulement, jamais de réseau) ;
- copie, si un dossier de déploiement est réglé, les fichiers changés vers le dossier installé (`deploy`), sans en
  supprimer : un fichier absent de la source est seulement signalé ;
- restaure une sauvegarde (`restore`) en déplaçant les fichiers créés depuis vers
  `<cache>/bridge/addons/set-aside/<horodatage>/` : rien n'est détruit.

Configuration : `<cache>/bridge/addons/config.json` (`forever bridge addons config`)."""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.errors import EXIT_USAGE, ForeverError

ADDONS_TIMEOUT_S = 600.0
GIT_SUBCOMMANDS = ("init", "add", "commit", "status", "diff", "log", "rev-parse")
IDENTITY = ("user.name=ForeverBridge", "user.email=forever-bridge@localhost")
MESSAGE_CHARS = 60
USER_ADDONS = ("RaphCompletionist",)  # addons de l'utilisateur (forever/addons.py, OWN_ADDONS, décision 227)
_IGNORED = (".git",)


class AddonsFolderError(ForeverError):
    exit_code = EXIT_USAGE

    def __init__(self, message: str, hint: str) -> None:
        super().__init__("bridge_addons", message, hint)


@dataclass(frozen=True)
class AddonsConfig:
    source: Path
    deploy: Path | None = None

    @property
    def name(self) -> str:
        return (self.deploy or self.source).name


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    files: int


@dataclass(frozen=True)
class DeployReport:
    copied: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RestoreReport:
    stamp: str
    restored: list[str] = field(default_factory=list)
    set_aside: list[str] = field(default_factory=list)


def addons_home(cache_dir: Path) -> Path:
    return cache_dir / "bridge" / "addons"


# --- Configuration -------------------------------------------------------------------------------------------------


def load_config(cache_dir: Path) -> AddonsConfig | None:
    try:
        doc = json.loads((addons_home(cache_dir) / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or not doc.get("source"):
        return None
    return AddonsConfig(Path(doc["source"]), Path(doc["deploy"]) if doc.get("deploy") else None)


def save_config(cache_dir: Path, config: AddonsConfig) -> None:
    path = addons_home(cache_dir) / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"source": str(config.source), "deploy": str(config.deploy) if config.deploy else None}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    os.replace(tmp, path)


def check_folder(path: Path, addons_dir: Path) -> None:
    """Refuse un dossier absent, le dossier des addons lui-même, un addon de la communauté ou du dépôt installé dans le
    jeu, et le dépôt forever-core ; accepte un addon de l'utilisateur (`USER_ADDONS`) ou un dossier hors des addons."""
    from forever.bridge.install import REPO_ROOT

    if not path.is_dir():
        raise AddonsFolderError(f"Dossier introuvable : {path}.", "donner le dossier de l'addon (--source)")
    resolved, addons = path.resolve(), addons_dir.resolve()
    if resolved == addons:
        raise AddonsFolderError(
            "Le dossier des addons entier n'est jamais confié à la conversation « addons ».", "donner un seul addon"
        )
    if resolved.is_relative_to(REPO_ROOT.resolve()):
        raise AddonsFolderError("Le dépôt forever-core n'est pas un dossier d'addon.", "donner le dossier de l'addon")
    if resolved.is_relative_to(addons):
        top = resolved.relative_to(addons).parts[0]
        if top not in USER_ADDONS:
            raise AddonsFolderError(
                f"{top} n'est pas un addon de l'utilisateur : la conversation « addons » ne touche jamais aux addons "
                "de la communauté ni aux addons du dépôt (décision 196).",
                f"choisir parmi {', '.join(USER_ADDONS)}, ou un projet hors du dossier des addons",
            )


# --- Sauvegarde, git local, déploiement, restauration --------------------------------------------------------------


def _files(folder: Path) -> list[str]:
    out = []
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if path.is_file() and not any(part in _IGNORED for part in rel.parts):
            out.append(rel.as_posix())
    return out


def snapshot(config: AddonsConfig, cache_dir: Path, stamp: str) -> Path:
    """Copie complète du dossier source (sans `.git`) dans les sauvegardes ; rend le dossier de la copie."""
    target = addons_home(cache_dir) / "backups" / stamp
    shutil.copytree(config.source, target, ignore=shutil.ignore_patterns(*_IGNORED), dirs_exist_ok=True)
    return target


Run = Callable[..., subprocess.CompletedProcess[str]]


def git(folder: Path, *args: str, run: Run = subprocess.run) -> subprocess.CompletedProcess[str]:
    """`git -C <dossier> …` local ; ValueError pour une sous-commande hors de GIT_SUBCOMMANDS."""
    sub = next((a for a in args if not a.startswith("-") and "=" not in a), None)
    if sub not in GIT_SUBCOMMANDS:
        raise ValueError(f"sous-commande git refusée : {sub}")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # pas de fenêtre de console sous Windows
    return run(["git", "-C", str(folder), *args], capture_output=True, text=True, check=False, creationflags=flags)


def commit(config: AddonsConfig, message: str, *, run: Run = subprocess.run) -> CommitInfo | None:
    """Commit local de tout ce qui a changé dans le dossier source ; None si rien n'a changé."""
    folder = config.source
    if not (folder / ".git").exists():
        git(folder, "init", run=run)
    git(folder, "add", "-A", run=run)
    status = git(folder, "status", "--porcelain", run=run).stdout or ""
    changed = [line for line in status.splitlines() if line.strip()]
    if not changed:
        return None
    pairs = [x for pair in IDENTITY for x in ("-c", pair)]
    git(folder, *pairs, "commit", "-m", message, run=run)
    sha = (git(folder, "rev-parse", "--short", "HEAD", run=run).stdout or "").strip()
    return CommitInfo(sha=sha, files=len(changed))


def deploy(config: AddonsConfig) -> DeployReport:
    """Copie vers le dossier installé les fichiers ajoutés ou modifiés ; signale ceux qui manquent à la source."""
    if config.deploy is None:
        return DeployReport()
    source, target = config.source, config.deploy
    copied = []
    for rel in _files(source):
        dest = target / rel
        if dest.is_file() and filecmp.cmp(source / rel, dest, shallow=False):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, dest)
        copied.append(rel)
    present = set(_files(source))
    missing = [rel for rel in _files(target) if rel not in present]
    return DeployReport(copied=copied, missing=missing)


def backups(cache_dir: Path) -> list[str]:
    folder = addons_home(cache_dir) / "backups"
    return sorted(p.name for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []


def restore(config: AddonsConfig, cache_dir: Path, stamp: str | None, now: str) -> RestoreReport:
    """Remet la sauvegarde `stamp` (défaut : la plus récente) ; les fichiers créés depuis sont déplacés, jamais
    supprimés."""
    stamps = backups(cache_dir)
    chosen = stamp or (stamps[-1] if stamps else None)
    if chosen is None or chosen not in stamps:
        raise AddonsFolderError(f"Sauvegarde introuvable : {chosen}.", "forever bridge addons status les liste")
    backup = addons_home(cache_dir) / "backups" / chosen
    kept = set(_files(backup))
    aside_root = addons_home(cache_dir) / "set-aside" / now
    set_aside = []
    for rel in _files(config.source):
        if rel not in kept:
            dest = aside_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(config.source / rel, dest)  # déplacement sur le même volume : rien n'est détruit
            set_aside.append(rel)
    restored = []
    for rel in sorted(kept):
        dest = config.source / rel
        if dest.is_file() and filecmp.cmp(backup / rel, dest, shallow=False):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup / rel, dest)
        restored.append(rel)
    return RestoreReport(stamp=chosen, restored=restored, set_aside=set_aside)


# --- Un tour de conversation ----------------------------------------------------------------------------------------


class AddonsTurn:
    """Un tour de la conversation « addons » : sauvegarde, agent, commit, déploiement ; rend la réponse publiée."""

    def __init__(
        self,
        *,
        config: AddonsConfig,
        cache_dir: Path,
        agent: Callable[[str, str | None], Any],
        snapshot: Callable[[AddonsConfig, Path, str], Path] = snapshot,
        run: Run = subprocess.run,
        now: Callable[[], str],
    ) -> None:
        self.config = config
        self.cache_dir = cache_dir
        self.agent = agent
        self.snapshot = snapshot
        self.run = run
        self.now = now

    def status(self) -> dict[str, Any]:
        return {"configured": True, "name": self.config.name, "source": str(self.config.source)}

    def __call__(self, question: str, session: str | None) -> tuple[Any, str]:
        """(résultat de l'agent, texte publié) ; la sauvegarde précède toujours l'agent."""
        from forever.bridge.prompt import addons_message

        self.snapshot(self.config, self.cache_dir, self.now())
        result = self.agent(addons_message(self.config.name, question), session)
        if getattr(result, "is_error", False):
            return result, ""
        info = commit(self.config, f"Conversation addons : {question.strip()[:MESSAGE_CHARS]}", run=self.run)
        report = deploy(self.config)
        lines = [f"{info.sha} · {info.files} fichier(s)" if info else "aucun fichier changé"]
        if report.copied:
            lines.append(f"déployé vers {self.config.deploy} : {len(report.copied)} fichier(s)")
        if report.missing:
            lines.append(f"absents de la source, laissés dans le dossier installé : {', '.join(report.missing)}")
        return result, "\n".join(lines)
