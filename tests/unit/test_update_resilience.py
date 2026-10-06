"""Passages de `forever update` interrompus ou laissés en plan (correctifs du 2026-10-06, après le passage du jour).

Cas réels relevés le 2026-10-06 dans `<cache>/update` :

1. le passage détaché lancé par `forever update approve` (12:40:16) est mort avec l'arbre de processus qui l'avait
   lancé : `taskkill /T` sur le lanceur tue aussi un processus `DETACHED_PROCESS` (sonde du jour) ;
2. son verrou est resté, alors que son processus était mort ;
3. le clone dédié est resté sale dans les seuls chemins que le passage écrit (`forever/data`, `docs/research`), et
   tout passage suivant s'arrêtait ;
4. son journal `run-20261006T124016Z.log` est vide (0 octet) : la sortie n'était écrite qu'à la fin ;
5. un dossier de version vide (`forever/data/1.60.1.70235`), reste de ce passage, a fait dire au passage suivant
   « version du client 1.60.1.70235 déjà installée » alors que le manifeste de `main` installe 1.60.1.70170.

Aucun réseau : processus locaux (1, 2), git réel sur un dépôt nu local et `gh` simulé (3, 5)."""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from test_update_chain import BASE, DRY, TARGET, Replay, montage, step  # noqa: F401 : fixture partagée
from test_update_publish import GAME, Recorder, git, isolated_git, origin  # noqa: F401 : fixtures partagées

from forever import update
from forever.cli import main
from forever.spawn import update_command
from forever.timefmt import format_utc
from forever.update import UpdateOptions, acquire_lock, due, run_update, update_dir, update_summary

ADDONS_ONLY = UpdateOptions(only=frozenset({"addons"}))

# Lanceur : lance un passage détaché (qui écrit `fini` après un court délai), signale qu'il l'a lancé, puis attend
# d'être tué avec tout son arbre de processus, comme une session ou un terminal qu'on ferme.
LAUNCHER = """
import sys, time
from pathlib import Path
from forever.spawn import spawn_detached
marker = Path(sys.argv[1])
child = [sys.executable, "-c", "import pathlib, sys, time; time.sleep(2); pathlib.Path(sys.argv[1]).write_text('fini')",
         str(marker)]
spawn_detached(child, marker.with_name("passage.log"))
marker.with_name("lance").write_text("lancé")
time.sleep(120)
"""


def _wait_for(path: Path, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.1)
    return True


def _kill_tree(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
    else:
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=30)


# --- 1. Lancement détaché ---------------------------------------------------------------------------------------


@pytest.mark.slow
def test_a_detached_run_survives_the_kill_of_its_launcher_tree(tmp_path):
    marker = tmp_path / "fini"
    launcher = subprocess.Popen(
        [sys.executable, "-c", LAUNCHER, str(marker)], cwd=REPO_ROOT, start_new_session=os.name != "nt"
    )
    try:
        assert _wait_for(tmp_path / "lance", 60), "le lanceur n'a pas lancé le passage"
    finally:
        _kill_tree(launcher)
    assert _wait_for(marker, 30), "le passage détaché est mort avec son lanceur"
    assert marker.read_text() == "fini"


def test_the_detached_command_writes_its_output_unbuffered():
    assert update_command()[1] == "-u"


# --- 2. Verrou dont le processus est mort ------------------------------------------------------------------------


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(timeout=60)
    return proc.pid


def test_a_lock_whose_process_is_dead_is_taken_over(montage):  # noqa: F811
    deps, _ = montage()
    pid = _dead_pid()
    lock = update_dir(deps.cache_dir) / "lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        json.dumps({"pid": pid, "started_at": format_utc(deps.now()), "command": "forever update --auto"}),
        encoding="utf-8",
    )
    assert update_summary(deps.cache_dir, deps.now())["running"] is False
    assert due(deps.cache_dir, deps.now()) is True
    taken = acquire_lock(deps, "forever update")
    assert taken is not None and taken.status == "fait" and taken.data["stale"] is True
    assert f"processus {pid}" in taken.detail and "mort" in taken.detail
    assert json.loads(lock.read_text(encoding="utf-8"))["pid"] == os.getpid()


def test_a_fresh_lock_of_a_living_process_still_stops_the_run(montage):  # noqa: F811
    deps, _ = montage()
    assert acquire_lock(deps, "forever update --auto") is None  # processus des tests : vivant
    assert update_summary(deps.cache_dir, deps.now())["running"] is True
    report = run_update(deps, DRY, replay=Replay())
    assert [s["status"] for s in report["steps"]] == ["arrêt"]


# --- 4. Journal écrit au fil de l'eau ----------------------------------------------------------------------------


