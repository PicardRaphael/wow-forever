"""Git du clone dédié (T08d, bloc F, décision 181).

Git réel dans `tmp_path` : dépôt nu `origin.git`, clone dédié, second clone qui joue « l'autre PC » ; configuration
git isolée (aucun réglage du poste) ; `gh` simulé. Aucun réseau. Chaque commande émise est journalisée et refusée si
elle force une poussée."""

import json
import subprocess

import pytest

from forever.pipeline.gitops import (
    commit_branch,
    delete_branch,
    ensure_clone,
    merge_ff_and_push,
    push,
    remote_has,
    subprocess_runner,
    sync_main,
    wait_ci,
)

FORBIDDEN = {"--force", "-f", "--force-with-lease", "--force-if-includes"}
WRITES = {"commit", "push", "merge", "switch", "checkout", "reset", "branch", "add", "rebase"}
VERSION = "1.60.1.70170"


def assert_not_forced(args):
    assert not FORBIDDEN & set(args), args
    assert not any(a.startswith("--force") for a in args), args
    assert not any(a.startswith("+") for a in args), args  # refspec forcée


class Recorder:
    """Runner des tests : git réel (exécuteur de production), `gh` répondu par `gh_reply`."""

    def __init__(self, gh_reply=None):
        self.calls = []
        self.gh_reply = gh_reply

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        assert_not_forced(args)
        self.calls.append(args)
        if args[0] == "gh":
            assert self.gh_reply is not None, f"gh inattendu : {args}"
            return self.gh_reply(args)
        assert args[0] == "git"
        return subprocess_runner(args, cwd, timeout)

    def git_writes(self):
        return [c for c in self.calls if c[0] == "git" and len(c) > 1 and c[1] in WRITES]


def git(cwd, *args):
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)
    return out.stdout.strip()


def done(stdout="", code=0):
    return subprocess.CompletedProcess(["gh"], code, stdout, "")


@pytest.fixture(autouse=True)
def isolated_git(tmp_path, monkeypatch):
    config = tmp_path / "gitconfig"
    config.write_text(
        "[user]\n\tname = Test\n\temail = test@example.invalid\n[init]\n\tdefaultBranch = main\n"
        "[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def write_revisions(repo, revision):
    path = repo / "forever" / "data" / VERSION / "revisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps({"revisions": [{"revision": r} for r in range(1, revision + 1)]}).encode("utf-8"))


@pytest.fixture
def origin(tmp_path):
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", str(bare), str(seed)], check=True, capture_output=True)
    write_revisions(seed, 1)
    (seed / "README.md").write_bytes(b"depot de test\n")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "amorce")
    git(seed, "push", "origin", "main")
    return bare


@pytest.fixture
def other(origin, tmp_path):
    path = tmp_path / "autre-pc"
    subprocess.run(["git", "clone", str(origin), str(path)], check=True, capture_output=True)
    return path


def other_pushes(other, change="note", revision=None):
    git(other, "pull", "--ff-only")
    if revision is not None:
        write_revisions(other, revision)
    (other / f"{change}.txt").write_bytes(change.encode("utf-8"))
    git(other, "add", ".")
    git(other, "commit", "-m", f"autre PC : {change}")
    git(other, "push", "origin", "main")
    return git(other, "rev-parse", "HEAD")


@pytest.fixture
def clone(origin, tmp_path):
    path = tmp_path / "cache" / "update" / "repo"
    ensure_clone(Recorder(), str(origin), path)
    return path


def origin_main(origin):
    return git(origin, "rev-parse", "main")


def ci_reply(sha, windows="success", runs=None):
    def reply(args):
        if args[1:3] == ["run", "list"]:
            listed = (
                runs
                if runs is not None
                else [
                    {
                        "databaseId": 7,
                        "headSha": sha,
                        "status": "completed",
                        "conclusion": "success",
                        "url": "https://ci/7",
                    }
                ]
            )
            return done(json.dumps(listed))
        if args[1:3] == ["run", "watch"]:
            return done(code=0 if windows == "success" else 1)
        if args[1:3] == ["run", "view"]:
            jobs = [
                {"name": "verify (ubuntu-24.04)", "conclusion": "success"},
                {"name": "verify (windows-latest)", "conclusion": windows},
            ]
            return done(json.dumps({"jobs": jobs}))
        raise AssertionError(args)

    return reply


