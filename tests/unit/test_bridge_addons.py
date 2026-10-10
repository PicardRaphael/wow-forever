"""Conversation « addons » (P06b, bloc F, décision 235) : ligne de `claude` sans shell, limitée au dossier (forme
relevée par la sonde 0.2 du 2026-10-10 : règles relatives au dossier de travail, `--restricted`) ; dossier refusé
s'il est celui d'un addon de la communauté ; sauvegarde avant le tour, commit git local après (sous-commandes
fermées, jamais de réseau), restauration qui déplace sans rien supprimer, déploiement qui copie sans rien supprimer.
Flux réels de la sonde 0.2 : `claude_stream_addons.jsonl` (travail dans une copie de RaphCompletionist) et
`claude_stream_addons_denied.jsonl` (quatre opérations hors du dossier refusées)."""

import subprocess
from pathlib import Path

import pytest
from conftest import FIXTURES, REPO_ROOT

from forever.bridge.addons import (
    ADDONS_TIMEOUT_S,
    GIT_SUBCOMMANDS,
    AddonsConfig,
    check_folder,
    commit,
    deploy,
    restore,
    snapshot,
)
from forever.bridge.agent import ADDONS_TOOLS, addons_argv, parse_stream
from forever.errors import ForeverError

STREAMS = FIXTURES / "bridge"


def addon(root: Path, name="RaphCompletionist") -> Path:
    folder = root / "Interface" / "AddOns" / name
    (folder / "Guides").mkdir(parents=True)
    (folder / f"{name}.toc").write_text("## Interface: 16001\nCore.lua\n", encoding="utf-8")
    (folder / "Core.lua").write_text("-- coeur\n", encoding="utf-8")
    (folder / "Guides" / "GuideList.lua").write_text("-- guides\n", encoding="utf-8")
    return folder


# --- Ligne de claude ----------------------------------------------------------------------------------------------


def test_addons_argv_is_limited_to_the_folder(tmp_path):
    argv = addons_argv(claude="claude", folder=tmp_path, mcp_config=tmp_path / "mcp.json", system_prompt="s",
                       session_id="sess", model="sonnet")  # fmt: skip
    assert ADDONS_TOOLS == ("Read", "Glob", "Grep", "Edit", "Write")
    assert argv[argv.index("--tools") + 1] == "Read,Glob,Grep,Edit,Write"
    assert argv[argv.index("--allowedTools") + 1] == "Read(./**),Edit(./**),Write(./**),Glob(./**),Grep(./**)"
    for option in ("--restricted", "--strict-mcp-config", "-p"):
        assert option in argv
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert argv[argv.index("--resume") + 1] == "sess" and argv[argv.index("--model") + 1] == "sonnet"
    text = " ".join(argv)
    for forbidden in ("Bash", "WebFetch", "WebSearch", "mcp__", "bypassPermissions", "--dangerously-skip-permissions",
                      "--plugin-dir"):  # fmt: skip
        assert forbidden not in text
    assert ADDONS_TIMEOUT_S == 600


def test_probe_streams_show_the_folder_limit():
    inside = parse_stream((STREAMS / "claude_stream_addons.jsonl").read_text(encoding="utf-8").splitlines(True))
    assert not inside.is_error and inside.denied == [] and "Write" in inside.tools
    outside = parse_stream((STREAMS / "claude_stream_addons_denied.jsonl").read_text(encoding="utf-8").splitlines(True))
    assert sorted(outside.denied) == ["Glob", "Grep", "Read", "Write"]
    assert "Bash" not in inside.tools + outside.tools


# --- Dossier ------------------------------------------------------------------------------------------------------


def test_check_folder(tmp_path):
    addons_dir = tmp_path / "Interface" / "AddOns"
    own = addon(tmp_path)
    for name in ("Questie", "Simulationcraft", "ForeverBridge"):
        (addons_dir / name).mkdir(parents=True)
        with pytest.raises(ForeverError):
            check_folder(addons_dir / name, addons_dir)
    with pytest.raises(ForeverError):
        check_folder(addons_dir, addons_dir)
    with pytest.raises(ForeverError):
        check_folder(REPO_ROOT, addons_dir)
    with pytest.raises(ForeverError):
        check_folder(tmp_path / "absent", addons_dir)
    check_folder(own, addons_dir)
    project = tmp_path / "Documents" / "RaphCompletionist"
    project.mkdir(parents=True)
    check_folder(project, addons_dir)


# --- Sauvegarde, commit, restauration, déploiement ----------------------------------------------------------------


