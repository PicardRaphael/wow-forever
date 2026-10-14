"""Sauvegarde et restauration de ce qui n'est pas sur GitHub (LN1, bloc E, décision 271).

Tout s'écrit dans `tmp_path` : installation de fixture (`test_installs.make_root`), profil, cache et racine des
sauvegardes. Aucun disque réel : les disques, OneDrive et Documents sont injectés."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import PRODUCT
from test_installs import BETA_V, make_root

from forever.backup import (
    BACKUP_SUBDIR,
    KEEP,
    DriveInfo,
    backup_root,
    daily,
    list_backups,
    make_backup,
    manifest_of,
    prune,
    restore,
)
from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.provenance import validate_provenance

NOW = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
GiB = 1 << 30
SV_ACCOUNT = Path("WTF") / "Account" / "COMPTE" / "SavedVariables" / "ForeverLogger.lua"
SV_CHARACTER = Path("WTF") / "Account" / "COMPTE" / "Royaume" / "Perso" / "SavedVariables" / "ForeverBridge.lua"
CONFIG_WTF = Path("WTF") / "Config.wtf"


# --- Racine ----------------------------------------------------------------------------------------------------------


def drive(tmp_path, name, label="", *, free=100 * GiB, system=False):
    return DriveInfo(tmp_path / name, label, free, system)


def test_forever_backup_dir_comes_first(tmp_path):
    root, warning = backup_root(
        {"FOREVER_BACKUP_DIR": str(tmp_path / "ici")}, [drive(tmp_path, "F", "SAUVEGARDE")], None, tmp_path / "Doc"
    )
    assert (root, warning) == (tmp_path / "ici", None)


def test_a_drive_named_backup_comes_before_the_letters(tmp_path):
    drives = [
        drive(tmp_path, "C", "Windows", system=True),
        drive(tmp_path, "D", "RPKrypto"),
        drive(tmp_path, "E", "Divers"),
        drive(tmp_path, "F", "SAUVEGARDE"),
    ]
    assert backup_root({}, drives, tmp_path / "OneDrive", tmp_path / "Doc") == (tmp_path / "F" / BACKUP_SUBDIR, None)


def test_backup_in_english_is_recognized(tmp_path):
    drives = [drive(tmp_path, "C", system=True), drive(tmp_path, "D", "Data"), drive(tmp_path, "G", "My Backup")]
    assert backup_root({}, drives, None, tmp_path / "Doc")[0] == tmp_path / "G" / BACKUP_SUBDIR


def test_otherwise_the_first_non_system_drive_with_room(tmp_path):
    drives = [drive(tmp_path, "C", system=True), drive(tmp_path, "D", "Plein", free=GiB // 2), drive(tmp_path, "E")]
    assert backup_root({}, drives, None, tmp_path / "Doc") == (tmp_path / "E" / BACKUP_SUBDIR, None)


def test_otherwise_onedrive(tmp_path):
    drives = [drive(tmp_path, "C", system=True)]
    assert backup_root({}, drives, tmp_path / "OneDrive", tmp_path / "Doc") == (
        tmp_path / "OneDrive" / BACKUP_SUBDIR,
        None,
    )


def test_otherwise_documents_with_a_warning(tmp_path):
    root, warning = backup_root({}, [drive(tmp_path, "C", system=True)], None, tmp_path / "Doc")
    assert root == tmp_path / "Doc" / BACKUP_SUBDIR
    assert warning is not None and "disque système" in warning


# --- Sauvegarde ------------------------------------------------------------------------------------------------------


@pytest.fixture
def world(tmp_path, make_deps):
    """Installation, profil, réglages du pont, attente de mise à jour et racine des sauvegardes."""
    root = make_root(tmp_path / "jeu", [(PRODUCT, BETA_V)], {"_classic_beta_": (PRODUCT, "WowB.exe")})
    wow = root / "_classic_beta_"
    for rel, text in (
        (SV_ACCOUNT, "ForeverLoggerDB = {}\n"),
        (SV_CHARACTER, "ForeverBridgeDB = {}\n"),
        (CONFIG_WTF, 'SET advancedCombatLogging "1"\n'),
    ):
        (wow / rel).parent.mkdir(parents=True, exist_ok=True)
        (wow / rel).write_text(text, encoding="utf-8")
    deps = make_deps(wow_dir=wow)
    deps = replace(deps, environ={"FOREVER_BACKUP_DIR": str(tmp_path / "sauvegardes")})
    deps.profile_path.parent.mkdir(parents=True)
    deps.profile_path.write_text('{"schema_version": 3, "active": null, "characters": {}}', encoding="utf-8")
    (deps.cache_dir / "bridge").mkdir(parents=True)
    (deps.cache_dir / "bridge" / "config.json").write_text('{"model": "sonnet"}', encoding="utf-8")
    (deps.cache_dir / "bridge" / ".credentials.json").write_text('{"jeton": "secret"}', encoding="utf-8")
    project = tmp_path / "RaphCompletionist"
    (project / ".git").mkdir(parents=True)
    (project / "RaphCompletionist.lua").write_text("-- addon\n", encoding="utf-8")
    (project / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (project / ".credentials.json").write_text("{}", encoding="utf-8")
    (deps.cache_dir / "bridge" / "addons").mkdir()
    (deps.cache_dir / "bridge" / "addons" / "config.json").write_text(
        json.dumps({"source": str(project), "deploy": None}), encoding="utf-8"
    )
    (deps.cache_dir / "update" / "pending").mkdir(parents=True)
    (deps.cache_dir / "update" / "pending" / "measures-x.json").write_text("{}", encoding="utf-8")
    (deps.cache_dir / "update" / "state.json").write_text("{}", encoding="utf-8")
    (deps.cache_dir / "client_builds.json").write_text('{"schema_version": 2, "builds": []}', encoding="utf-8")
    return deps


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_backup_copies_everything_with_exact_fingerprints(world, tmp_path):
    folder = make_backup(world, NOW, reason="à la main")
    assert folder.parent == tmp_path / "sauvegardes" and folder.name == "2026-11-03T080000"
    manifest = manifest_of(folder)
    assert manifest["reason"] == "à la main"
    origins = {Path(f["origin"]): f for f in manifest["files"]}
    wow = world.wow_dir
    expected = [
        world.profile_path,
        wow / SV_ACCOUNT,
        wow / SV_CHARACTER,
        wow / CONFIG_WTF,
        world.cache_dir / "bridge" / "config.json",
        world.cache_dir / "bridge" / "addons" / "config.json",
        tmp_path / "RaphCompletionist" / "RaphCompletionist.lua",
        tmp_path / "RaphCompletionist" / ".git" / "HEAD",
        world.cache_dir / "update" / "pending" / "measures-x.json",
        world.cache_dir / "update" / "state.json",
        world.cache_dir / "client_builds.json",
    ]
    assert set(expected) <= set(origins)
    for origin in expected:
        entry = origins[origin]
        assert entry["sha256"] == sha(origin) == sha(folder / entry["path"]), origin
        assert entry["size"] == origin.stat().st_size
    assert origins[wow / SV_ACCOUNT]["kind"] == "wtf" and origins[wow / SV_ACCOUNT]["product"] == PRODUCT
    assert not [f for f in manifest["files"] if Path(f["origin"]).name == ".credentials.json"]
    assert not list(folder.rglob(".credentials.json"))


def test_fourteen_backups_are_kept(world, tmp_path):
    for day in range(KEEP + 1):
        make_backup(world, NOW + timedelta(days=day), reason="test")
    found = list_backups(tmp_path / "sauvegardes")
    assert len(found) == KEEP
    assert found[0].stamp == "2026-11-04T080000"  # la plus ancienne (03/11) retirée
    assert prune(tmp_path / "sauvegardes") == []


def test_a_partial_backup_is_never_listed(world, tmp_path):
    (tmp_path / "sauvegardes" / "2026-11-01T080000.partiel").mkdir(parents=True)
    make_backup(world, NOW, reason="test")
    assert [b.stamp for b in list_backups(tmp_path / "sauvegardes")] == ["2026-11-03T080000"]


# --- Restauration ----------------------------------------------------------------------------------------------------


def test_restore_refused_while_the_game_runs(world):
    make_backup(world, NOW, reason="test")
    with pytest.raises(InvalidArgumentError):
        restore(replace(world, game_running=lambda: True), None, confirm=True)


def test_restore_without_agreement_writes_nothing(world, tmp_path):
    make_backup(world, NOW, reason="test")
    (world.wow_dir / SV_ACCOUNT).write_text("abîmé", encoding="utf-8")
    plan = restore(world, None, confirm=False)
    assert not plan.applied and str(world.wow_dir / SV_ACCOUNT) in plan.written
    assert (world.wow_dir / SV_ACCOUNT).read_text(encoding="utf-8") == "abîmé"
    assert len(list_backups(tmp_path / "sauvegardes")) == 1


def test_restore_saves_the_current_state_first(world, tmp_path):
    make_backup(world, NOW, reason="test")
    (world.wow_dir / SV_ACCOUNT).write_text("abîmé", encoding="utf-8")
    world.profile_path.unlink()
    plan = restore(replace(world, now=lambda: NOW + timedelta(hours=1)), None, confirm=True)
    assert plan.applied and plan.before is not None
    found = list_backups(tmp_path / "sauvegardes")
    assert [b.reason for b in found] == ["test", "avant restauration"]
    assert (world.wow_dir / SV_ACCOUNT).read_text(encoding="utf-8") == "ForeverLoggerDB = {}\n"
    assert world.profile_path.is_file()


def test_restore_only_one_kind(world):
    make_backup(world, NOW, reason="test")
    (world.wow_dir / SV_ACCOUNT).write_text("abîmé", encoding="utf-8")
    world.profile_path.write_text("{}", encoding="utf-8")
    restore(replace(world, now=lambda: NOW + timedelta(hours=1)), None, only=frozenset({"profile"}), confirm=True)
    assert (world.wow_dir / SV_ACCOUNT).read_text(encoding="utf-8") == "abîmé"
    assert "schema_version" in world.profile_path.read_text(encoding="utf-8")


def test_saved_variables_follow_the_installation_when_the_game_moved(world, tmp_path):
    """Remise à zéro du PC : le même produit réinstallé ailleurs reçoit ses SavedVariables ; un compte absent est
    créé."""
    make_backup(world, NOW, reason="test")
    moved = make_root(tmp_path / "ailleurs", [(PRODUCT, BETA_V)], {"_classic_beta_": (PRODUCT, "WowB.exe")})
    target = replace(world, wow_dir=moved / "_classic_beta_", now=lambda: NOW + timedelta(hours=1))
    restore(target, None, only=frozenset({"wtf"}), confirm=True)
    assert (moved / "_classic_beta_" / SV_CHARACTER).read_text(encoding="utf-8") == "ForeverBridgeDB = {}\n"


def test_saved_variables_of_another_product_are_never_copied(world, tmp_path):
    make_backup(world, NOW, reason="test")
    other = make_root(
        tmp_path / "autre", [("wow_fictif_finale", "9.99.9.99999")], {"_fictif_": ("wow_fictif_finale", "WowF.exe")}
    )
    target = replace(world, wow_dir=other / "_fictif_", now=lambda: NOW + timedelta(hours=1))
    plan = restore(target, None, only=frozenset({"wtf"}), confirm=True)
    assert not (other / "_fictif_" / SV_ACCOUNT).exists()
    assert any(str(SV_ACCOUNT.name) in s for s in plan.skipped)


# --- Sauvegarde du jour ----------------------------------------------------------------------------------------------


def test_daily_backup_when_the_last_is_older_than_a_day(world, tmp_path):
    make_backup(world, NOW, reason="test")
    assert daily(world, NOW + timedelta(hours=23)) is None
    made = daily(world, NOW + timedelta(hours=25))
    assert made is not None and manifest_of(made)["reason"] == "sauvegarde du jour"


def test_no_daily_backup_while_the_game_runs(world):
    assert daily(replace(world, game_running=lambda: True), NOW) is None
    assert daily(replace(world, game_running=lambda: None), NOW) is None


def test_the_automatic_update_pass_makes_the_daily_backup(world, tmp_path):
    from forever.update import UpdateOptions, run_update

    options = UpdateOptions(auto=True, network=False, only=frozenset({"addons"}))
    run_update(replace(world, game_running=lambda: True), options, replay=lambda *a: {})
    assert list_backups(tmp_path / "sauvegardes") == []
    report = run_update(world, options, replay=lambda *a: {})
    assert len(list_backups(tmp_path / "sauvegardes")) == 1
    step = next(s for s in report["steps"] if s["name"] == "archivage")
    assert "backup" in step["data"]


# --- Commande --------------------------------------------------------------------------------------------------------


def test_cli_backup_list_and_restore(world, tmp_path, capsys):
    assert main(["backup", "--json"], world) == 0
    made = json.loads(capsys.readouterr().out)
    assert validate_provenance(made["provenance"]) == []
    assert Path(made["path"]).parent == tmp_path / "sauvegardes"
    assert main(["backup", "list", "--json"], world) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [b["stamp"] for b in listed["backups"]] == [Path(made["path"]).name]
    (world.wow_dir / SV_ACCOUNT).write_text("abîmé", encoding="utf-8")
    assert main(["backup", "restore"], world) == 2  # sans --yes ni accord : rien écrit
    assert (world.wow_dir / SV_ACCOUNT).read_text(encoding="utf-8") == "abîmé"
    later = replace(world, now=lambda: NOW + timedelta(hours=2))
    assert main(["backup", "restore", "--yes", "--json"], later) == 0
    assert (world.wow_dir / SV_ACCOUNT).read_text(encoding="utf-8") == "ForeverLoggerDB = {}\n"
