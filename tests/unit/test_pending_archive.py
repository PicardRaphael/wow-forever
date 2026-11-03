"""Vieilles attentes de la bêta (anomalie du 2026-11-03) : une attente close (faite, périmée, rejetée) d'une version
plus ancienne que la version installée, ou créée avant l'installation de cette version (erreurs de passage, relectures
d'addons), est rangée dans `<cache>/update/pending/archive/` : ni `forever update status` ni `--all` ne la montrent
plus (dont les mentions du garde-fou de première écriture, supprimé par la décision 295). Une attente encore ouverte
reste affichée ; une attente rangée « rejetée » ou « faite » n'est jamais rouverte par un passage qui la recalcule.

Attentes fabriquées ; aucun chiffre du jeu."""

import json

from forever.update import archive_stale_pending, list_pending, record_pending, update_dir
from forever.update_installed import save_installed

INSTALLED = "1.60.1.70707"


def pending(cache, pending_id, state, version=None, created_at="2026-10-20T06:00:00Z", **extra):
    folder = update_dir(cache) / "pending"
    folder.mkdir(parents=True, exist_ok=True)
    doc = {"id": pending_id, "kind": "measures", "state": state, "version": version, "created_at": created_at, **extra}
    (folder / f"{pending_id}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def ids(cache):
    return [e["id"] for e in list_pending(cache)]


def installed_on(cache, at="2026-10-31T15:56:52Z"):
    save_installed(cache, {"id": "r1", "version": INSTALLED, "revision": 1, "sha": "abc", "state": "installée",
                           "installed_at": at})  # fmt: skip


def test_closed_entries_of_the_beta_are_archived(tmp_path):
    installed_on(tmp_path)
    reason = "garde-fou : première écriture git de `forever update --auto`"
    pending(tmp_path, "measures-1.60.1.70338-a", "périmée", "1.60.1.70338", reasons=[reason])
    pending(tmp_path, "hotfixes-1.60.1.70425", "périmée", "1.60.1.70425")
    pending(tmp_path, "1.60.1.70450-r10-b", "rejetée", "1.60.1.70450")
    pending(tmp_path, "pass-error-20261020060725", "périmée", kind="pass_error")
    pending(tmp_path, "addon-Questie-1", "faite", "11.38.0 Forever-v27", kind="addon_data")
    archived = archive_stale_pending(tmp_path, INSTALLED)
    assert len(archived) == 5
    assert ids(tmp_path) == []
    assert (update_dir(tmp_path) / "pending" / "archive" / "hotfixes-1.60.1.70425.json").is_file()  # gardée, rangée


def test_open_entries_and_recent_closed_ones_stay(tmp_path):
    installed_on(tmp_path)
    pending(tmp_path, "measures-1.60.1.70338-open", "en_attente", "1.60.1.70338")
    pending(tmp_path, "pass-error-20261103124223", "faite", kind="pass_error", created_at="2026-11-03T12:43:06Z")
    pending(tmp_path, "hotfixes-1.60.1.70707", "faite", INSTALLED)
    assert archive_stale_pending(tmp_path, INSTALLED) == []
    assert len(ids(tmp_path)) == 3


def test_without_install_date_only_older_versions_are_archived(tmp_path):
    pending(tmp_path, "hotfixes-1.60.1.70425", "périmée", "1.60.1.70425")
    pending(tmp_path, "pass-error-20261020060725", "périmée", kind="pass_error")
    assert archive_stale_pending(tmp_path, INSTALLED) == ["hotfixes-1.60.1.70425"]


def test_an_archived_rejected_entry_is_never_reopened(tmp_path):
    installed_on(tmp_path)
    pending(tmp_path, "1.60.1.70450-r10-b", "rejetée", "1.60.1.70450")
    archive_stale_pending(tmp_path, INSTALLED)
    record_pending(tmp_path, {"id": "1.60.1.70450-r10-b", "kind": "install_revision", "version": "1.60.1.70450"})
    assert ids(tmp_path) == []


def test_status_all_no_longer_shows_the_beta(tmp_path, make_deps, capsys):
    from forever.cli import main

    deps = make_deps(cache_dir=tmp_path)
    pending(tmp_path, "measures-1.60.1.70338-a", "périmée", "1.60.1.70338", reasons=["garde-fou : première écriture"])
    assert main(["update", "status", "--all"], deps) == 0
    out = capsys.readouterr().out
    assert "garde-fou" not in out and "measures-1.60.1.70338-a" not in out
