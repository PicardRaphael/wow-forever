"""MythicSim compilé chez nous depuis un commit épinglé, sans modification du code (MS1, décision 301), comme
wowsims/forever : clone superficiel du moteur Rust (`<cache>/third_party/mythicsim/engine`), son fork Go à la révision
qu'il épingle lui-même (`upstream/sources.json`, `pinned_revision`) dans `<cache>/third_party/mythicsim/go` (rotations
et préréglages du même proto), compilation `cargo +<chaîne> build --locked --release` (chaîne de `rust-toolchain.toml`),
épinglage (`pin.json` : commit, date, empreinte du binaire, chaîne, révision du fork). Un commit déjà compilé n'est pas
recompilé ; une commande en échec garde le binaire épinglé précédent. Commandes simulées, aucun réseau ni compilateur."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from forever.pipeline.mythicsim_build import GO_REPO, REPO, pinned, update_mythicsim

from forever.pipeline.gitops import GitOpsError

COMMIT, NEXT = "a" * 40, "b" * 40
FORK = "c" * 40
SOURCES = {"schema_version": 1, "sources": [{"id": "reference", "repository": GO_REPO.removesuffix(".git"),
                                             "pinned_revision": FORK, "client_build": "1.60.1.70425"}]}  # fmt: skip


class Tools:
    """git, rustup et cargo simulés : le clone, ses fichiers et le binaire apparaissent comme sur le poste."""

    def __init__(self, root, commit=COMMIT, fail=None):
        self.root, self.commit, self.fail, self.calls = root, commit, fail, []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        self.calls.append(args)
        out = ""
        if self.fail and args[0] == self.fail[0] and self.fail[1] in args:
            return subprocess.CompletedProcess(args, 1, "", "échec simulé")
        engine = self.root / "third_party" / "mythicsim" / "engine"
        if args[:2] == ["git", "clone"]:
            (engine / ".git").mkdir(parents=True)
            (engine / "upstream").mkdir()
            (engine / "upstream" / "sources.json").write_text(json.dumps(SOURCES), encoding="utf-8")
            (engine / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.99.1"\n', encoding="utf-8")
        elif args[:2] == ["git", "init"]:
            (Path(args[-1]) / ".git").mkdir(parents=True)
        elif args[:2] == ["git", "rev-parse"]:
            out = (self.commit if Path(cwd) == engine else FORK) + "\n"
        elif args[:3] == ["git", "log", "-1"]:
            out = "2026-11-04T15:39:27+11:00\n"
        elif args[0] == "cargo" and "build" in args:
            exe = engine / "target" / "release"
            exe.mkdir(parents=True, exist_ok=True)
            for name in ("forever-engine.exe", "forever-engine"):
                (exe / name).write_bytes(b"moteur " + self.commit.encode())
        return subprocess.CompletedProcess(args, 0, out, "")


def test_first_update_clones_both_builds_and_pins(tmp_path):
    tools = Tools(tmp_path)
    pin = update_mythicsim(tmp_path, runner=tools)
    clone = ["git", "clone", "--depth", "1", REPO]
    assert tools.calls[0][: len(clone)] == clone
    fetch = next(c for c in tools.calls if c[:2] == ["git", "fetch"] and FORK in c)
    assert "--depth" in fetch  # fork Go à la révision épinglée par MythicSim lui-même
    remote = next(c for c in tools.calls if c[:3] == ["git", "remote", "add"])
    assert remote[-1] == GO_REPO
    build = next(c for c in tools.calls if c[0] == "cargo")
    assert build[1].startswith("+1.99.1") and "--locked" in build and "--release" in build
    root = tmp_path / "third_party" / "mythicsim"
    binary = root / pin["binary"]
    assert pin["commit"] == COMMIT and pin["committed_at"] == "2026-11-04T15:39:27+11:00"
    assert pin["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest() and pin["status"] == "compilé"
    assert pin["go_revision"] == FORK and pin["toolchain"].startswith("1.99.1")
    assert pinned(tmp_path) == pin
    assert not any("push" in c for c in tools.calls)  # lecture seule, aucun envoi


def test_same_commit_is_not_rebuilt(tmp_path):
    update_mythicsim(tmp_path, runner=Tools(tmp_path))
    tools = Tools(tmp_path)
    pin = update_mythicsim(tmp_path, runner=tools)
    assert not any(c[0] == "cargo" for c in tools.calls) and pin["status"] == "à jour"


def test_new_commit_is_rebuilt_and_only_one_binary_is_kept(tmp_path):
    first = update_mythicsim(tmp_path, runner=Tools(tmp_path))
    pin = update_mythicsim(tmp_path, runner=Tools(tmp_path, commit=NEXT))
    root = tmp_path / "third_party" / "mythicsim"
    assert pin["commit"] == NEXT and pin["sha256"] != first["sha256"]
    assert not (root / first["binary"]).exists() and (root / pin["binary"]).is_file()


def test_failed_build_keeps_the_previous_pin(tmp_path):
    first = update_mythicsim(tmp_path, runner=Tools(tmp_path))
    with pytest.raises(GitOpsError):
        update_mythicsim(tmp_path, runner=Tools(tmp_path, commit=NEXT, fail=["cargo", "build"]))
    assert pinned(tmp_path) == first
