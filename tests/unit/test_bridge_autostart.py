"""Démarrage automatique du pont (décision 226) : tâche planifiée « WoW Forever - pont » lancée à l'ouverture de la
session Windows de l'utilisateur, sans droits administrateur, qui démarre une surveillance ; la surveillance lance le
pont avec le vrai interpréteur (jamais le lanceur de l'environnement, qui retient l'interpréteur dans un objet de
tâche et l'emporte quand on le tue) et le relance s'il s'arrête, sauf arrêt voulu (`forever bridge stop`).

Le contenu de la tâche est vérifié ici sans l'installer : aucun test n'appelle `schtasks` pour de vrai."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

import pytest
from conftest import REPO_ROOT

from forever import spawn
from forever.bridge import autostart, loop
from forever.bridge.journal import Journal
from forever.cli import main

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
PYTHONW = Path(r"C:\Program Files\Python313\pythonw.exe")
REPO = Path(r"C:\Users\joueur\wow-forever")
WOW = Path(r"C:\Program Files (x86)\World of Warcraft\_classic_beta_")
CACHE = Path(r"C:\Users\joueur\.cache\forever")


def task():
    xml = autostart.task_xml(user=r"PC\joueur", pythonw=PYTHONW, repo=REPO, wow_dir=WOW, cache_dir=CACHE)
    return ET.fromstring(xml)


def text(root, path):
    node = root.find(path, NS)
    assert node is not None, path
    return node.text


# --- Contenu de la tâche -------------------------------------------------------------------------------------------


def test_task_name():
    assert autostart.TASK_NAME == "WoW Forever - pont"


def test_task_starts_at_the_logon_of_this_user_only():
    root = task()
    triggers = root.find("t:Triggers", NS)
    assert [t.tag.split("}")[1] for t in triggers] == ["LogonTrigger"]
    assert text(root, "t:Triggers/t:LogonTrigger/t:UserId") == r"PC\joueur"
    assert text(root, "t:Triggers/t:LogonTrigger/t:Enabled") == "true"


def test_task_needs_no_administrator_rights():
    root = task()
    assert text(root, "t:Principals/t:Principal/t:UserId") == r"PC\joueur"
    assert text(root, "t:Principals/t:Principal/t:LogonType") == "InteractiveToken"  # bureau de la session
    assert text(root, "t:Principals/t:Principal/t:RunLevel") == "LeastPrivilege"


def test_task_settings():
    root = task()
    assert text(root, "t:Settings/t:MultipleInstancesPolicy") == "IgnoreNew"  # une seule surveillance
    assert text(root, "t:Settings/t:ExecutionTimeLimit") == "PT0S"  # sans limite : le pont tourne toute la session
    assert text(root, "t:Settings/t:DisallowStartIfOnBatteries") == "false"
    assert text(root, "t:Settings/t:StopIfGoingOnBatteries") == "false"
    assert text(root, "t:Settings/t:Enabled") == "true"


def test_task_runs_the_supervisor_with_the_windowless_base_interpreter():
    root = task()
    assert text(root, "t:Actions/t:Exec/t:Command") == str(PYTHONW)
    assert text(root, "t:Actions/t:Exec/t:WorkingDirectory") == str(REPO)
    assert text(root, "t:Actions/t:Exec/t:Arguments") == (
        f'-m forever.bridge.autostart --wow-dir "{WOW}" --cache-dir "{CACHE}"'
    )


def test_task_description_is_in_french():
    assert "pont" in text(task(), "t:RegistrationInfo/t:Description")


def test_parse_task_reads_back_the_action():
    xml = autostart.task_xml(user=r"PC\joueur", pythonw=PYTHONW, repo=REPO, wow_dir=WOW, cache_dir=CACHE)
    parsed = autostart.parse_task('<?xml version="1.0" encoding="UTF-16"?>\r\r\n' + xml.split("?>", 1)[1])
    assert parsed == {
        "command": str(PYTHONW),
        "arguments": f'-m forever.bridge.autostart --wow-dir "{WOW}" --cache-dir "{CACHE}"',
        "working_directory": str(REPO),
        "user": r"PC\joueur",
    }


# --- Vrai interpréteur ---------------------------------------------------------------------------------------------


def test_real_interpreter_on_windows_is_the_base_python_in_the_environment():
    exe, env = spawn.real_interpreter(
        launcher=r"C:\r\.venv\Scripts\python.exe",
        base_executable=r"C:\Program Files\Python313\pythonw.exe",
        environ={"PATH": "x"},
        windows=True,
    )
    assert exe == str(Path(r"C:\Program Files\Python313") / "python.exe")
    assert env == {"PATH": "x", "__PYVENV_LAUNCHER__": r"C:\r\.venv\Scripts\python.exe"}


def test_real_interpreter_elsewhere_is_the_launcher_itself():
    exe, env = spawn.real_interpreter(
        launcher="/r/.venv/bin/python", base_executable="/usr/bin/python3", environ={"PATH": "x"}, windows=False
    )
    assert exe == "/r/.venv/bin/python" and env == {"PATH": "x"}


def test_bridge_launch_uses_the_real_interpreter(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(spawn, "spawn_detached", lambda args, log, env=None: calls.append((args, log, env)))
    monkeypatch.setattr(spawn, "current_interpreter", lambda: ("REAL", {"__PYVENV_LAUNCHER__": "VENV"}))
    from datetime import UTC, datetime

    log = autostart.launch_bridge(tmp_path / "wow", tmp_path / "cache", datetime(2026, 10, 9, 18, 0, tzinfo=UTC))
    args, logged, env = calls[0]
    assert args == ["REAL", "-u", "-m", "forever", "bridge", "run", "--wow-dir", str(tmp_path / "wow")]
    assert logged == log == tmp_path / "cache" / "bridge" / "run-20261009-180000.log"
    assert env == {"__PYVENV_LAUNCHER__": "VENV", "FOREVER_CACHE_DIR": str(tmp_path / "cache")}


def test_bridge_start_uses_the_real_interpreter(make_deps, tmp_path, monkeypatch, capsys):
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    deps = make_deps(wow_dir=wow)
    calls = []
    monkeypatch.setattr(spawn, "spawn_detached", lambda args, log, env=None: calls.append((args, env)))
    monkeypatch.setattr(spawn, "current_interpreter", lambda: ("REAL", {"__PYVENV_LAUNCHER__": "VENV"}))
    assert main(["bridge", "start", "--model", "haiku"], deps) == 0
    args, env = calls[0]
    assert args[:6] == ["REAL", "-u", "-m", "forever", "bridge", "run"] and args[-2:] == ["--model", "haiku"]
    assert env is not None and env["__PYVENV_LAUNCHER__"] == "VENV"
    assert env["FOREVER_CACHE_DIR"] == str(deps.cache_dir)


@pytest.mark.skipif(sys.platform != "win32", reason="lanceur de l'environnement : Windows seulement")
def test_base_python_with_the_launcher_variable_runs_in_the_environment():
    """Hypothèse sur laquelle repose le correctif : l'interpréteur de base, avec `__PYVENV_LAUNCHER__`, tourne dans
    l'environnement du dépôt (paquets compris) sans passer par le lanceur."""
    exe, env = spawn.current_interpreter()
    assert Path(exe).resolve() != Path(sys.executable).resolve()
    code = "import sys, forever, mcp; print(sys.prefix)"
    done = subprocess.run([exe, "-c", code], env=env, capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 0, done.stderr
    assert Path(done.stdout.strip()).resolve() == Path(sys.prefix).resolve()


def test_supervisor_and_update_task_need_only_the_standard_library():
    """La tâche lance ces modules avec l'interpréteur de base, hors de l'environnement : aucun paquet tiers."""
    code = "import forever.bridge.autostart, forever.update_task"
    done = subprocess.run(
        [sys.executable, "-S", "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False
    )
    assert done.returncode == 0, done.stderr


# --- Surveillance --------------------------------------------------------------------------------------------------


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def events(cache):
    out = []
    for path in sorted((cache / "bridge" / "journal").glob("*.jsonl")):
        out += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return out


def hold_lock(cache, pid):
    path = loop.lock_path(cache)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "started_at": "2026-10-09T18:00:00Z"}), encoding="utf-8")


