"""MythicSim compilé chez nous depuis un commit épinglé, sans aucune modification du code (MS1, décision 301), sur le
modèle de wowsims/forever (`wowsims_build.py`) : le projet publie un moteur Rust (sage3648/mythicsim-forever-engine,
MIT) porté de son fork Go (sage3648/mythicsim-forever-engine-go). `forever sims update` (et la veille) :

- copie le moteur en lecture seule (clone superficiel, `<cache>/third_party/mythicsim/engine`), remis sur son dernier
  commit ;
- copie son fork Go à la révision que le moteur épingle lui-même (`upstream/sources.json`, source `reference`,
  `pinned_revision`) dans `<cache>/third_party/mythicsim/go` : rotations, options et arbres des talents du même proto ;
- compile `cargo +<chaîne> build --locked --release` (chaîne de `rust-toolchain.toml`, installée par `rustup` au
  besoin ; sous Windows la chaîne GNU, sans outils de Microsoft) ;
- épingle le binaire copié hors du clone (`pin.json` : commit, date, empreinte, chaîne, révision du fork).

Un commit déjà compilé n'est pas recompilé ; un échec garde le binaire épinglé précédent. Réseau : git (dépôts publics)
et les téléchargements de `rustup` et `cargo` ; jamais d'envoi. Les commandes passent par l'exécuteur de `gitops`."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forever.pipeline import gitops
from forever.pipeline.gitops import path_with_cargo  # noqa: F401 : réexporté

REPO = "https://github.com/sage3648/mythicsim-forever-engine.git"
GO_REPO = "https://github.com/sage3648/mythicsim-forever-engine-go.git"
FOLDER = ("third_party", "mythicsim")
PIN_NAME = "pin.json"
TIMEOUT_S = 1800.0  # compilation Rust et téléchargement des paquets (réglage de l'outil)
GIT_TIMEOUT_S = 120.0  # une commande git : au-delà, GitHub est tenu pour injoignable
WINDOWS_HOST = "x86_64-pc-windows-gnu"  # chaîne GNU : compile sans les outils de compilation de Microsoft
_CHANNEL = re.compile(r'^\s*channel\s*=\s*"([^"]+)"', re.MULTILINE)


def mythicsim_dir(cache_dir: Path) -> Path:
    return cache_dir.joinpath(*FOLDER)


def pinned(cache_dir: Path) -> dict[str, Any] | None:
    """Épinglage en cours (`pin.json`) ; None si MythicSim n'a jamais été compilé."""
    path = mythicsim_dir(cache_dir) / PIN_NAME
    if not path.is_file():
        return None
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _out(runner: gitops.Runner, args: list[str], cwd: Path) -> str:
    timeout = GIT_TIMEOUT_S if args[0] == "git" else TIMEOUT_S
    try:
        return gitops._run(runner, args, cwd, timeout=timeout).stdout.strip()
    except OSError as exc:  # outil absent (git, rustup, cargo) : échec nommé, épinglage précédent gardé
        raise gitops.GitOpsError(
            f"`{args[0]}` introuvable ou en échec : {exc}", "installer Rust (rustup) et git"
        ) from exc


def go_revision(engine: Path) -> str:
    """Révision du fork Go épinglée par le moteur (`upstream/sources.json`, source `reference`)."""
    path = engine / "upstream" / "sources.json"
    doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    for source in doc.get("sources") or []:
        if source.get("id") == "reference" and source.get("pinned_revision"):
            return str(source["pinned_revision"])
    raise gitops.GitOpsError("MythicSim : révision du fork Go introuvable (upstream/sources.json, source reference).")


def toolchain(engine: Path, platform: str | None = None) -> str:
    """Chaîne Rust du moteur (`rust-toolchain.toml`), avec l'hôte GNU sous Windows."""
    m = _CHANNEL.search((engine / "rust-toolchain.toml").read_text(encoding="utf-8"))
    if m is None:
        raise gitops.GitOpsError("MythicSim : chaîne Rust introuvable (rust-toolchain.toml).")
    return f"{m.group(1)}-{WINDOWS_HOST}" if (platform or sys.platform) == "win32" else m.group(1)


def _sync_go(run: gitops.Runner, go: Path, revision: str) -> None:
    if not (go / ".git").is_dir():
        go.mkdir(parents=True, exist_ok=True)
        _out(run, ["git", "init", "-q", str(go)], go.parent)
        _out(run, ["git", "remote", "add", "origin", GO_REPO], go)
    _out(run, ["git", "fetch", "--depth", "1", "origin", revision], go)
    _out(run, ["git", "checkout", "-q", "--detach", "FETCH_HEAD"], go)


def update_mythicsim(
    cache_dir: Path, *, runner: gitops.Runner | None = None, now: datetime | None = None, platform: str | None = None
) -> dict[str, Any]:
    """Clone ou remise à jour du moteur et de son fork Go, puis compilation si le commit a changé ; rend l'épinglage
    (`status` : « compilé » ou « à jour »). GitOpsError si une commande échoue (l'épinglage précédent reste)."""
    run = runner or gitops.subprocess_runner
    root = mythicsim_dir(cache_dir)
    engine = root / "engine"
    if not (engine / ".git").is_dir():
        root.mkdir(parents=True, exist_ok=True)
        _out(run, ["git", "clone", "--depth", "1", REPO, str(engine)], root)
    else:
        _out(run, ["git", "fetch", "--depth", "1", "origin"], engine)
        _out(run, ["git", "reset", "--hard", "FETCH_HEAD"], engine)
    commit = _out(run, ["git", "rev-parse", "HEAD"], engine)
    revision = go_revision(engine)
    _sync_go(run, root / "go", revision)
    previous = pinned(cache_dir)
    if (previous and previous.get("commit") == commit and previous.get("go_revision") == revision
            and (root / str(previous.get("binary"))).is_file()):  # fmt: skip
        return {**previous, "status": "à jour"}
    committed_at = _out(run, ["git", "log", "-1", "--format=%cI"], engine)
    chain = toolchain(engine, platform)
    _out(run, ["rustup", "toolchain", "install", chain, "--profile", "minimal"], engine)
    _out(run, ["cargo", f"+{chain}", "build", "--locked", "--release"], engine)
    built = engine / "target" / "release" / "forever-engine.exe"
    if not built.is_file():
        built = engine / "target" / "release" / "forever-engine"
    if not built.is_file():
        raise gitops.GitOpsError(f"MythicSim : binaire compilé introuvable ({built}).")
    binary = f"forever-engine-{commit[:12]}.exe"
    shutil.copyfile(built, root / binary)
    pin = {
        "repo": REPO,
        "commit": commit,
        "committed_at": committed_at,
        "binary": binary,
        "sha256": hashlib.sha256((root / binary).read_bytes()).hexdigest(),
        "toolchain": chain,
        "go_repo": GO_REPO,
        "go_revision": revision,
        "built_at": (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "compilé",
    }
    (root / PIN_NAME).write_text(json.dumps(pin, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if previous and previous.get("binary") not in (None, binary):
        (root / str(previous["binary"])).unlink(missing_ok=True)  # un seul binaire épinglé à la fois
    return pin
