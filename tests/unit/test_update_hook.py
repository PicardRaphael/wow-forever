"""Démarrage de session et `forever update` (T08d, bloc G, décision 180).

Au `SessionStart` : archivage des fichiers du client, puis passage `forever update --auto` **détaché** (`spawn`
simulé) si aucun verrou n'est vivant et que le dernier passage a plus de 6 h. La ligne de démarrage dit, sans
réseau et sur une seule ligne, le passage en cours, les attentes et le `git pull` à faire quand `main` distant
(relevé par le clone dédié) a avancé. Git réel dans `tmp_path` pour ce dernier point (configuration isolée)."""

import subprocess
from datetime import timedelta

import pytest
from conftest import NOW

from forever import hooks
from forever.update import acquire_lock, record_pending, save_report

HOME = {"FOREVER_HOME": "x"}


class Spawn:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, args):
        self.calls.append(list(args))
        if self.fail:
            raise OSError("lancement simulé en échec")


def report(finished_at="2026-09-27T11:00:00Z", origin_main=None):
    return {
        "schema_version": 1,
        "started_at": finished_at,
        "finished_at": finished_at,
        "steps": [],
        "verdicts": [],
        "written": [],
        "pending": [],
        "origin_main": origin_main,
        "provenance": {},
    }


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "World of Warcraft" / "_classic_beta_"
    (root / "Logs").mkdir(parents=True)
    return root


@pytest.fixture
def archived(monkeypatch):
    calls = []

    def fake(deps, **_kwargs):
        calls.append(deps.wow_dir)
        from forever.archive import ArchiveResult

        return ArchiveResult([], [], None)

    monkeypatch.setattr("forever.archive.archive_client_files", fake)
    return calls


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


def git(cwd, *args):
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)
    return out.stdout.strip()


# --- Lancement du passage ------------------------------------------------------------------------------------


def test_first_session_archives_and_spawns_once(make_deps, wow, archived):
    deps = make_deps(wow_dir=wow)
    spawn = Spawn()
    hooks.update_kickoff(deps, HOME, spawn)
    assert archived == [wow]
    assert len(spawn.calls) == 1
    assert "update" in spawn.calls[0] and "--auto" in spawn.calls[0]


def test_no_spawn_while_a_lock_is_alive(make_deps, wow, archived):
    deps = make_deps(wow_dir=wow)
    assert acquire_lock(deps, "forever update --auto") is None
    spawn = Spawn()
    hooks.update_kickoff(deps, HOME, spawn)
    assert spawn.calls == [] and archived == [wow]


def test_no_spawn_after_a_recent_pass_but_one_after_six_hours(make_deps, wow, archived):
    deps = make_deps(wow_dir=wow)
    save_report(deps.cache_dir, report(finished_at="2026-09-27T11:00:00Z"))  # 1 h avant NOW
    spawn = Spawn()
    hooks.update_kickoff(deps, HOME, spawn)
    assert spawn.calls == []
    later = make_deps(wow_dir=wow, now=NOW + timedelta(hours=6))
    hooks.update_kickoff(later, HOME, spawn)
    assert len(spawn.calls) == 1


def test_no_spawn_without_client_or_offline(make_deps, wow, archived):
    spawn = Spawn()
    hooks.update_kickoff(make_deps(wow_dir=None), HOME, spawn)
    hooks.update_kickoff(make_deps(wow_dir=wow), {**HOME, "FOREVER_OFFLINE": "1"}, spawn)
    assert spawn.calls == []


def test_a_failing_spawn_never_breaks_the_line(make_deps, wow, archived, tmp_path):
    deps = make_deps(wow_dir=wow)
    repo = tmp_path / "repo"
    repo.mkdir()
    out = hooks.session_start_output({"cwd": str(repo)}, deps, HOME, repo_root=repo, spawn=Spawn(fail=True))
    assert out is not None and "WoW Forever" in out["systemMessage"]