def test_snapshot_copies_the_whole_folder(tmp_path):
    folder = addon(tmp_path)
    (folder / ".git").mkdir()
    (folder / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    copy = snapshot(AddonsConfig(folder), tmp_path / "cache", "20261010T120000Z")
    assert copy == tmp_path / "cache" / "bridge" / "addons" / "backups" / "20261010T120000Z"
    assert sorted(p.relative_to(copy).as_posix() for p in copy.rglob("*") if p.is_file()) == [
        "Core.lua", "Guides/GuideList.lua", "RaphCompletionist.toc",
    ]  # fmt: skip


class FakeGit:
    def __init__(self, status="M Core.lua\n?? New.lua\n"):
        self.calls: list[list[str]] = []
        self.status = status

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        sub = next(a for a in argv[3:] if not a.startswith("-") and "=" not in a)
        out = {"status": self.status, "rev-parse": "abc1234\n"}.get(sub, "")
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")


def subcommands(fake):
    return [next(a for a in argv[3:] if not a.startswith("-") and "=" not in a) for argv in fake.calls]


def test_commit_initializes_then_commits_with_the_local_identity(tmp_path):
    folder = addon(tmp_path)
    fake = FakeGit()
    info = commit(AddonsConfig(folder), "Conversation addons : corrige le chargement", run=fake)
    assert subcommands(fake) == ["init", "add", "status", "commit", "rev-parse"]
    assert all(argv[:3] == ["git", "-C", str(folder)] for argv in fake.calls)
    committed = next(argv for argv in fake.calls if "commit" in argv)
    assert "user.name=ForeverBridge" in committed and "user.email=forever-bridge@localhost" in committed
    assert committed[-2:] == ["-m", "Conversation addons : corrige le chargement"]
    assert (info.sha, info.files) == ("abc1234", 2)
    for argv in fake.calls:
        assert not {"push", "remote", "fetch", "pull", "clone"} & set(argv)
    assert set(subcommands(fake)) <= set(GIT_SUBCOMMANDS)


def test_no_commit_when_nothing_changed(tmp_path):
    folder = addon(tmp_path)
    (folder / ".git").mkdir()
    fake = FakeGit(status="")
    assert commit(AddonsConfig(folder), "rien", run=fake) is None
    assert subcommands(fake) == ["add", "status"]


def test_restore_moves_new_files_aside_and_never_unlinks(tmp_path, monkeypatch):
    folder = addon(tmp_path)
    cache = tmp_path / "cache"
    snapshot(AddonsConfig(folder), cache, "20261010T120000Z")
    (folder / "Core.lua").write_text("-- cassé\n", encoding="utf-8")
    (folder / "New.lua").write_text("-- nouveau\n", encoding="utf-8")

    def refuse(*args, **kwargs):
        raise AssertionError("suppression interdite")

    monkeypatch.setattr(Path, "unlink", refuse)
    monkeypatch.setattr("os.remove", refuse)
    monkeypatch.setattr("os.unlink", refuse)
    monkeypatch.setattr("shutil.rmtree", refuse)
    report = restore(AddonsConfig(folder), cache, None, "20261010T130000Z")
    assert report.stamp == "20261010T120000Z"
    assert (folder / "Core.lua").read_text(encoding="utf-8") == "-- coeur\n"
    assert not (folder / "New.lua").exists()
    aside = cache / "bridge" / "addons" / "set-aside" / "20261010T130000Z" / "New.lua"
    assert aside.read_text(encoding="utf-8") == "-- nouveau\n"
    assert report.set_aside == ["New.lua"] and "Core.lua" in report.restored


def test_deploy_copies_and_reports_missing_files(tmp_path):
    source = tmp_path / "Documents" / "RaphCompletionist"
    source.mkdir(parents=True)
    (source / "Core.lua").write_text("-- v2\n", encoding="utf-8")
    (source / "Same.lua").write_text("-- pareil\n", encoding="utf-8")
    installed = addon(tmp_path)
    (installed / "Same.lua").write_text("-- pareil\n", encoding="utf-8")
    report = deploy(AddonsConfig(source, installed))
    assert report.copied == ["Core.lua"]
    assert (installed / "Core.lua").read_text(encoding="utf-8") == "-- v2\n"
    assert sorted(report.missing) == ["Guides/GuideList.lua", "RaphCompletionist.toc"]
    assert (installed / "RaphCompletionist.toc").exists()
    assert deploy(AddonsConfig(source)).copied == []


def test_addons_module_runs_only_local_git():
    from test_network_boundary import imported_modules, network_uses

    path = REPO_ROOT / "forever" / "bridge" / "addons.py"
    assert "subprocess" in imported_modules(path) and network_uses(path) == set()
    text = path.read_text(encoding="utf-8")
    for call in ("shell=", "os.system", "os.popen", "Popen"):
        assert call not in text
    assert set(GIT_SUBCOMMANDS) == {"init", "add", "commit", "status", "diff", "log", "rev-parse"}