def supervise(cache, on_sleep, *, alive=lambda pid: pid in (4242, 999), pid=999):
    """Surveillance jusqu'au marqueur d'arrêt ; `on_sleep(n, clock)` pilote le monde à chaque pause."""
    clock = Clock()
    launches = []
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        clock.t += seconds
        on_sleep(len(sleeps), clock)

    from datetime import UTC, datetime

    journal = Journal(cache / "bridge" / "journal", lambda: datetime(2026, 10, 9, 18, 0, tzinfo=UTC))
    code = autostart.supervise(
        cache, lambda: launches.append(clock()), journal=journal, clock=clock, sleep=sleep, alive=alive, pid=pid
    )
    return code, launches


def test_supervisor_launches_the_bridge_when_none_runs_and_stops_on_request(tmp_path):
    def world(n, clock):
        if n == 1:
            hold_lock(tmp_path, 4242)  # le pont lancé a pris le verrou
        if n == 3:
            autostart.request_stop(tmp_path)

    code, launches = supervise(tmp_path, world)
    assert code == 0 and launches == [0.0]
    names = [e["event"] for e in events(tmp_path)]
    assert names[0] == "autostart_start" and "autostart_launch" in names and names[-1] == "autostart_stop"
    assert not (tmp_path / "bridge" / autostart.STOP_MARKER).exists()
    assert not (tmp_path / "bridge" / autostart.STATE).exists()