def test_each_step_is_written_before_the_next_one_starts(montage, monkeypatch, capsys):  # noqa: F811
    """Un passage tué à l'étape « addons » a déjà écrit les étapes précédentes : sur la sortie d'erreur (journal du
    passage détaché) et dans le verrou (`forever update status`)."""
    deps, _ = montage()
    seen: dict = {}

    def killed_here(run):
        seen["err"] = capsys.readouterr().err
        seen["lock"] = json.loads((update_dir(deps.cache_dir) / "lock").read_text(encoding="utf-8"))
        return update.Step("addons", "rien", "sonde", {})

    monkeypatch.setattr(update, "_step_addons", killed_here)
    main(["update", "--json", "--no-network"], deps)
    for name in ("archivage", "clone", "jeu", "nouvelle_version", "correctifs", "journaux"):
        assert f"{name} : " in seen["err"], (name, seen["err"])
    assert "addons : en cours" in seen["err"]
    assert [s["name"] for s in seen["lock"]["steps"]] == ["verrou", "archivage", "clone", "jeu", "nouvelle_version",
                                                          "correctifs", "journaux"]  # fmt: skip
    assert seen["lock"]["step"] == "addons"
    assert json.loads(capsys.readouterr().out)["steps"][-1]["name"] == "fin"  # sortie JSON inchangée


# --- 5. Version installée lue dans le manifeste ------------------------------------------------------------------


def test_an_empty_version_folder_is_not_an_installed_version(montage):  # noqa: F811
    deps, _ = montage()
    (deps.data_dir / TARGET).mkdir()  # reste d'un passage interrompu, absent du manifeste
    report = run_update(deps, DRY, replay=Replay())
    game = step(report, "jeu")
    assert game["status"] == "fait" and game["data"]["target"] == TARGET, game
    assert game["data"]["installed"] == BASE
    assert step(report, "correctifs")["detail"] == f"version du client {TARGET} non installée"
    assert [v["action"] for v in report["verdicts"]] == ["écrire"]


# --- 3 et 5. Clone dédié laissé sale par un passage interrompu ---------------------------------------------------


def _clone(origin_):
    """Clone dédié créé par un premier passage, comme sur le poste."""
    montage_, bare = origin_
    deps, _ = montage_()
    run_update(deps, ADDONS_ONLY, runner=Recorder())
    clone = update_dir(deps.cache_dir) / "repo"
    assert (clone / ".git").is_dir()
    return deps, bare, clone


def test_an_interrupted_publish_left_in_the_clone_is_discarded(origin):  # noqa: F811
    """Le passage tué pendant `tasks.py verify` laisse la préparation copiée dans `forever/data` (fichiers suivis
    modifiés, nouvelle version non suivie) et son rapport de recherche."""
    deps, bare, clone = _clone(origin)
    data = clone / "forever" / "data"
    shutil.copytree(data / BASE, data / TARGET)
    with (data / "manifest.json").open("a", encoding="utf-8") as f:
        f.write(" ")
    (clone / "docs" / "research").mkdir(parents=True)
    (clone / "docs" / "research" / f"data-{TARGET}-r1.md").write_text("rapport", encoding="utf-8")
    report = run_update(deps, GAME, runner=Recorder(), replay=Replay())
    cloned = step(report, "clone")
    assert cloned["status"] == "fait", cloned
    assert "passage interrompu" in cloned["detail"]
    assert any(p.startswith(f"forever/data/{TARGET}/") for p in cloned["data"]["discarded"])
    assert [w["version"] for w in report["written"]] == [TARGET]
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")


def test_an_empty_version_folder_left_in_the_clone_is_removed_and_the_version_installed(origin):  # noqa: F811
    """Le cas du poste : `forever/data/1.60.1.70235` vide dans le clone (fichiers retirés, dossier gardé)."""
    deps, bare, clone = _clone(origin)
    (clone / "forever" / "data" / TARGET).mkdir()
    report = run_update(deps, GAME, runner=Recorder(), replay=Replay())
    assert step(report, "clone")["status"] == "fait"
    assert f"forever/data/{TARGET}/" in step(report, "clone")["data"]["discarded"]
    assert step(report, "jeu")["data"]["target"] == TARGET
    assert [w["version"] for w in report["written"]] == [TARGET]
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")


def test_dirt_outside_the_paths_of_the_pass_still_stops_the_run(origin):  # noqa: F811
    deps, bare, clone = _clone(origin)
    head = git(bare, "rev-parse", "main")
    (clone / "notes.txt").write_text("à moi", encoding="utf-8")
    (clone / "forever" / "data" / TARGET).mkdir()
    report = run_update(deps, GAME, runner=Recorder(), replay=Replay())
    cloned = step(report, "clone")
    assert cloned["status"] == "arrêt" and "notes.txt" in cloned["detail"], cloned
    assert (clone / "notes.txt").read_text(encoding="utf-8") == "à moi"  # jamais touché
    assert report["written"] == [] and git(bare, "rev-parse", "main") == head
