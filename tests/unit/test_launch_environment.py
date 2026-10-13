"""Pont, surveillance et tâche de mise à jour lancés depuis un Python sans aucun paquet (décision 241, cas réel du
2026-10-13 après la remise à zéro du PC : le Python de base installé par uv, sans les dépendances du projet).

- Machine neuve : depuis l'interpréteur de base lancé sans site-packages (`-S`) et sans aucune variable de
  l'environnement, la chaîne réelle (interpréteur choisi, relais détaché, processus final) importe `forever.cli` et
  ses dépendances ; le relais transmet la variable qui place l'interpréteur dans `.venv` (Python la retire de son
  propre environnement au démarrage, d'où la panne).
- Environnement cassé : la vérification au démarrage rend l'erreur d'import ; la surveillance ne relance pas le pont en
  boucle, note l'erreur une fois et réessaie plus tard ; la tâche de mise à jour ne lance pas le passage ; l'erreur
  est lisible dans `forever bridge status` et `forever update status`.

Aucun réseau ; tout s'écrit dans `tmp_path`."""

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from forever import spawn, update_task
from forever.bridge import autostart
from forever.bridge.journal import Journal

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = getattr(sys, "_base_executable", sys.executable)
CLEAN = {
    k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", spawn.VENV_LAUNCHER)
}


def bare_python(code, tmp_path, timeout=120):
    """`code` exécuté par l'interpréteur de base sans site-packages (`-S`), comme la tâche planifiée d'une machine
    neuve : aucun paquet tiers importable."""
    return subprocess.run(
        [BASE, "-S", "-c", code], cwd=REPO_ROOT, env=CLEAN, capture_output=True, text=True, timeout=timeout,
        check=False,
    )  # fmt: skip


def test_a_bare_python_cannot_import_the_dependencies(tmp_path):
    done = bare_python("import yaml", tmp_path)
    assert done.returncode != 0 and "yaml" in done.stderr


def test_the_bridge_chain_starts_with_the_project_dependencies_from_a_bare_python(tmp_path):
    mark = tmp_path / "ok.txt"
    log = tmp_path / "run.log"
    child = f"import forever.cli, yaml, pathlib; pathlib.Path({str(mark)!r}).write_text('ok')"
    code = (
        "from pathlib import Path\n"
        "from forever import spawn\n"
        "exe, env = spawn.current_interpreter()\n"
        f"spawn.spawn_detached([exe, '-c', {child!r}], Path({str(log)!r}), env=env)\n"
    )
    done = bare_python(code, tmp_path)
    assert done.returncode == 0, done.stderr
    for _ in range(240):
        if mark.exists():
            break
        time.sleep(0.25)
    assert mark.exists(), log.read_text(encoding="utf-8", errors="replace") if log.exists() else "journal absent"


def test_the_update_task_finds_its_dependencies_from_a_bare_python(tmp_path):
    code = "from forever import spawn\nexe, env = spawn.current_interpreter()\nprint(spawn.probe_environment(exe, env))"
    done = bare_python(code, tmp_path)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "None"


# --- environnement cassé --------------------------------------------------------------------------------------


def test_probe_reports_the_missing_module(tmp_path):
    error = spawn.probe_environment(BASE, CLEAN, code="import forever_module_absent")
    assert error is not None and "forever_module_absent" in error


def test_launch_bridge_refuses_a_broken_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(
        spawn, "probe_environment", lambda exe, env, **kw: "ModuleNotFoundError: No module named 'yaml'"
    )
    launched = []
    monkeypatch.setattr(spawn, "spawn_detached", lambda *a, **k: launched.append(a))
    with pytest.raises(spawn.EnvironmentBroken, match="yaml"):
        autostart.launch_bridge(tmp_path / "wow", tmp_path, datetime(2026, 10, 13, tzinfo=UTC))
    assert launched == []
    state = spawn.read_environment(tmp_path / "bridge")
    assert state is not None and "yaml" in state["error"]
    monkeypatch.setattr(spawn, "probe_environment", lambda exe, env, **kw: None)
    autostart.launch_bridge(tmp_path / "wow", tmp_path, datetime(2026, 10, 13, tzinfo=UTC))
    assert len(launched) == 1 and spawn.read_environment(tmp_path / "bridge") is None


def test_supervisor_does_not_loop_on_a_broken_environment(tmp_path):
    clock = [0.0]
    calls = []
    sleeps = []

    def launch():
        calls.append(clock[0])
        raise spawn.EnvironmentBroken("ModuleNotFoundError: No module named 'yaml'")

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
        if clock[0] >= 3 * autostart.ENV_RETRY_S + 1:
            (tmp_path / "bridge" / autostart.STOP_MARKER).write_text("", encoding="utf-8")

    journal = Journal(tmp_path / "bridge" / "journal", lambda: datetime(2026, 10, 13, tzinfo=UTC))
    autostart.supervise(tmp_path, launch, journal=journal, clock=lambda: clock[0], sleep=sleep, alive=lambda p: False)
    assert len(calls) == 4  # un essai au démarrage, puis un toutes les ENV_RETRY_S secondes
    lines = [
        json.loads(x)
        for p in (tmp_path / "bridge" / "journal").glob("*.jsonl")
        for x in p.read_text("utf-8").splitlines()
    ]
    kinds = [e["event"] for e in lines]
    assert kinds.count("autostart_env_error") == 1  # noté une fois, pas à chaque essai
    assert "autostart_bridge_down" not in kinds and "autostart_launch" not in kinds


def test_update_task_does_not_start_the_pass_with_a_broken_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        spawn, "probe_environment", lambda exe, env, **kw: "ModuleNotFoundError: No module named 'yaml'"
    )
    ran = []
    monkeypatch.setattr(update_task, "run_held", lambda args, env: ran.append(args) or 0)
    assert update_task.main() == update_task.EXIT_ENVIRONMENT
    assert ran == []
    state = spawn.read_environment(tmp_path / "update")
    assert state is not None and "yaml" in state["error"]
    monkeypatch.setattr(spawn, "probe_environment", lambda exe, env, **kw: None)
    assert update_task.main() == 0 and len(ran) == 1
    assert spawn.read_environment(tmp_path / "update") is None


def test_the_error_is_shown_by_both_status_commands(make_deps, capsys):
    from forever.cli import main

    deps = make_deps()
    error = "ModuleNotFoundError: No module named 'yaml'"
    spawn.record_environment(deps.cache_dir / "bridge", error, "python.exe", "2026-10-13T06:31:38Z")
    spawn.record_environment(deps.cache_dir / "update", error, "python.exe", "2026-10-13T06:00:00Z")
    assert main(["bridge", "status"], deps) == 0
    out = capsys.readouterr()[0]
    assert "ne peut pas démarrer" in out and "No module named 'yaml'" in out and "uv sync" in out
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr()[0]
    assert "ne peut pas démarrer" in out and "No module named 'yaml'" in out and "uv sync" in out