def test_supervisor_does_not_launch_while_a_bridge_holds_the_lock(tmp_path):
    hold_lock(tmp_path, 4242)  # pont lancé à la main avant la surveillance

    def world(n, clock):
        if n == 4:
            autostart.request_stop(tmp_path)

    code, launches = supervise(tmp_path, world)
    assert code == 0 and launches == []


def test_supervisor_relaunches_a_bridge_that_died(tmp_path):
    def world(n, clock):
        if n == 1:
            hold_lock(tmp_path, 4242)
        if n == 200:  # le pont meurt après une longue partie : relancé tout de suite
            hold_lock(tmp_path, 5555)
        if n == 201:  # le pont relancé a pris le verrou
            hold_lock(tmp_path, 4242)
        if n == 202:
            autostart.request_stop(tmp_path)

    _, launches = supervise(tmp_path, world)
    assert len(launches) == 2 and launches[1] == 200 * autostart.CHECK_S
    down = [e for e in events(tmp_path) if e["event"] == "autostart_bridge_down"]
    assert len(down) == 1 and down[0]["next_in_s"] == 0


def test_supervisor_backs_off_when_the_bridge_dies_at_once(tmp_path):
    def world(n, clock):
        if clock() >= 4 * 3600:
            autostart.request_stop(tmp_path)

    _, launches = supervise(tmp_path, world)
    gaps = [b - a for a, b in pairwise(launches)]
    assert len(launches) >= 6
    assert all(b > a for a, b in pairwise(gaps[:6]))  # attente croissante
    assert max(gaps) <= autostart.MAX_DELAY_S + 2 * autostart.CHECK_S  # plafonnée


def test_a_stale_stop_request_does_not_prevent_the_next_session(tmp_path):
    autostart.request_stop(tmp_path)  # laissé par la session précédente

    def world(n, clock):
        if n == 2:
            autostart.request_stop(tmp_path)

    _, launches = supervise(tmp_path, world)
    assert launches == [0.0]


def test_a_second_supervisor_exits_at_once(tmp_path):
    state = tmp_path / "bridge" / autostart.STATE
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"pid": 4242, "started_at": "2026-10-09T17:00:00Z"}), encoding="utf-8")
    code, launches = supervise(tmp_path, lambda n, c: None, pid=999)
    assert code == 0 and launches == []
    assert json.loads(state.read_text(encoding="utf-8"))["pid"] == 4242


