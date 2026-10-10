"""Passage `forever update --auto` lancé par le pont (demande de l'utilisateur du 2026-10-10, décision 227).

Le pont, qui tourne en permanence, relit toutes les `CHECK_S` secondes l'état du jeu et la date de `DBCache.bin`.
Le jeu qui se ferme (journal de combat terminé) ou un `DBCache.bin` réécrit (le client l'écrit à la déconnexion du
royaume, DON14) déclenche un passage, une fois l'ensemble stable depuis `SETTLE_S` secondes ; le passage prend
lui-même le verrou de la tâche de 08:00 et du hook de démarrage : verrou vivant, le pont réessaie plus tard. Au
premier relevé (pont lancé jeu ouvert ou fermé), rien n'est lancé."""

import os

from forever.bridge.updater import CHECK_S, SETTLE_S, UpdateOnClose
from test_bridge_loop import NOW, Clock, FakeCapture, events, make

from forever.bridge.journal import Journal


class Game:
    def __init__(self, running):
        self.running = running

    def __call__(self):
        if isinstance(self.running, Exception):
            raise self.running
        return self.running


class Launch:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.answers.pop(0) if self.answers else True


def setup(tmp_path, running, launch=None):
    clock = Clock()
    game = Game(running)
    dbcache = tmp_path / "Cache" / "ADB" / "enUS" / "DBCache.bin"
    dbcache.parent.mkdir(parents=True)
    dbcache.write_bytes(b"ancien")
    launch = launch or Launch()
    trigger = UpdateOnClose(
        game_running=game,
        dbcache=dbcache,
        journal=Journal(tmp_path / "journal", lambda: NOW),
        clock=clock,
        launch=launch,
    )
    return trigger, game, clock, launch, dbcache


def advance(trigger, clock, seconds):
    end = clock.t + seconds
    while clock.t < end:
        clock.t += 1.0
        trigger.tick()


def rewrite(path, data):
    path.write_bytes(data)
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000_000))  # date distincte, même sur un disque lent


def journal_events(tmp_path):
    return [e["event"] for e in events(tmp_path)]


def test_nothing_is_launched_at_the_first_reading(tmp_path):
    trigger, _, clock, launch, _ = setup(tmp_path, running=False)
    trigger.tick()
    advance(trigger, clock, SETTLE_S * 3)
    assert launch.calls == 0


def test_game_closing_launches_one_pass_once_settled(tmp_path):
    trigger, game, clock, launch, _ = setup(tmp_path, running=True)
    trigger.tick()
    game.running = False
    advance(trigger, clock, SETTLE_S - CHECK_S)
    assert launch.calls == 0  # pas avant que l'ensemble soit stable
    advance(trigger, clock, CHECK_S * 3)
    assert launch.calls == 1
    advance(trigger, clock, SETTLE_S * 4)
    assert launch.calls == 1
    launched = [e for e in events(tmp_path) if e["event"] == "update_launched"]
    assert len(launched) == 1 and launched[0]["reasons"] == ["game_closed"]


def test_dbcache_written_while_the_game_runs_launches_a_pass(tmp_path):
    trigger, _, clock, launch, dbcache = setup(tmp_path, running=True)
    trigger.tick()
    rewrite(dbcache, b"nouveau build")
    advance(trigger, clock, SETTLE_S + CHECK_S * 2)
    assert launch.calls == 1
    launched = [e for e in events(tmp_path) if e["event"] == "update_launched"]
    assert launched[0]["reasons"] == ["dbcache_written"]


def test_dbcache_and_closing_together_make_one_pass(tmp_path):
    trigger, game, clock, launch, dbcache = setup(tmp_path, running=True)
    trigger.tick()
    rewrite(dbcache, b"nouveau build")
    game.running = False
    advance(trigger, clock, SETTLE_S + CHECK_S * 2)
    assert launch.calls == 1
    launched = [e for e in events(tmp_path) if e["event"] == "update_launched"]
    assert launched[0]["reasons"] == ["dbcache_written", "game_closed"]


def test_a_rewrite_during_the_wait_restarts_it(tmp_path):
    trigger, game, clock, launch, dbcache = setup(tmp_path, running=True)
    trigger.tick()
    game.running = False
    advance(trigger, clock, SETTLE_S - CHECK_S)
    rewrite(dbcache, b"nouveau build")
    advance(trigger, clock, SETTLE_S - CHECK_S)
    assert launch.calls == 0
    advance(trigger, clock, CHECK_S * 3)
    assert launch.calls == 1


def test_a_live_lock_defers_the_pass_until_it_is_free(tmp_path):
    trigger, game, clock, launch, _ = setup(tmp_path, running=True, launch=Launch(False, False, True))
    trigger.tick()
    game.running = False
    advance(trigger, clock, SETTLE_S + CHECK_S * 4)
    assert launch.calls == 3
    names = journal_events(tmp_path)
    assert names.count("update_deferred") == 1 and names.count("update_launched") == 1


def test_a_failed_launch_is_journaled_and_dropped(tmp_path):
    def broken():
        raise OSError("relais en échec")

    trigger, game, clock, _, _ = setup(tmp_path, running=True, launch=broken)
    trigger.tick()
    game.running = False
    advance(trigger, clock, SETTLE_S * 3)
    errors = [e for e in events(tmp_path) if e["event"] == "error"]
    assert len(errors) == 1 and "relais en échec" in errors[0]["error"]


def test_unknown_game_state_changes_nothing(tmp_path):
    trigger, game, clock, launch, _ = setup(tmp_path, running=True)
    trigger.tick()
    game.running = OSError("liste des processus illisible")
    advance(trigger, clock, SETTLE_S * 3)
    assert launch.calls == 0


def test_the_state_is_read_at_most_every_check_period(tmp_path):
    calls = []

    def game():
        calls.append(1)
        return False

    trigger = UpdateOnClose(
        game_running=game,
        dbcache=tmp_path / "absent" / "DBCache.bin",
        journal=Journal(tmp_path / "journal", lambda: NOW),
        clock=(clock := Clock()),
        launch=Launch(),
    )
    for _ in range(int(CHECK_S * 4)):  # quatre pas par seconde, comme la boucle du pont
        clock.t += 0.25
        trigger.tick()
    assert len(calls) == 1


def test_the_bridge_ticks_the_trigger_and_survives_its_errors(tmp_path):
    bridge, _, _ = make(tmp_path, FakeCapture(None, front=False), lambda prompt, session: None)

    class Boom:
        ticks = 0

        def tick(self):
            Boom.ticks += 1
            raise RuntimeError("panne simulée")

    bridge.updater = Boom()
    bridge.step()
    bridge.step()
    assert Boom.ticks == 2
    errors = [e for e in events(tmp_path) if e["event"] == "error" and e.get("where") == "mise à jour à la fermeture"]
    assert errors and "panne simulée" in errors[0]["error"]
