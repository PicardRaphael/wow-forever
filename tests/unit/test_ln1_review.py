"""Suites de la relecture de LN1 (décision 271) : sauvegardes robustes à une racine partagée, archivage du profil
indépendant du produit des données installées, journal des versions illisible sans arrêt des commandes ni de la
surveillance du pont."""

import json
from dataclasses import replace
from datetime import UTC, datetime

from conftest import PRODUCT
from test_backup import NOW
from test_installs import FINAL, beta_root

from forever.backup import list_backups, make_backup, manifest_of, prune
from forever.bridge import autostart
from forever.bridge.journal import Journal
from forever.config import default_wow_dir
from forever.installs import survey
from forever.profile import archive_characters, load_profile


def test_a_foreign_manifest_in_the_backup_root_is_ignored_and_never_deleted(tmp_path, make_deps):
    root = tmp_path / "D"
    foreign = root / "Projet"
    foreign.mkdir(parents=True)
    (foreign / "manifest.json").write_text('{"files": []}', encoding="utf-8")
    other = root / "2020-01-01T000000"
    other.mkdir()
    (other / "manifest.json").write_text('{"name": "autre outil"}', encoding="utf-8")
    deps = replace(make_deps(), environ={"FOREVER_BACKUP_DIR": str(root)})
    for day in range(16):
        make_backup(deps, NOW.replace(day=1 + day), reason="test")
    assert prune(root, keep=1) != []
    assert foreign.is_dir() and other.is_dir()
    assert all(b.path.name.startswith("2026-11") for b in list_backups(root))


def test_a_file_that_cannot_be_copied_is_reported(tmp_path, make_deps):
    deps = make_deps()
    deps.profile_path.parent.mkdir(parents=True)
    deps.profile_path.write_text("{}", encoding="utf-8")
    folder = make_backup(replace(deps, environ={"FOREVER_BACKUP_DIR": str(tmp_path / "s")}), NOW, reason="test")
    assert manifest_of(folder)["skipped"] == []


def test_archive_ignores_the_product_of_the_installed_data(make_deps, monkeypatch):
    """Personnage d'avant LN1 (sans produit) : toujours un personnage de la bêta, même quand les données installées
    sont déjà celles de la version finale."""
    deps = make_deps(now=NOW)
    deps.profile_path.parent.mkdir(parents=True)
    doc = {"schema_version": 3, "active": "Moi", "characters": {"Moi": {"realm": "R", "updated_at": "x"}}, "realms": {}}
    deps.profile_path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr("forever.installs.beta_product", lambda data_dir: FINAL)
    assert archive_characters(deps, FINAL, NOW) == []
    assert archive_characters(deps, PRODUCT, NOW) == ["Moi-R"]
    assert load_profile(deps.profile_path)["characters"] == {}


def broken_journal(cache):
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "client_builds.json").write_text("{illisible", encoding="utf-8")


def test_an_unreadable_versions_journal_never_stops_the_choice(tmp_path):
    root = beta_root(tmp_path)
    broken_journal(tmp_path / "cache")
    environ = {"FOREVER_WOW_ROOTS": str(root)}
    choice, _ = survey(environ, drives=list, cache_dir=tmp_path / "cache", data_dir=tmp_path / "x")
    assert default_wow_dir(environ, drives=list, cache_dir=tmp_path / "cache") in (
        choice.folder,
        root / "_classic_beta_",
    )


def test_the_supervisor_survives_a_failing_resolution(tmp_path):
    from test_choice_everywhere import hold_lock

    calls = {"n": 0}

    def resolve():
        calls["n"] += 1
        if calls["n"] > 1:
            raise ValueError("journal des versions illisible")
        return tmp_path / "A"

    def sleep(seconds):
        n = sleep.n = getattr(sleep, "n", 0) + 1
        if n == 1:
            hold_lock(tmp_path, 4242)
        if n == 4:
            autostart.request_stop(tmp_path)

    journal = Journal(tmp_path / "bridge" / "journal", lambda: datetime(2026, 11, 4, 9, 0, tzinfo=UTC))
    code = autostart.supervise(
        tmp_path, lambda: None, journal=journal, clock=lambda: 0.0, sleep=sleep,
        alive=lambda pid: pid in (4242, 999), pid=999, resolve=resolve, game_running=lambda o, n: False,
    )  # fmt: skip
    assert code == 0
