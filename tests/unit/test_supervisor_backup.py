"""Sauvegarde avant bascule d'installation vue par la surveillance du pont (LN1, blocs B et E, décision 271)."""

from datetime import UTC, datetime

from test_choice_everywhere import hold_lock

from forever.bridge import autostart
from forever.bridge.journal import Journal


def test_the_supervisor_asks_for_a_backup_before_switching(tmp_path):
    chosen = {"dir": tmp_path / "A"}
    switches = []
    clock = {"t": 0.0, "n": 0}

    def sleep(seconds):
        clock["t"] += seconds
        clock["n"] += 1
        n = clock["n"]
        if n == 1:
            hold_lock(tmp_path, 4242)
        if n == 2:
            chosen["dir"] = tmp_path / "B"
        if n == 4:
            autostart.request_stop(tmp_path)

    journal = Journal(tmp_path / "bridge" / "journal", lambda: datetime(2026, 11, 4, 9, 0, tzinfo=UTC))
    autostart.supervise(
        tmp_path,
        lambda: None,
        journal=journal,
        clock=lambda: clock["t"],
        sleep=sleep,
        alive=lambda pid: pid in (4242, 999),
        pid=999,
        resolve=lambda: chosen["dir"],
        game_running=lambda old, new: False,
        on_switch=lambda: switches.append(clock["n"]),
    )
    assert switches == [2]


def test_the_backup_is_launched_detached_with_the_real_interpreter(tmp_path, monkeypatch):
    from forever import spawn

    calls = []
    monkeypatch.setattr(spawn, "spawn_detached", lambda args, log, env=None: calls.append((args, env)))
    monkeypatch.setattr(spawn, "current_interpreter", lambda: ("REAL", {}))
    autostart.backup_before_switch(tmp_path / "cache", datetime(2026, 11, 4, 9, 0, tzinfo=UTC))
    args, env = calls[0]
    assert args[:6] == ["REAL", "-u", "-m", "forever", "backup", "--reason"]
    assert env["FOREVER_CACHE_DIR"] == str(tmp_path / "cache")
