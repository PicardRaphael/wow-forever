"""Tâche planifiée de mise à jour (décision 226) : « WoW Forever - mise à jour » lance `forever update --auto` comme
le hook de démarrage (même verrou, même journal `<cache>/update/run-<horodatage>.log`), chaque jour à 08:00, dès que
possible si l'heure est passée, seulement avec le réseau, 2 h au plus ; elle remplace l'ancienne tâche « veille
locale » (`forever watch --report`, qui ne faisait que regarder).

Le contenu de la tâche est vérifié sans l'installer (`-Print`) ; les scripts PowerShell sont en UTF-8 avec BOM, sans
quoi Windows PowerShell 5.1 les lit en ANSI et casse les accents."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import NOW, REPO_ROOT

from forever import update_task
from forever.cli import main

SCRIPTS = REPO_ROOT / "scripts"
UPDATE_SCRIPT = SCRIPTS / "install_update_task.ps1"
DOCS = [REPO_ROOT / "docs" / "USAGE.md", REPO_ROOT / "docs" / "ADDON.md"]


# --- Encodage des scripts ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("script", sorted(SCRIPTS.glob("*.ps1")), ids=lambda p: p.name)
def test_powershell_scripts_are_utf8_with_bom(script):
    raw = script.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), f"{script.name} : BOM UTF-8 absent (Windows PowerShell 5.1 lit en ANSI)"
    raw.decode("utf-8")  # strict


def test_there_are_powershell_scripts():
    assert {p.name for p in SCRIPTS.glob("*.ps1")} >= {"install_plugin.ps1", "install_update_task.ps1"}


# --- Ancienne tâche « veille locale » ------------------------------------------------------------------------------


def test_the_watch_only_task_script_is_gone():
    assert not (SCRIPTS / "install_watch_task.ps1").exists()
    for doc in DOCS:
        assert "install_watch_task" not in doc.read_text(encoding="utf-8"), doc.name


def test_update_script_removes_the_old_task():
    text = UPDATE_SCRIPT.read_text(encoding="utf-8-sig")
    assert '"WoW Forever - veille locale"' in text and '"WoW Forever - mise à jour"' in text
    assert "Unregister-ScheduledTask -TaskName $OldTaskName" in text


# --- Contenu de la tâche, sans l'installer -------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="module ScheduledTasks de Windows PowerShell")
def test_update_task_content_without_installing_it():
    done = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(UPDATE_SCRIPT), "-Print"],
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr.decode("utf-8", errors="replace")
    task = json.loads(done.stdout.decode("utf-8"))
    assert task["TaskName"] == "WoW Forever - mise à jour"  # accent intact : script lu en UTF-8
    assert Path(task["Execute"]).name.lower() == "pythonw.exe"  # interpréteur de base, sans fenêtre
    assert task["Arguments"] == "-m forever.update_task"
    assert Path(task["WorkingDirectory"]) == REPO_ROOT
    assert task["Trigger"]["Kind"] == "Daily" and task["Trigger"]["DaysInterval"] == 1
    assert "T08:00:00" in task["Trigger"]["StartBoundary"]
    assert task["StartWhenAvailable"] is True  # lancée dès que possible si 08:00 est passée
    assert task["RunOnlyIfNetworkAvailable"] is True
    assert task["ExecutionTimeLimit"] == "PT2H"
    assert task["MultipleInstances"] == "IgnoreNew"
    assert task["LogonType"] == "Interactive" and task["RunLevel"] == "Limited"  # sans droits administrateur
    assert task["OldTaskName"] == "WoW Forever - veille locale"


# --- Relais de la tâche (interpréteur de base, sans fenêtre) -------------------------------------------------------


def test_update_task_command_is_the_hook_command_with_its_log():
    assert update_task.command("REAL") == ["REAL", "-u", "-m", "forever", "update", "--auto", "--json", "--log"]


def test_update_task_waits_for_the_pass_and_returns_its_code(monkeypatch):
    calls = []

    def run(args, env):
        calls.append((args, env))
        return 3

    monkeypatch.setattr(update_task, "run_held", run)
    monkeypatch.setattr("forever.spawn.current_interpreter", lambda: ("REAL", {"__PYVENV_LAUNCHER__": "VENV"}))
    assert update_task.main() == 3
    assert calls == [(update_task.command("REAL"), {"__PYVENV_LAUNCHER__": "VENV"})]


# --- Journal du passage --------------------------------------------------------------------------------------------


def test_run_log_path_is_shared_by_the_hook_and_the_task(tmp_path):
    from forever.update import run_log_path, update_dir

    assert run_log_path(tmp_path, NOW) == update_dir(tmp_path) / f"run-{NOW:%Y%m%dT%H%M%SZ}.log"


def test_update_log_option_writes_the_pass_in_the_update_journal(make_deps, monkeypatch, capsys):
    deps = make_deps()

    def fake(deps, options, *, progress=None, **_):
        assert options.auto is True
        progress("verrou : fait")
        return {
            "schema_version": 1,
            "started_at": "2026-10-10T08:00:00Z",
            "finished_at": "2026-10-10T08:01:00Z",
            "steps": [],
            "verdicts": [],
            "written": [],
            "pending": [],
            "provenance": {"game_version": "x"},
        }

    monkeypatch.setattr("forever.update.run_update", fake)
    monkeypatch.setattr("forever.update.exit_code", lambda report: 0)
    assert main(["update", "--auto", "--json", "--log"], deps) == 0
    out, err = capsys.readouterr()
    assert out == "" and err == ""
    from forever.update import run_log_path

    text = run_log_path(deps.cache_dir, deps.now()).read_text(encoding="utf-8")
    assert "verrou : fait" in text and '"finished_at": "2026-10-10T08:01:00Z"' in text
