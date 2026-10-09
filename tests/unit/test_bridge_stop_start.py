"""Arrêt et démarrage du pont (retours de la sonde en jeu F du 2026-10-09, point 2). Cas réel : `forever bridge stop`
lancé alors qu'aucun pont ne tournait a posé un fichier d'arrêt, et le `bridge start` suivant s'est arrêté dans la
même seconde (journal : start puis stop à 10:09:10). `stop` ne pose plus de fichier sans pont vivant ; un pont qui
démarre efface tout fichier d'arrêt plus ancien que son lancement et dit dans le journal pourquoi il s'arrête.

Même sonde : trois ponts (lancés à 10:05:42, 10:10:02 et 10:13:25) sont morts sans écrire `stop` ni trace, verrou
laissé en place : processus tué de l'extérieur. Le pont date désormais son dernier signe de vie dans le verrou
(toutes les 30 secondes) et `forever bridge status` signale un arrêt sans `stop` avec cette heure."""

import json
import os
import time

from forever.bridge import loop
from forever.bridge.loop import HEARTBEAT_S, acquire_lock
from forever.cli import main


def wow(tmp_path):
    root = tmp_path / "wow"
    (root / "Interface" / "AddOns").mkdir(parents=True)
    return root


def test_stop_without_a_running_bridge_writes_no_file(capsys, make_deps, tmp_path):
    deps = make_deps(wow_dir=wow(tmp_path))
    assert main(["bridge", "stop"], deps) == 0
    out = capsys.readouterr()[0]
    assert not (deps.cache_dir / "bridge" / "stop").exists()
    assert "Aucun pont ne tourne" in out and "fichier d'arrêt est posé" not in out


def test_stop_with_a_running_bridge_writes_the_file(capsys, make_deps, tmp_path, monkeypatch):
    deps = make_deps(wow_dir=wow(tmp_path))
    assert acquire_lock(deps.cache_dir, deps.now(), pid=4242, alive=lambda p: True)
    monkeypatch.setattr("forever.spawn.pid_alive", lambda p: True)
    assert main(["bridge", "stop"], deps) == 0
    assert (deps.cache_dir / "bridge" / "stop").is_file() and "4242" in capsys.readouterr()[0]


def test_a_stale_stop_file_does_not_stop_a_new_bridge(tmp_path):
    from test_bridge_loop import FakeAgent, FakeCapture, events, make

    bridge, _, _ = make(tmp_path, FakeCapture(), FakeAgent())
    stop = tmp_path / "stop"
    stop.write_text("", encoding="utf-8")
    old = time.time() - 120
    os.utime(stop, (old, old))
    sleeps = []

    def sleep(_):
        sleeps.append(1)
        if len(sleeps) == 3:
            stop.write_text("", encoding="utf-8")

    assert bridge.run(stop, sleep=sleep) == 0
    names = [e["event"] for e in events(tmp_path)]
    assert names[0] == "start" and "published" in names and names[-1] == "stop"
    assert len(sleeps) == 3 and not stop.exists()
    start = next(e for e in events(tmp_path) if e["event"] == "start")
    assert start["stale_stop_file"] is True and start["pid"] == os.getpid()
    assert events(tmp_path)[-1]["reason"] == "fichier d'arrêt"


def test_heartbeat_is_called_while_running(tmp_path):
    from test_bridge_loop import FakeAgent, FakeCapture, make

    bridge, _, clock = make(tmp_path, FakeCapture(), FakeAgent())
    beats = []
    bridge.heartbeat = lambda: beats.append(clock())
    stop = tmp_path / "stop"
    steps = []

    def sleep(_):
        steps.append(1)
        clock.t += HEARTBEAT_S / 2
        if len(steps) == 6:
            stop.write_text("", encoding="utf-8")

    bridge.run(stop, sleep=sleep)
    assert len(beats) == 3  # au départ, puis toutes les HEARTBEAT_S


def test_lock_keeps_the_last_sign_of_life(make_deps):
    deps = make_deps()
    assert acquire_lock(deps.cache_dir, deps.now(), pid=4242, alive=lambda p: True)
    loop.touch_lock(deps.cache_dir, deps.now(), pid=4242)
    doc = json.loads(loop.lock_path(deps.cache_dir).read_text(encoding="utf-8"))
    assert doc["pid"] == 4242 and doc["seen_at"] == doc["started_at"]
    loop.touch_lock(deps.cache_dir, deps.now(), pid=1)  # verrou d'un autre pont : inchangé
    assert json.loads(loop.lock_path(deps.cache_dir).read_text(encoding="utf-8"))["pid"] == 4242


def test_status_reports_a_bridge_killed_without_stop(capsys, make_deps, monkeypatch):
    deps = make_deps()
    assert acquire_lock(deps.cache_dir, deps.now(), pid=4242, alive=lambda p: True)
    monkeypatch.setattr("forever.spawn.pid_alive", lambda p: False)
    assert main(["bridge", "status", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["running"] is False
    assert payload["abnormal_end"] == {
        "pid": 4242,
        "started_at": payload["abnormal_end"]["started_at"],
        "seen_at": payload["abnormal_end"]["seen_at"],
    }
    assert main(["bridge", "status"], deps) == 0
    out = capsys.readouterr()[0]
    assert "arrêté sans passer par stop" in out and "dernier signe de vie" in out
