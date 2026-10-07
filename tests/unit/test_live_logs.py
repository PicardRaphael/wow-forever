"""Journal en cours d'écriture (décision 205, demande de l'utilisateur du 2026-10-07).

`forever update` et `forever measures refresh` ne mesurent un journal que si le jeu est fermé (aucun processus du
client) ou si le journal n'a pas été modifié depuis `LOG_QUIET_S` ; sinon il est noté « en cours d'écriture » et
reproposé au passage suivant. Cas réel : le journal du 2026-10-07 a grossi entre la simulation montrée et l'écriture.
État du jeu inconnu (détection en échec) : traité comme ouvert. Aucun processus réel n'est lu ici : la détection est
injectée dans `Deps`, l'analyse de la liste des processus est testée sur du texte."""

import dataclasses
import os
from datetime import timedelta

from conftest import LOCAL_VERSION
from test_measures_refresh import QUESTIE, accept, never, world  # noqa: F401  (fixture importée)
from test_update_chain import LOG, Measure, Replay, logs, step  # noqa: F401  (fixture importée)

from forever.cli import main
from forever.pipeline.live_logs import (
    DEFAULT_EXECUTABLES,
    LOG_QUIET_S,
    client_executables,
    game_running_from,
    split_live,
)
from forever.update import UpdateOptions, run_update

QUIET = timedelta(seconds=LOG_QUIET_S)
MINUTE = timedelta(minutes=1)
JOURNALS = UpdateOptions(dry_run=True, only=frozenset({"journaux"}))


def touch(path, when):
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def two_logs(tmp_path, now):
    recent, old = tmp_path / "WoWCombatLog-recent.txt", tmp_path / "WoWCombatLog-old.txt"
    for p in (recent, old):
        p.write_text("x", encoding="utf-8")
    touch(recent, now - QUIET + MINUTE)
    touch(old, now - QUIET - MINUTE)
    return recent, old


def test_game_closed_measures_every_log(tmp_path, make_deps):
    now = make_deps().now()
    recent, old = two_logs(tmp_path, now)
    ready, writing = split_live([recent, old], now=now, running=False)
    assert ready == [recent, old] and writing == []


def test_game_open_holds_a_recently_modified_log(tmp_path, make_deps):
    now = make_deps().now()
    recent, old = two_logs(tmp_path, now)
    ready, writing = split_live([recent, old], now=now, running=True)
    assert ready == [old]
    assert [w["name"] for w in writing] == [recent.name]
    assert writing[0]["age_s"] < LOG_QUIET_S


def test_unknown_game_state_counts_as_open(tmp_path, make_deps):
    now = make_deps().now()
    recent, old = two_logs(tmp_path, now)
    ready, writing = split_live([recent, old], now=now, running=None)
    assert ready == [old] and [w["name"] for w in writing] == [recent.name]


def test_a_log_dated_in_the_future_is_still_being_written(tmp_path, make_deps):
    now = make_deps().now()
    log = tmp_path / "WoWCombatLog-futur.txt"
    log.write_text("x", encoding="utf-8")
    touch(log, now + MINUTE)
    ready, writing = split_live([log], now=now, running=True)
    assert ready == [] and [w["name"] for w in writing] == [log.name]


def test_process_list_parsing():
    tasklist = '"System","4","Services","0","152 K"\n"WowB.exe","1234","Console","1","2 000 000 K"\n'
    assert game_running_from(tasklist, {"WowB.exe"}) is True
    assert game_running_from(tasklist.replace("WowB.exe", "wowb.EXE"), {"WowB.exe"}) is True  # casse ignorée
    assert game_running_from(tasklist, {"WowClassic.exe"}) is False
    ps = "systemd\n/usr/bin/bash\nWowB.exe\n"
    assert game_running_from(ps, {"WowB.exe"}) is True
    assert game_running_from("", {"WowB.exe"}) is False


def test_client_executables_come_from_the_client_folder(tmp_path):
    (tmp_path / "WowB.exe").write_bytes(b"")
    (tmp_path / "BlizzardError.exe").write_bytes(b"")
    assert client_executables(tmp_path) == {"WowB.exe"}
    assert client_executables(tmp_path / "absent") == set(DEFAULT_EXECUTABLES)


def test_refresh_skips_a_log_being_written(capsys, make_deps, world):  # noqa: F811
    deps = dataclasses.replace(make_deps(data_dir=world["data"]), confirm=never, game_running=lambda: True)
    now = deps.now()
    logs_dir = world["logs"]
    names = sorted(p.name for p in logs_dir.iterdir())
    for p in logs_dir.iterdir():
        touch(p, now - MINUTE)
    argv = ["measures", "refresh", "--logs", str(logs_dir), "--sv", str(world["sv"]), "--questie", str(QUESTIE)]
    code = main([*argv, "--fit-exclude", "3986", "--dry-run", "--json"], deps)
    out = __import__("json").loads(capsys.readouterr().out)
    assert code == 0
    assert out["sources"]["logs"] == []
    assert sorted(w["name"] for w in out["writing"]) == names
    assert any("en cours d'écriture" in a for a in out["provenance"]["assumptions"])


def test_refresh_measures_every_log_when_the_game_is_closed(capsys, make_deps, world):  # noqa: F811
    deps = dataclasses.replace(make_deps(data_dir=world["data"]), confirm=accept, game_running=lambda: False)
    now = deps.now()
    for p in world["logs"].iterdir():
        touch(p, now - MINUTE)
    argv = ["measures", "refresh", "--logs", str(world["logs"]), "--sv", str(world["sv"]), "--questie", str(QUESTIE)]
    code = main([*argv, "--fit-exclude", "3986", "--dry-run", "--json"], deps)
    out = __import__("json").loads(capsys.readouterr().out)
    assert code == 0 and len(out["sources"]["logs"]) == 2 and out["writing"] == []


def test_update_holds_a_log_being_written_and_proposes_it_again_later(logs):  # noqa: F811
    deps = dataclasses.replace(logs([(LOCAL_VERSION, 1)]), game_running=lambda: True)
    log = deps.wow_dir / "Logs" / LOG.name
    measure = Measure([{"file": "monsters.json", "pointer": "/hp_curve"}])
    touch(log, deps.now() - MINUTE)
    report = run_update(deps, JOURNALS, replay=Replay(), measure=measure)
    assert measure.calls == []
    journaux = step(report, "journaux")
    assert journaux["status"] == "rien" and "en cours d'écriture" in journaux["detail"]
    assert [w["name"] for w in journaux["data"]["writing"]] == [LOG.name]
    assert report["pending"] == []
    touch(log, deps.now() - QUIET - MINUTE)  # passage suivant : journal au repos
    report = run_update(deps, JOURNALS, replay=Replay(), measure=measure)
    assert measure.calls == [[LOG.name]]
    assert step(report, "journaux")["status"] == "attente"
