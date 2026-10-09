"""Commandes du pont (P06a, bloc D) : `forever bridge start` lance la boucle détachée par le relais de `forever.spawn`
(jamais deux ponts), `stop` pose le fichier d'arrêt, `status` dit si le pont tourne, avec sa provenance."""

import json
import sys

from forever.bridge import loop
from forever.cli import main


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def wow_dir(tmp_path):
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    return wow


def test_start_spawns_the_loop_detached(capsys, make_deps, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("forever.spawn.spawn_detached", lambda args, log: calls.append((args, log)))
    deps = make_deps(wow_dir=wow_dir(tmp_path))
    code, out, _ = run(capsys, ["bridge", "start"], deps)
    assert code == 0 and len(calls) == 1
    args, log = calls[0]
    assert args[:6] == [sys.executable, "-u", "-m", "forever", "bridge", "run"]
    assert log.parent == deps.cache_dir / "bridge" and log.name.startswith("run-") and log.suffix == ".log"
    assert "pont" in out


def test_start_refuses_when_a_bridge_runs(capsys, make_deps, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("forever.spawn.spawn_detached", lambda args, log: calls.append(args))
    deps = make_deps(wow_dir=wow_dir(tmp_path))
    assert loop.acquire_lock(deps.cache_dir, deps.now(), pid=4242, alive=lambda p: True)
    monkeypatch.setattr("forever.spawn.pid_alive", lambda p: True)
    code, _, err = run(capsys, ["bridge", "start"], deps)
    assert code != 0 and calls == [] and "4242" in err


def test_stop_writes_the_stop_file(capsys, make_deps, tmp_path):
    deps = make_deps(wow_dir=wow_dir(tmp_path))
    code, _, _ = run(capsys, ["bridge", "stop"], deps)
    assert code == 0 and (deps.cache_dir / "bridge" / "stop").is_file()


def test_status_json_has_provenance(capsys, make_deps, tmp_path):
    deps = make_deps(wow_dir=wow_dir(tmp_path))
    code, out, _ = run(capsys, ["bridge", "status", "--json"], deps)
    payload = json.loads(out)
    assert code == 0 and payload["running"] is False and "provenance" in payload
    assert "data" in payload and "line" in payload["data"]