def test_supervisor_pid(tmp_path):
    assert autostart.supervisor_pid(tmp_path, alive=lambda p: True) is None
    state = tmp_path / "bridge" / autostart.STATE
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"pid": 4242}), encoding="utf-8")
    assert autostart.supervisor_pid(tmp_path, alive=lambda p: True) == 4242
    assert autostart.supervisor_pid(tmp_path, alive=lambda p: False) is None


# --- Commandes -----------------------------------------------------------------------------------------------------


class Schtasks:
    """`schtasks` simulé : tâches enregistrées en mémoire, rien n'est installé."""

    def __init__(self):
        self.calls: list[list[str]] = []
        self.tasks: dict[str, str] = {}

    def __call__(self, args):
        self.calls.append(list(args))
        name = args[args.index("/TN") + 1]
        if args[0] == "/Create":
            self.tasks[name] = Path(args[args.index("/XML") + 1]).read_text(encoding="utf-16")
            return subprocess.CompletedProcess(args, 0, b"OK", b"")
        if args[0] == "/Query":
            if name not in self.tasks:
                return subprocess.CompletedProcess(args, 1, b"", b"introuvable")
            return subprocess.CompletedProcess(args, 0, self.tasks[name].encode("ascii", "replace"), b"")
        if args[0] == "/Delete":
            return subprocess.CompletedProcess(args, 0 if self.tasks.pop(name, None) else 1, b"", b"")
        return subprocess.CompletedProcess(args, 0, b"", b"")


@pytest.fixture
def windows(monkeypatch, tmp_path):
    fake = Schtasks()
    monkeypatch.setattr(autostart, "SUPPORTED", True)
    monkeypatch.setattr(autostart, "schtasks", fake)
    monkeypatch.setattr(autostart, "base_pythonw", lambda: tmp_path / "pythonw.exe")
    monkeypatch.setattr(autostart, "current_user", lambda: r"PC\joueur")
    (tmp_path / "pythonw.exe").write_bytes(b"")
    return fake


def deps_with_wow(make_deps, tmp_path):
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    return make_deps(wow_dir=wow)