# --- Ligne de démarrage ---------------------------------------------------------------------------------------


@pytest.fixture
def history(tmp_path):
    """Dépôt git de trois commits c0 → c1 → c2 ; la session est sur c1."""
    repo = tmp_path / "session"
    repo.mkdir()
    git(repo, "init", "-q")
    shas = []
    for i in range(3):
        (repo / "f.txt").write_text(str(i), encoding="utf-8")
        git(repo, "add", "f.txt")
        git(repo, "commit", "-q", "-m", f"c{i}")
        shas.append(git(repo, "rev-parse", "HEAD"))
    git(repo, "reset", "-q", "--hard", shas[1])
    return repo, shas


def test_line_says_nothing_without_state(make_deps, history):
    repo, _ = history
    assert hooks.update_line(make_deps(), repo) is None


def test_line_counts_the_pending_entries(make_deps, history):
    repo, _ = history
    deps = make_deps()
    record_pending(
        deps.cache_dir, {"id": "1.60.1.79999-r1-aaaaaaaaaaaa", "kind": "install_version", "action": "attente"}
    )
    line = hooks.update_line(deps, repo)
    assert line is not None and "1 attente : `forever update status`" in line


def test_line_proposes_a_pull_when_remote_main_moved_ahead(make_deps, history):
    repo, (c0, c1, c2) = history
    deps = make_deps()
    save_report(deps.cache_dir, report(origin_main=c2))
    line = hooks.update_line(deps, repo)
    assert line is not None and "main distant a avancé : `git pull`" in line
    for known in (c1, c0):  # déjà dans la session : rien à tirer
        save_report(deps.cache_dir, report(origin_main=known))
        assert hooks.update_line(deps, repo) is None


def written(approved, summary="fiches PvP : Warrior, 1 sort modifié"):
    doc = report()
    doc["written"] = [{"version": "1.60.1.79999", "revision": 1, "approved": approved, "summary": summary}]
    return doc


def test_line_names_an_install_alone_with_its_summary(make_deps, history):
    repo, _ = history
    deps = make_deps()
    save_report(deps.cache_dir, written(False))
    line = hooks.update_line(deps, repo)
    assert line == "mise à jour : 1.60.1.79999 r1 installée seule (fiches PvP : Warrior, 1 sort modifié)"
    save_report(deps.cache_dir, written(True, summary=""))
    assert hooks.update_line(deps, repo) == "mise à jour : 1.60.1.79999 r1 installée"


def test_line_names_the_hotfixes_to_read(make_deps, history):
    repo, _ = history
    deps = make_deps()
    entry = {"id": "hotfixes-1.60.1.79999", "kind": "hotfixes_unread", "action": "attente", "version": "1.60.1.79999"}
    record_pending(deps.cache_dir, entry)
    line = hooks.update_line(deps, repo)
    assert line == "1.60.1.79999 : correctifs du serveur à lire (lancer le jeu sur ce build)"


def test_status_shows_the_summary_and_the_self_clearing_wait(make_deps, capsys):
    from forever.cli import main

    deps = make_deps()
    record_pending(
        deps.cache_dir,
        {"id": "hotfixes-1.60.1.79999", "kind": "hotfixes_unread", "action": "attente", "version": "1.60.1.79999"},
    )
    record_pending(
        deps.cache_dir,
        {
            "id": "1.60.1.79999-r1-aaaaaaaaaaaa",
            "kind": "install_version",
            "action": "attente",
            "version": "1.60.1.79999",
            "summary": {"pvp_dr": {"sentence": "fiches PvP : Warrior, 1 sort modifié", "counts": {}}},
        },
    )
    save_report(deps.cache_dir, written(False, summary="fiches PvP : Druid, 2 sorts modifiés"))
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr().out
    assert "fiches PvP : Warrior, 1 sort modifié" in out
    assert "se lève seule" in out and "lancer le jeu sur ce build" in out
    assert "1.60.1.79999 r1 installée seule (fiches PvP : Druid, 2 sorts modifiés)" in out


