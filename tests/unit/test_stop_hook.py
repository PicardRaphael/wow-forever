"""Hook de fin de tour (`.claude/hooks/test_on_stop.py`) : pas de relance sur un arbre déjà vert, budget de temps
sous le délai du hook (300 s dans `.claude/settings.json`) avec arrêt de tous les processus des tests."""

import importlib.util
import subprocess
import sys
import time

import pytest
from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location("test_on_stop", REPO_ROOT / ".claude" / "hooks" / "test_on_stop.py")
assert spec and spec.loader
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "a.py")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_fingerprint_is_stable_without_change(repo):
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert hook.fingerprint(repo) == hook.fingerprint(repo)


def test_fingerprint_follows_edits_untracked_files_and_commits(repo):
    seen = {hook.fingerprint(repo)}
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    seen.add(hook.fingerprint(repo))
    (repo / "b.py").write_text("y = 1\n", encoding="utf-8")
    seen.add(hook.fingerprint(repo))
    (repo / "b.py").write_text("y = 2\n", encoding="utf-8")
    seen.add(hook.fingerprint(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "suite")
    seen.add(hook.fingerprint(repo))
    assert len(seen) == 5


def test_green_tree_is_not_retested_until_it_changes(repo):
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert not hook.already_green(repo)
    hook.record_green(repo)
    assert hook.already_green(repo)
    (repo / "a.py").write_text("x = 3\n", encoding="utf-8")
    assert not hook.already_green(repo)


def test_green_record_lives_in_git_dir(repo):
    hook.record_green(repo)
    assert (
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        == ""
    )


def test_run_over_budget_is_stopped_with_its_children(tmp_path):
    marker = tmp_path / "survivant.txt"
    child = f"import time, pathlib; time.sleep(4); pathlib.Path({str(marker)!r}).write_text('vivant')"
    parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(60)"
    start = time.monotonic()
    assert hook.run_with_budget([sys.executable, "-c", parent], tmp_path, budget=1) is None
    assert time.monotonic() - start < 10
    time.sleep(5)
    assert not marker.exists()


def test_run_within_budget_returns_the_result(tmp_path):
    r = hook.run_with_budget([sys.executable, "-c", "print('ok')"], tmp_path, budget=30)
    assert r is not None and r.returncode == 0 and "ok" in r.stdout