def test_clone_then_sync_is_on_origin_main(origin, tmp_path):
    rec = Recorder()
    path = tmp_path / "repo"
    ensure_clone(rec, str(origin), path)
    assert any(c[1] == "clone" for c in rec.calls)
    result = sync_main(rec, path)
    assert result.ok and result.reason is None and not result.advanced
    assert result.origin_main == origin_main(origin) == git(path, "rev-parse", "HEAD")
    assert git(path, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    again = Recorder()
    ensure_clone(again, str(origin), path)
    assert not any(c[1] == "clone" for c in again.calls)


def test_sync_advances_after_the_other_pc_pushed(clone, other, origin):
    sha = other_pushes(other)
    result = sync_main(Recorder(), clone)
    assert result.ok and result.advanced and result.origin_main == sha
    assert git(clone, "rev-parse", "HEAD") == sha


def test_dirty_clone_is_refused_without_any_write(clone, other):
    other_pushes(other)
    (clone / "README.md").write_bytes(b"modifie a la main\n")
    rec = Recorder()
    result = sync_main(rec, clone)
    assert not result.ok and result.reason == "arbre de travail modifié"
    assert rec.git_writes() == []


def test_clone_on_another_branch_is_refused(clone):
    git(clone, "switch", "-c", "ailleurs")
    rec = Recorder()
    result = sync_main(rec, clone)
    assert not result.ok and "main" in result.reason
    assert rec.git_writes() == []


def test_remote_has_reads_origin_main_without_checkout(clone, other):
    rec = Recorder()
    assert remote_has(rec, clone, VERSION, None)
    assert remote_has(rec, clone, VERSION, 1)
    assert not remote_has(rec, clone, VERSION, 2)
    assert not remote_has(rec, clone, "1.60.1.79999", None)
    other_pushes(other, "r2", revision=2)
    sync_main(rec, clone)
    assert remote_has(rec, clone, VERSION, 2)
    assert rec.git_writes() == [["git", "merge", "--ff-only", "origin/main"]]


def full_path_until_ci(clone, windows="success"):
    rec = Recorder()
    assert sync_main(rec, clone).ok
    data = clone / "forever" / "data" / "1.60.1.79999" / "meta.json"
    data.parent.mkdir(parents=True)
    data.write_bytes(b"{}\n")
    branch = "data/1.60.1.79999-r1"
    sha = commit_branch(rec, clone, branch, ["forever/data/1.60.1.79999"], "Veille : 1.60.1.79999 r1 installée")
    assert sha == git(clone, "rev-parse", "HEAD")
    push(rec, clone, branch)
    rec.gh_reply = ci_reply(sha, windows)
    ci = wait_ci(rec, clone, branch, sha, 600, sleep=lambda _s: None)
    return rec, branch, sha, ci


def test_full_path_with_green_ci(clone, origin):
    rec, branch, sha, ci = full_path_until_ci(clone)
    assert ci.ok and ci.status == "success" and ci.url == "https://ci/7"
    assert ci.jobs == {"verify (ubuntu-24.04)": "success", "verify (windows-latest)": "success"}
    merged = merge_ff_and_push(rec, clone, branch)
    assert merged.ok and merged.reason is None
    assert origin_main(origin) == sha
    assert git(clone, "rev-parse", "--abbrev-ref", "HEAD") == "main" and git(clone, "rev-parse", "HEAD") == sha
    delete_branch(rec, clone, branch)
    assert git(origin, "branch", "--list", branch) == ""
    assert git(clone, "branch", "--list", branch) == ""
    for args in rec.calls:
        assert_not_forced(args)


def test_red_windows_job_stops_before_merge(clone, origin):
    before = origin_main(origin)
    _rec, branch, sha, ci = full_path_until_ci(clone, windows="failure")
    assert not ci.ok and ci.status == "failure" and ci.url == "https://ci/7"
    assert origin_main(origin) == before
    assert git(origin, "rev-parse", branch) == sha  # branche gardée, poussée


def test_ci_run_never_found_times_out(clone):
    rec = Recorder()
    ticks = iter(range(0, 10_000, 30))
    rec.gh_reply = ci_reply("x", runs=[])
    ci = wait_ci(rec, clone, "data/x", "abc", 120, sleep=lambda _s: None, clock=lambda: next(ticks))
    assert not ci.ok and ci.status in {"timeout", "not_found"}


def test_main_moved_between_ci_and_merge(clone, origin, other):
    rec, branch, sha, ci = full_path_until_ci(clone)
    assert ci.ok
    moved = other_pushes(other, "pendant-la-ci")
    merged = merge_ff_and_push(rec, clone, branch)
    assert not merged.ok and merged.reason == "main_moved"
    assert origin_main(origin) == moved  # rien n'a été écrasé
    assert git(origin, "rev-parse", branch) == sha


def test_production_runner_needs_no_shell(tmp_path):
    out = subprocess_runner(["git", "--version"], tmp_path)
    assert out.returncode == 0 and out.stdout.startswith("git version")