def test_line_says_a_run_is_in_progress(make_deps, history):
    repo, _ = history
    deps = make_deps()
    assert acquire_lock(deps, "forever update --auto") is None
    line = hooks.update_line(deps, repo)
    assert line is not None and "en cours" in line


def test_session_start_stays_on_one_line(make_deps, wow, archived, history):
    repo, (_, _, c2) = history
    deps = make_deps(wow_dir=wow)
    save_report(deps.cache_dir, report(origin_main=c2))
    record_pending(
        deps.cache_dir, {"id": "1.60.1.79999-r1-aaaaaaaaaaaa", "kind": "install_version", "action": "attente"}
    )
    out = hooks.session_start_output({"cwd": str(repo)}, deps, HOME, repo_root=repo, spawn=Spawn())
    assert out is not None
    line = out["systemMessage"]
    assert "\n" not in line and "1 attente" in line and "git pull" in line
    assert out["hookSpecificOutput"]["additionalContext"] == line


def test_nothing_runs_in_the_bridge_conversation(make_deps, wow, archived):
    """P06a, bloc C : dans la conversation « jeu » lancée par le pont (FOREVER_BRIDGE=1), le hook de démarrage
    n'archive rien et ne lance pas `forever update`, même sans FOREVER_OFFLINE."""
    spawn = Spawn()
    hooks.update_kickoff(make_deps(wow_dir=wow), {**HOME, "FOREVER_BRIDGE": "1"}, spawn)
    assert archived == [] and spawn.calls == []


# --- DBCache.bin d'un nouveau build archivé (DON14, décision 227) ------------------------------------------------


@pytest.fixture
def archived_dbcache(monkeypatch, tmp_path):
    def fake(deps, **_kwargs):
        from forever.archive import ArchivedCopy, ArchiveResult

        copy = ArchivedCopy("dbcache", "79999", tmp_path / "DBCache.bin", "0" * 64, 1, "", "", True)
        return ArchiveResult([copy], [], None)

    monkeypatch.setattr("forever.archive.archive_client_files", fake)


def test_a_new_dbcache_copy_spawns_a_pass_even_within_six_hours(make_deps, wow, archived_dbcache):
    deps = make_deps(wow_dir=wow)
    save_report(deps.cache_dir, report(finished_at="2026-09-27T11:00:00Z"))  # 1 h avant NOW
    spawn = Spawn()
    hooks.update_kickoff(deps, HOME, spawn)
    assert len(spawn.calls) == 1 and "--auto" in spawn.calls[0]


def test_a_new_dbcache_copy_never_spawns_over_a_live_lock(make_deps, wow, archived_dbcache):
    deps = make_deps(wow_dir=wow)
    assert acquire_lock(deps, "forever update --auto") is None
    spawn = Spawn()
    hooks.update_kickoff(deps, HOME, spawn)
    assert spawn.calls == []


def test_launch_pass_ignores_the_six_hours_but_not_the_lock(make_deps):
    from forever.update import launch_pass

    deps = make_deps()
    save_report(deps.cache_dir, report(finished_at="2026-09-27T11:00:00Z"))
    spawn = Spawn()
    assert launch_pass(deps.cache_dir, deps.now(), spawn) is True
    assert len(spawn.calls) == 1 and spawn.calls[0][-4:] == ["forever", "update", "--auto", "--json"]
    assert acquire_lock(deps, "forever update --auto") is None
    assert launch_pass(deps.cache_dir, deps.now(), spawn) is False
    assert len(spawn.calls) == 1


def test_the_self_clearing_hint_says_when_the_client_writes_dbcache():
    from forever.update import SELF_CLEARING_HINT

    assert "lancer le jeu sur ce build" in SELF_CLEARING_HINT and "déconnexion" in SELF_CLEARING_HINT
