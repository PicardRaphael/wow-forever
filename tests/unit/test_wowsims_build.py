"""wowsims/forever compilé chez nous depuis un commit épinglé, sans modification du code (décisions 293 et 294, plan
des simulateurs §6) : clone superficiel en cache (`<cache>/third_party/wowsims/forever`), remise sur le dernier commit,
génération protobuf (`protoc` avec le greffon `protoc-gen-go` de la version de `google.golang.org/protobuf` du
`go.mod`), `go build --tags=with_db ./cmd/wowsimcli`, épinglage (`pin.json` : commit, date du commit, empreinte du
binaire, versions de Go et de protoc). Un commit déjà compilé n'est pas recompilé ; une commande en échec garde le
binaire épinglé précédent. Commandes simulées, aucun réseau ni compilateur."""

import hashlib
import json
import subprocess

import pytest

from forever.pipeline.gitops import GitOpsError
from forever.pipeline.wowsims_build import REPO, pinned, update_wowsims

COMMIT, NEXT = "a" * 40, "b" * 40
GOMOD = "module github.com/wowsims/forever\n\ngo 1.25.0\n\nrequire (\n\tgoogle.golang.org/protobuf v1.36.10\n)\n"


class Tools:
    """git, go et protoc simulés : le clone, les fichiers .proto et le binaire apparaissent comme sur le poste."""

    def __init__(self, root, commit=COMMIT, fail=None):
        self.root, self.commit, self.fail, self.calls = root, commit, fail, []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        self.calls.append(args)
        out = ""
        if self.fail and args[:2] == self.fail:
            return subprocess.CompletedProcess(args, 1, "", "échec simulé")
        clone = self.root / "third_party" / "wowsims" / "forever"
        if args[:2] == ["git", "clone"]:
            (clone / ".git").mkdir(parents=True)
            (clone / "proto").mkdir()
            for name in ("api.proto", "common.proto"):
                (clone / "proto" / name).write_text("syntax", encoding="utf-8")
            (clone / "go.mod").write_text(GOMOD, encoding="utf-8")
        elif args[:2] == ["git", "rev-parse"]:
            out = self.commit + "\n"
        elif args[:3] == ["git", "log", "-1"]:
            out = "2026-10-21T12:45:53+02:00\n"
        elif args[:2] == ["go", "version"]:
            out = "go version go1.27.0 windows/amd64\n"
        elif args[:3] == ["go", "env", "GOPATH"]:
            out = str(self.root / "gopath") + "\n"
        elif args[:2] == ["protoc", "--version"]:
            out = "libprotoc 36.0\n"
        elif args[:2] == ["go", "build"]:
            target = args[args.index("-o") + 1]
            from pathlib import Path

            Path(target).write_bytes(b"binaire " + self.commit.encode())
        return subprocess.CompletedProcess(args, 0, out, "")


def test_first_update_clones_builds_and_pins(tmp_path):
    tools = Tools(tmp_path)
    pin = update_wowsims(tmp_path, runner=tools)
    clone = ["git", "clone", "--depth", "1", REPO]
    assert tools.calls[0][: len(clone)] == clone
    install = next(c for c in tools.calls if c[:2] == ["go", "install"])
    assert install[-1] == "google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.10"  # version du go.mod
    protoc = next(c for c in tools.calls if c[0] == "protoc" and c[1] != "--version")
    assert any(a.startswith("--plugin=protoc-gen-go=") for a in protoc)
    assert {a.rsplit("/", 1)[-1] for a in protoc if a.endswith(".proto")} == {"api.proto", "common.proto"}
    build = next(c for c in tools.calls if c[:2] == ["go", "build"])
    assert "--tags=with_db" in build and build[-1] == "./cmd/wowsimcli"
    binary = tmp_path / "third_party" / "wowsims" / pin["binary"]
    assert pin["commit"] == COMMIT and pin["committed_at"] == "2026-10-21T12:45:53+02:00"
    assert pin["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()
    assert pin["go"] == "go1.27.0" and pin["protoc"] == "36.0" and pin["status"] == "compilé"
    assert pinned(tmp_path) == pin
    assert not any("push" in c or "commit" in c[:2] for c in tools.calls)  # lecture seule, aucun envoi


def test_same_commit_is_not_rebuilt(tmp_path):
    update_wowsims(tmp_path, runner=Tools(tmp_path))
    tools = Tools(tmp_path)
    pin = update_wowsims(tmp_path, runner=tools)
    assert [c[:2] for c in tools.calls if c[0] == "git"][:2] == [["git", "fetch"], ["git", "reset"]]
    assert not any(c[:2] == ["go", "build"] for c in tools.calls) and pin["status"] == "à jour"


def test_new_commit_is_rebuilt_and_repinned(tmp_path):
    first = update_wowsims(tmp_path, runner=Tools(tmp_path))
    pin = update_wowsims(tmp_path, runner=Tools(tmp_path, commit=NEXT))
    assert pin["commit"] == NEXT and pin["sha256"] != first["sha256"] and pin["status"] == "compilé"


def test_failed_build_keeps_the_previous_pin(tmp_path):
    first = update_wowsims(tmp_path, runner=Tools(tmp_path))
    with pytest.raises(GitOpsError):
        update_wowsims(tmp_path, runner=Tools(tmp_path, commit=NEXT, fail=["go", "build"]))
    assert pinned(tmp_path) == first
    assert json.loads((tmp_path / "third_party" / "wowsims" / "pin.json").read_text(encoding="utf-8")) == first
