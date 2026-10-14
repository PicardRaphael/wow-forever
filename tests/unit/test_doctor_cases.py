"""Cas réels de `forever doctor` (LN1, bloc D) : un problème par test, constat et correction exacts. Cas tirés de la
remise à zéro du PC du 12 octobre et des décisions 241 (environnement du projet incomplet) et 257 (tâches, pont)."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest
from conftest import NOW
from test_doctor import World

from forever.bridge.journal import Journal
from forever.bridge.slots import slot_name
from forever.spawn import record_environment


@pytest.fixture
def world(tmp_path, make_deps):
    return World(tmp_path, make_deps)


def test_base_python_without_packages(world):
    check = world.checks(python_check=lambda: "ModuleNotFoundError: No module named 'yaml'")["env.python"]
    assert check.status == "fail" and "No module named 'yaml'" in check.finding
    assert "uv sync" in check.fix


def test_environment_state_left_by_a_task(world):
    record_environment(world.deps.cache_dir / "bridge", "ModuleNotFoundError: No module named 'yaml'", "py", "x")
    check = world.checks()["env.state"]
    assert check.status == "fail" and "uv sync" in check.fix


def test_environment_behind_uv_lock(world):
    check = world.checks(uv_check=lambda repo: (False, "Would install 3 packages"))["env.uv"]
    assert check.status == "fail" and "uv sync" in check.fix


def test_forever_wow_dir_points_to_the_old_folder(world):
    world.environ["FOREVER_WOW_DIR"] = str(world.tmp / "ancien" / "_classic_beta_")
    check = world.checks()["wow.env"]
    assert check.status == "fail" and str(world.wow) in check.finding
    assert "install_plugin.ps1" in check.fix


def test_an_unknown_product_is_flagged_with_the_adopt_command(world):
    folder = world.root / "_fictif_"
    folder.mkdir()
    (folder / "WowF.exe").write_bytes(b"")
    (folder / ".flavor.info").write_bytes(b"Product Flavor!STRING:0\nwow_fictif_inconnu\n")
    check = world.checks()["wow.unknown"]
    assert check.status == "warn" and "wow_fictif_inconnu" in check.finding
    assert check.fix == f"forever wow adopt {folder}"


def test_bridge_task_missing(world):
    del world.tasks["WoW Forever - pont"]
    check = world.checks()["tasks.bridge"]
    assert check.status == "fail" and check.fix == "uv run forever bridge autostart install"


def test_bridge_task_forcing_an_old_folder(world):
    world.tasks["WoW Forever - pont"] = world.task(
        f'-m forever.bridge.autostart --wow-dir "{world.tmp / "ancien"}" --cache-dir x'
    )
    check = world.checks()["tasks.bridge"]
    assert check.status == "fail" and "à recréer" in check.finding
    assert check.fix == "uv run forever bridge autostart install"


def test_update_task_missing(world):
    del world.tasks["WoW Forever - mise à jour"]
    check = world.checks()["tasks.update"]
    assert check.status == "fail" and "install_update_task.ps1" in check.fix


def test_task_interpreter_gone(world):
    world.pythonw.unlink()
    check = world.checks()["tasks.bridge"]
    assert check.status == "fail" and str(world.pythonw) in check.finding


def test_gh_missing(world):
    check = world.checks(gh_version=lambda: None)["gh"]
    assert check.status == "fail" and check.fix == "winget install --id GitHub.cli"


def test_gh_without_token(world):
    check = world.checks(gh_token=lambda: False)["gh"]
    assert check.status == "fail" and check.fix == "gh auth login"


def test_claude_session_expired_in_the_bridge_journal(world):
    journal = Journal(world.deps.cache_dir / "bridge" / "journal", lambda: NOW - timedelta(hours=3))
    journal.write("reply", id="m1", conversation="jeu", seconds=4.0)
    later = Journal(world.deps.cache_dir / "bridge" / "journal", lambda: NOW - timedelta(hours=1))
    later.write("error", where="conversation", error="OAuth session expired. Please run /login.")
    check = world.checks()["claude"]
    assert check.status == "fail" and "expirée" in check.finding
    assert "/login" in check.fix


def test_an_old_auth_error_followed_by_a_reply_is_fine(world):
    Journal(world.deps.cache_dir / "bridge" / "journal", lambda: NOW - timedelta(hours=3)).write(
        "error", where="conversation", error="OAuth session expired"
    )
    Journal(world.deps.cache_dir / "bridge" / "journal", lambda: NOW - timedelta(hours=1)).write(
        "reply", id="m2", conversation="jeu", seconds=3.0
    )
    assert world.checks()["claude"].status == "ok"


def test_claude_logged_out(world):
    check = world.checks(claude_auth=lambda: {"loggedIn": False, "authMethod": None})["claude"]
    assert check.status == "fail" and "/login" in check.fix


def test_claude_missing(world):
    check = world.checks(claude_path=lambda: None)["claude"]
    assert check.status == "fail"


def test_forever_logger_missing(world):
    import shutil

    shutil.rmtree(world.wow / "Interface" / "AddOns" / "ForeverLogger")
    check = world.checks()["addons.logger"]
    assert check.status == "fail" and "scripts/install_addon.py" in check.fix


def test_forever_bridge_differs_from_the_repository(world):
    toc = world.wow / "Interface" / "AddOns" / "ForeverBridge" / "ForeverBridge.toc"
    toc.write_text(toc.read_text(encoding="utf-8") + "\n-- modifié\n", encoding="utf-8")
    check = world.checks()["addons.bridge"]
    assert check.status == "fail" and "ForeverBridge.toc" in check.finding
    assert "forever bridge install" in check.fix


def test_bridge_reserve_with_199_slots(world):
    import shutil

    shutil.rmtree(world.wow / "Interface" / "AddOns" / slot_name(200))
    check = world.checks()["addons.bridge"]
    assert check.status == "fail" and "199" in check.finding


def test_profile_missing_with_a_backup(world):
    world.deps.profile_path.unlink()
    check = world.checks()["profile"]
    assert check.status == "fail" and "forever backup restore" in check.fix


def test_profile_missing_without_backup(world):
    import shutil

    world.deps.profile_path.unlink()
    shutil.rmtree(world.tmp / "sauvegardes")
    check = world.checks()["profile"]
    assert check.status == "fail" and "forever profile import" in check.fix


def test_antivirus_is_unknown(world):
    check = world.checks()["antivirus"]
    assert check.status == "unknown" and "docs/LANCEMENT.md" in check.fix


def test_backups_on_the_system_drive(world):
    drive = world.tmp.drive or ""
    check = world.checks(system_drive=drive)["backup"]
    assert check.status == "warn" and "FOREVER_BACKUP_DIR" in check.fix


def test_no_backup_yet(world):
    import shutil

    shutil.rmtree(world.tmp / "sauvegardes")
    check = world.checks()["backup"]
    assert check.status == "warn" and check.fix == "uv run forever backup"


def test_backup_too_old(world):
    check = run_at(world, NOW + timedelta(days=3))["backup"]
    assert check.status == "warn"


def run_at(world, when):
    from forever.doctor import run_checks

    return {c.id: c for c in run_checks(replace(world.deps, now=lambda: when), world.probes)}


def test_no_recent_combat_log(world):
    world.age_log(timedelta(days=10))
    check = world.checks()["combatlog"]
    assert check.status == "warn" and "ForeverLogger" in check.fix


def test_combat_log_without_advanced_logging(world):
    world.log.write_text(
        world.log.read_text(encoding="utf-8").replace("ADVANCED_LOG_ENABLED,1", "ADVANCED_LOG_ENABLED,0")
    )
    world.age_log(timedelta(days=1))
    assert world.checks()["combatlog"].status == "fail"


def test_bridge_supervisor_stopped(world):
    check = world.checks(supervisor_pid=lambda cache: None)["bridge.running"]
    assert check.status == "warn" and "schtasks /Run" in check.fix


def test_environment_error_in_the_bridge_journal(world):
    Journal(world.deps.cache_dir / "bridge" / "journal", lambda: NOW - timedelta(hours=2)).write(
        "autostart_env_error", error="ModuleNotFoundError: No module named 'yaml'", next_in_s=300
    )
    check = world.checks()["bridge.journal"]
    assert check.status == "fail" and "uv sync" in check.fix


def test_a_third_party_saved_variables_bridge_is_reported_as_information(world):
    (world.wow / "Interface" / "AddOns" / "ForeverSVBridge").mkdir()
    check = world.checks()["info.sv_bridge"]
    assert check.status == "info" and "ForeverSVBridge" in check.finding


def test_json_of_a_check(world):
    check = world.checks(gh_version=lambda: None)["gh"]
    assert json.loads(json.dumps(check.as_dict())) == {
        "id": "gh",
        "status": "fail",
        "finding": check.finding,
        "fix": "winget install --id GitHub.cli",
        "certainty": "certain",
    }
