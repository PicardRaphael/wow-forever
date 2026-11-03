"""Installations de la veille faites sur un autre PC (décision 295, anomalie du 2026-11-03) : 1.60.1.70707 r1 a été
installée le 31 octobre par le portable ; sa fiche « Mis à jour » n'existait que dans le cache du portable. Chaque
PC relit l'historique de `main` dans le clone de la veille (commits « Veille : <version> r<n> installée par … ») et
crée la fiche qui lui manque : `forever update status` et la carte « Mis à jour » la montrent, « Annuler » marche.
Seules les installations depuis la décision 295 (installation automatique, 2026-10-22) sont relues.

Dépôt git fabriqué dans `tmp_path` ; aucun réseau, aucun chiffre du jeu."""

import subprocess

import pytest

from forever.update import import_installed, update_dir
from forever.update_installed import list_installed, notices, save_installed


def git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


def commit(repo, message, date):
    import os

    (repo / "f.txt").write_text(message, encoding="utf-8")
    git(repo, "add", "f.txt")
    env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    git(repo, "commit", "-q", "-m", message, env=env)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def clone(tmp_path):
    repo = update_dir(tmp_path / "cache") / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "test")
    return repo


def test_an_install_made_on_another_pc_gets_its_record(clone, tmp_path):
    cache = tmp_path / "cache"
    commit(clone, "Veille : 1.60.1.70374 r6 installée par forever update (règle tenue)", "2026-10-15T10:00:00Z")
    sha = commit(clone, "Veille : 1.60.1.70707 r1 installée par forever update (règle tenue)", "2026-10-31T15:56:52Z")
    commit(clone, "Veille : délai maximal de chaque accès réseau", "2026-11-01T10:00:00Z")
    added = import_installed(cache)
    assert len(added) == 1
    (rec,) = list_installed(cache)
    assert (rec["version"], rec["revision"], rec["sha"], rec["state"]) == ("1.60.1.70707", 1, sha, "installée")
    assert rec["installed_at"].startswith("2026-10-31T15:56")
    assert rec["undo"] == f"forever update undo {rec['id']}"
    assert notices(cache) == [rec]  # carte « Mis à jour »
    assert import_installed(cache) == []  # relu une seule fois


def test_an_install_already_recorded_here_is_not_doubled(clone, tmp_path):
    cache = tmp_path / "cache"
    sha = commit(clone, "Veille : 1.60.1.70707 r2 installée par forever update (règle tenue)", "2026-11-03T13:00:00Z")
    save_installed(cache, {"id": "1.60.1.70707-r2-local", "version": "1.60.1.70707", "revision": 2, "sha": sha,
                           "state": "installée", "installed_at": "2026-11-03T13:00:00Z"})  # fmt: skip
    assert import_installed(cache) == []
    assert [r["id"] for r in list_installed(cache)] == ["1.60.1.70707-r2-local"]


def test_an_undone_install_is_not_shown_again(clone, tmp_path):
    cache = tmp_path / "cache"
    sha = commit(clone, "Veille : 1.60.1.70707 r1 installée par forever update (règle tenue)", "2026-10-31T15:56:52Z")
    commit(
        clone, "Veille : annulation de 1.60.1.70707-r1-x (retour à 1.60.1.70532 r3, décision 295)", "2026-11-01T09:00Z"
    )
    import_installed(cache)
    (rec,) = list_installed(cache)
    assert rec["sha"] == sha and rec["state"] == "annulée"
    assert notices(cache) == []


def test_without_a_clone_nothing_is_read(tmp_path):
    assert import_installed(tmp_path / "cache") == []


def test_status_shows_the_install_of_the_other_pc(clone, make_deps, capsys):
    from forever.cli import main

    commit(clone, "Veille : 1.60.1.70707 r1 installée par forever update (règle tenue)", "2026-10-31T15:56:52Z")
    deps = make_deps(cache_dir=clone.parents[1])
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr().out
    assert "Mis à jour : données 1.60.1.70707 r1 le 2026-10-31 15:56" in out