def test_install_registers_the_task_and_starts_it(windows, make_deps, tmp_path, capsys):
    deps = deps_with_wow(make_deps, tmp_path)
    assert main(["bridge", "autostart", "install", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    create = windows.calls[0]
    assert create[:3] == ["/Create", "/TN", autostart.TASK_NAME] and create[-1] == "/F"
    assert windows.calls[1] == ["/Run", "/TN", autostart.TASK_NAME]
    xml = Path(create[create.index("/XML") + 1])
    assert xml.parent == deps.cache_dir / "bridge" and xml.read_bytes()[:2] == b"\xff\xfe"  # UTF-16 avec BOM
    root = ET.fromstring(windows.tasks[autostart.TASK_NAME].split("?>", 1)[1])
    assert text(root, "t:Actions/t:Exec/t:Command") == str(tmp_path / "pythonw.exe")
    assert f'--wow-dir "{tmp_path / "wow"}"' in text(root, "t:Actions/t:Exec/t:Arguments")
    assert payload["installed"] is True and payload["started"] is True and "provenance" in payload


def test_install_without_start(windows, make_deps, tmp_path, capsys):
    deps = deps_with_wow(make_deps, tmp_path)
    assert main(["bridge", "autostart", "install", "--no-start"], deps) == 0
    assert [c[0] for c in windows.calls] == ["/Create"]
    assert "prochaine ouverture de session" in capsys.readouterr()[0]


def test_status_and_remove(windows, make_deps, tmp_path, capsys, monkeypatch):
    deps = deps_with_wow(make_deps, tmp_path)
    assert main(["bridge", "autostart", "status", "--json"], deps) == 0
    assert json.loads(capsys.readouterr()[0])["installed"] is False
    assert main(["bridge", "autostart", "install", "--no-start"], deps) == 0
    capsys.readouterr()
    state = deps.cache_dir / "bridge" / autostart.STATE
    state.write_text(json.dumps({"pid": 4242}), encoding="utf-8")
    hold_lock(deps.cache_dir, 5555)
    monkeypatch.setattr("forever.spawn.pid_alive", lambda p: True)
    assert main(["bridge", "autostart", "status", "--json"], deps) == 0
    status = json.loads(capsys.readouterr()[0])
    assert status["installed"] is True and status["supervisor_pid"] == 4242 and status["bridge_pid"] == 5555
    assert status["task"]["command"] == str(tmp_path / "pythonw.exe") and status["problems"] == []
    assert main(["bridge", "autostart", "remove"], deps) == 0
    out = capsys.readouterr()[0]
    assert windows.calls[-1] == ["/Delete", "/TN", autostart.TASK_NAME, "/F"]
    assert (deps.cache_dir / "bridge" / autostart.STOP_MARKER).exists()  # la surveillance s'arrête
    assert "retirée" in out and "forever bridge stop" in out


def test_status_reports_a_missing_interpreter(windows, make_deps, tmp_path, capsys):
    deps = deps_with_wow(make_deps, tmp_path)
    assert main(["bridge", "autostart", "install", "--no-start"], deps) == 0
    (tmp_path / "pythonw.exe").unlink()
    capsys.readouterr()
    assert main(["bridge", "autostart", "status", "--json"], deps) == 0
    problems = json.loads(capsys.readouterr()[0])["problems"]
    assert problems and "pythonw.exe" in problems[0]


def test_autostart_refused_off_windows(make_deps, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(autostart, "SUPPORTED", False)
    deps = deps_with_wow(make_deps, tmp_path)
    assert main(["bridge", "autostart", "install"], deps) != 0
    assert "Windows" in capsys.readouterr()[1]


def test_stop_also_stops_the_supervisor(make_deps, tmp_path, monkeypatch, capsys):
    deps = deps_with_wow(make_deps, tmp_path)
    hold_lock(deps.cache_dir, 4242)
    (deps.cache_dir / "bridge" / autostart.STATE).write_text(json.dumps({"pid": 5555}), encoding="utf-8")
    monkeypatch.setattr("forever.spawn.pid_alive", lambda p: True)
    assert main(["bridge", "stop", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["stop"] is True and payload["autostart_stopped"] is True
    assert (deps.cache_dir / "bridge" / autostart.STOP_MARKER).exists()
    assert main(["bridge", "stop"], deps) == 0
    assert "prochaine ouverture de session" in capsys.readouterr()[0]


# --- pid repris après un arrêt brutal du PC ------------------------------------------------------------------------


def test_pid_reused():
    from datetime import UTC, datetime

    from forever.bridge.lock import pid_reused

    started = datetime(2026, 10, 9, 18, 0, tzinfo=UTC).timestamp()
    doc = {"pid": 4242, "started_at": "2026-10-09T18:00:00Z"}
    assert pid_reused(doc, created=lambda pid: started - 5) is False  # le propriétaire du verrou
    assert pid_reused(doc, created=lambda pid: started + 3600) is True  # créé après le verrou : autre processus
    assert pid_reused(doc, created=lambda pid: None) is False  # inconnu
    assert pid_reused({"pid": 4242}, created=lambda pid: started + 3600) is False  # heure absente


def test_supervisor_ignores_a_lock_whose_pid_was_reused(tmp_path, monkeypatch):
    """PC arrêté pendant que le pont tournait : le verrou reste ; à la session suivante, son pid appartient à un autre
    processus, plus récent que le verrou. La surveillance lance le pont, qui reprend le verrou."""
    from datetime import UTC, datetime

    hold_lock(tmp_path, 4242)
    monkeypatch.setattr(spawn, "pid_alive", lambda pid: True)
    monkeypatch.setattr(spawn, "process_created", lambda pid: datetime(2026, 10, 10, 8, 0, tzinfo=UTC).timestamp())
    launches = []

    def sleep(_):
        autostart.request_stop(tmp_path)

    journal = Journal(tmp_path / "bridge" / "journal", lambda: datetime(2026, 10, 10, 8, 1, tzinfo=UTC))
    autostart.supervise(tmp_path, lambda: launches.append(1), journal=journal, sleep=sleep, pid=999)
    assert launches == [1]
    assert loop.acquire_lock(tmp_path, datetime(2026, 10, 10, 8, 1, tzinfo=UTC), pid=777)  # le pont le reprend
