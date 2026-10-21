"""wowsims/forever compilé chez nous depuis un commit épinglé, sans aucune modification du code (décisions 293 et 294 ;
`tasks/plan-simulateurs.md` §6) : le projet ne publie pas de binaire. `forever sims update` (et la veille) copie le dépôt
public en lecture seule (clone superficiel en cache, `<cache>/third_party/wowsims/forever`), le remet sur son dernier
commit, génère le code protobuf (`protoc` et le greffon `protoc-gen-go` de la version du `go.mod`), compile
`cmd/wowsimcli` et épingle le binaire (`pin.json` : commit, date, empreinte, versions de Go et de protoc). Un commit
déjà compilé n'est pas recompilé ; un échec garde le binaire épinglé précédent. Réseau : git (dépôt public) et le
téléchargement des modules Go par `go` ; jamais d'envoi. Les commandes passent par l'exécuteur de `gitops`."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forever.pipeline import gitops

REPO = "https://github.com/wowsims/forever.git"
FOLDER = ("third_party", "wowsims")
PIN_NAME = "pin.json"
TIMEOUT_S = 1200.0  # compilation et téléchargement des modules (réglage de l'outil)
_PROTOBUF = re.compile(r"google\.golang\.org/protobuf\s+(v[0-9][^\s]*)")


def wowsims_dir(cache_dir: Path) -> Path:
    return cache_dir.joinpath(*FOLDER)


def pinned(cache_dir: Path) -> dict[str, Any] | None:
    """Épinglage en cours (`pin.json`) ; None si wowsims n'a jamais été compilé."""
    path = wowsims_dir(cache_dir) / PIN_NAME
    if not path.is_file():
        return None
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _out(runner: gitops.Runner, args: list[str], cwd: Path) -> str:
    return gitops._run(runner, args, cwd, timeout=TIMEOUT_S).stdout.strip()


def update_wowsims(
    cache_dir: Path, *, runner: gitops.Runner | None = None, now: datetime | None = None
) -> dict[str, Any]:
    """Clone ou remise à jour, puis compilation si le commit a changé ; rend l'épinglage (`status` : « compilé » ou
    « à jour »). GitOpsError si une commande échoue (l'épinglage précédent reste)."""
    run = runner or gitops.subprocess_runner
    root = wowsims_dir(cache_dir)
    clone = root / "forever"
    if not (clone / ".git").is_dir():
        root.mkdir(parents=True, exist_ok=True)
        _out(run, ["git", "clone", "--depth", "1", REPO, str(clone)], root)
    else:
        _out(run, ["git", "fetch", "--depth", "1", "origin"], clone)
        _out(run, ["git", "reset", "--hard", "FETCH_HEAD"], clone)
    commit = _out(run, ["git", "rev-parse", "HEAD"], clone)
    previous = pinned(cache_dir)
    if previous and previous.get("commit") == commit and (root / str(previous.get("binary"))).is_file():
        return {**previous, "status": "à jour"}
    committed_at = _out(run, ["git", "log", "-1", "--format=%cI"], clone)
    m = _PROTOBUF.search((clone / "go.mod").read_text(encoding="utf-8"))
    if m is None:
        raise gitops.GitOpsError("go.mod de wowsims/forever : version de google.golang.org/protobuf introuvable.")
    _out(run, ["go", "install", f"google.golang.org/protobuf/cmd/protoc-gen-go@{m.group(1)}"], clone)
    gopath = Path(_out(run, ["go", "env", "GOPATH"], clone))
    plugin = gopath / "bin" / "protoc-gen-go.exe"
    if not plugin.exists():
        plugin = gopath / "bin" / "protoc-gen-go"
    protos = sorted(p.relative_to(clone).as_posix() for p in (clone / "proto").glob("*.proto"))
    _out(
        run,
        [
            "protoc",
            "-I=./proto",
            f"--plugin=protoc-gen-go={plugin}",
            "--go_opt=Mgoogle/protobuf/descriptor.proto=google.golang.org/protobuf/types/descriptorpb",
            "--go_out=./sim/core",
            *(f"./{p}" for p in protos),
        ],
        clone,
    )
    binary = f"wowsimcli-{commit[:12]}.exe"
    _out(run, ["go", "build", "-o", str(root / binary), "--tags=with_db", "-ldflags=-s -w", "./cmd/wowsimcli"], clone)
    go = _out(run, ["go", "version"], clone).split()
    protoc = _out(run, ["protoc", "--version"], clone).split()
    pin = {
        "repo": REPO,
        "commit": commit,
        "committed_at": committed_at,
        "binary": binary,
        "sha256": hashlib.sha256((root / binary).read_bytes()).hexdigest(),
        "go": go[2] if len(go) > 2 else " ".join(go),
        "protoc": protoc[-1] if protoc else "",
        "built_at": (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "compilé",
    }
    (root / PIN_NAME).write_text(json.dumps(pin, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if previous and previous.get("binary") not in (None, binary):
        old = root / str(previous["binary"])
        old.unlink(missing_ok=True)  # un seul binaire épinglé à la fois
    return pin
