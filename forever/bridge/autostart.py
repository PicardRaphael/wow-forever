"""Démarrage automatique du pont (décision 226) : tâche planifiée Windows « WoW Forever - pont », lancée à
l'ouverture de la session de l'utilisateur, sans droits administrateur.

La tâche lance la **surveillance** (`python -m forever.bridge.autostart`) avec le `pythonw.exe` de l'interpréteur de
base : aucune fenêtre (l'environnement n'a pas de `pythonw.exe`, et une tâche qui lance une console l'ouvre sur le
bureau) et aucun lanceur. Ce module n'importe donc que la bibliothèque standard. Toutes les `CHECK_S` secondes, la
surveillance lit le verrou du pont ; libre, elle lance le pont avec le vrai interpréteur (`spawn.current_interpreter`,
jamais le lanceur `.venv/Scripts/python.exe`, qui retient l'interpréteur dans un objet de tâche et l'emporte quand on
le tue). Un pont mort est relancé aussitôt, sauf s'il meurt dans la minute : l'attente double alors à chaque essai
(plafond `MAX_DELAY_S`). `forever bridge stop` (ou `autostart remove`) pose `STOP_MARKER` : la surveillance s'arrête
jusqu'à la prochaine ouverture de session (une demande laissée par la session précédente est effacée au démarrage).

Contenu de la tâche : `task_xml`, pur, vérifié par les tests sans rien installer. Installation, retrait et lecture
par `schtasks` (System32), sortie XML seulement (jamais la sortie texte, traduite)."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from forever import spawn
from forever.bridge.journal import Journal
from forever.bridge.lock import lock_holder, lock_info, pid_reused
from forever.errors import ForeverError
from forever.timefmt import format_utc

TASK_NAME = "WoW Forever - pont"
CHECK_S = 15.0
FAST_DEATH_S = 60.0  # un pont mort moins d'une minute après son lancement : attente avant le suivant
MAX_DELAY_S = 1800.0
ENV_RETRY_S = 300.0  # environnement du projet incomplet : nouvelle vérification (décision 241)
STATE = "autostart.json"
STOP_MARKER = "autostart.stop"
SUPPORTED = sys.platform == "win32"
_NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
_DESCRIPTION = (
    "Pont de conversation en jeu de forever-core (décision 226) : surveillance lancée à l'ouverture de la session, "
    "qui démarre le pont et le relance s'il s'arrête. Arrêt : forever bridge stop ; retrait : forever bridge "
    "autostart remove."
)


class AutostartError(ForeverError):
    """`schtasks` a refusé l'opération."""

    def __init__(self, message: str) -> None:
        super().__init__(
            "bridge_autostart", message, "vérifier le message de schtasks, ou créer la tâche depuis une session ouverte"
        )


# --- Contenu de la tâche ---------------------------------------------------------------------------------------


def _quoted(path: Path) -> str:
    """Chemin entre guillemets pour la ligne de commande Windows : une barre oblique inverse finale (`D:\\`) est
    doublée, sinon elle échapperait le guillemet."""
    text = str(path)
    return f'"{text}\\"' if text.endswith("\\") else f'"{text}"'


def task_arguments(wow_dir: Path | None, cache_dir: Path) -> str:
    """Arguments de la surveillance ; `wow_dir` None (LN1) : le dossier du client suit le choix de
    `forever.installs` à chaque lancement du pont, sinon il est forcé."""
    forced = f" --wow-dir {_quoted(wow_dir)}" if wow_dir is not None else ""
    return f"-m forever.bridge.autostart{forced} --cache-dir {_quoted(cache_dir)}"


def task_xml(*, user: str, pythonw: Path, repo: Path, wow_dir: Path | None, cache_dir: Path) -> str:
    """Définition de la tâche : ouverture de session de `user` seulement, jeton interactif (bureau de la session :
    fenêtre du jeu, capture), privilèges limités, une seule instance, sans limite de durée, sur batterie aussi."""
    user_x = escape(user)
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>forever-core</Author>
    <Description>{escape(_DESCRIPTION)}</Description>
    <URI>\\{escape(TASK_NAME)}</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{user_x}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user_x}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>5</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(pythonw))}</Command>
      <Arguments>{escape(task_arguments(wow_dir, cache_dir))}</Arguments>
      <WorkingDirectory>{escape(str(repo))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def parse_task(text: str) -> dict[str, str | None]:
    """Action et utilisateur d'une définition de tâche (sortie de `schtasks /Query /XML`)."""
    root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", text))

    def get(path: str) -> str | None:
        node = root.find(path, _NS)
        return node.text if node is not None else None

    return {
        "command": get("t:Actions/t:Exec/t:Command"),
        "arguments": get("t:Actions/t:Exec/t:Arguments"),
        "working_directory": get("t:Actions/t:Exec/t:WorkingDirectory"),
        "user": get("t:Principals/t:Principal/t:UserId"),
    }


def base_pythonw() -> Path:
    """`pythonw.exe` de l'interpréteur de base (sans fenêtre), à côté de celui qui fait tourner l'environnement."""
    return Path(getattr(sys, "_base_executable", sys.executable)).with_name("pythonw.exe")


def current_user() -> str:
    return f"{os.environ.get('USERDOMAIN') or os.environ.get('COMPUTERNAME', '.')}\\{getpass.getuser()}"


# --- schtasks --------------------------------------------------------------------------------------------------


def schtasks(args: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    """`schtasks <args>` (liste d'arguments, sans shell, sans fenêtre)."""
    return subprocess.run(  # liste d'arguments, sans shell
        ["schtasks", *args],
        capture_output=True,
        timeout=60,
        check=False,
        stdin=subprocess.DEVNULL,
        creationflags=0x08000000 if SUPPORTED else 0,
    )


def _decode(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("oem" if sys.platform == "win32" else "utf-8", errors="replace")


def install(xml_path: Path, *, start: bool) -> None:
    """Crée ou remplace la tâche décrite par `xml_path`, puis la lance tout de suite si `start`."""
    done = schtasks(["/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"])
    if done.returncode != 0:
        raise AutostartError(f"création de la tâche refusée : {_decode(done.stderr or done.stdout).strip()}")
    if start:
        done = schtasks(["/Run", "/TN", TASK_NAME])
        if done.returncode != 0:
            raise AutostartError(f"tâche créée, lancement refusé : {_decode(done.stderr or done.stdout).strip()}")


def remove() -> bool:
    """Retire la tâche ; faux si elle n'existait pas."""
    return schtasks(["/Delete", "/TN", TASK_NAME, "/F"]).returncode == 0


def query() -> dict[str, str | None] | None:
    """Action de la tâche installée, ou None si elle n'existe pas."""
    done = schtasks(["/Query", "/TN", TASK_NAME, "/XML", "ONE"])
    if done.returncode != 0:
        return None
    return parse_task(_decode(done.stdout))


def status(cache_dir: Path) -> dict[str, Any]:
    """Tâche installée, surveillance et pont en marche, problèmes de la tâche (interpréteur ou dépôt disparus)."""
    task = query()
    problems = []
    if task is not None:
        if not task["command"] or not Path(task["command"]).is_file():
            problems.append(
                f"interpréteur de la tâche introuvable : {task['command']} (relancer forever bridge autostart install)"
            )
        if not task["working_directory"] or not (Path(task["working_directory"]) / "forever").is_dir():
            problems.append(f"dépôt de la tâche introuvable : {task['working_directory']}")
    return {
        "installed": task is not None,
        "task": task,
        "supervisor_pid": supervisor_pid(cache_dir),
        "bridge_pid": lock_holder(cache_dir),
        "problems": problems,
    }


# --- Surveillance ----------------------------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def supervisor_pid(cache_dir: Path, alive: Callable[[object], bool | None] | None = None) -> int | None:
    """pid de la surveillance si elle tourne (ou si on ne peut pas savoir) ; None sinon, ou si son pid a été repris
    par un autre processus (vrais processus seulement)."""
    doc = _read_json(cache_dir / "bridge" / STATE)
    pid = doc.get("pid") if isinstance(doc, dict) else None
    if not isinstance(pid, int):
        return None
    if alive is None and pid_reused(doc):
        return None
    return None if (alive or spawn.pid_alive)(pid) is False else pid


def _bridge_running(cache_dir: Path, alive: Callable[[object], bool | None] | None) -> bool:
    """Un pont tient le verrou ; un verrou dont le pid a été repris (PC arrêté brutalement pendant que le pont
    tournait, pid redonné à un autre processus à la session suivante) ne compte pas."""
    if lock_holder(cache_dir, alive) is None:
        return False
    return alive is not None or not pid_reused(lock_info(cache_dir))


def request_stop(cache_dir: Path) -> None:
    """Demande à la surveillance de s'arrêter (lu à son pas suivant)."""
    path = cache_dir / "bridge" / STOP_MARKER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_utc(datetime.now(UTC)), encoding="utf-8")


def stop_supervisor(
    cache_dir: Path, *, sleep: Callable[[float], None] = time.sleep, timeout_s: float = CHECK_S + 10
) -> bool:
    """Arrête la surveillance en marche (marqueur) et attend sa sortie ; vrai si plus aucune ne tourne."""
    if supervisor_pid(cache_dir) is None:
        return True
    request_stop(cache_dir)
    waited = 0.0
    while waited < timeout_s:
        sleep(0.5)
        waited += 0.5
        if supervisor_pid(cache_dir) is None:
            return True
    return False


def launch_bridge(wow_dir: Path | None, cache_dir: Path, now: datetime, model: str | None = None) -> Path:
    """Lance le pont détaché avec le vrai interpréteur (`forever bridge start` et la surveillance) ; rend le journal
    du lancement. Lève OSError si le lancement échoue. `wow_dir` None : le pont lit l'installation choisie (LN1)."""
    exe, env = spawn.current_interpreter()
    env = {**env, "FOREVER_CACHE_DIR": str(cache_dir)}  # même verrou que la surveillance qui le lit
    # environnement vérifié avant tout lancement (décision 241) : un pont sans ses paquets mourrait aussitôt
    error = spawn.probe_environment(exe, env)
    spawn.record_environment(cache_dir / "bridge", error, exe, format_utc(now))
    if error is not None:
        raise spawn.EnvironmentBroken(f"{error} ({exe}) : {spawn.ENV_HINT}")
    args = [exe, "-u", "-m", "forever", "bridge", "run"]
    if wow_dir is not None:
        args += ["--wow-dir", os.path.abspath(wow_dir)]
    if model:
        args += ["--model", model]
    log = cache_dir / "bridge" / f"run-{now:%Y%m%d-%H%M%S}.log"
    spawn.spawn_detached(args, log, env=env)
    return log


def supervise(
    cache_dir: Path,
    launch: Callable[[], object],
    *,
    journal: Journal,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    alive: Callable[[object], bool | None] | None = None,
    pid: int | None = None,
    resolve: Callable[[], Path | None] | None = None,
    game_running: Callable[[Path | None, Path | None], bool | None] | None = None,
    on_switch: Callable[[], object] | None = None,
) -> int:
    """Boucle de surveillance jusqu'à `STOP_MARKER` ; rend 0. Une autre surveillance vivante : rend 0 aussitôt.

    LN1 : `resolve` (None quand la tâche force le dossier) rend le dossier du client choisi. Quand il change pendant
    qu'un pont tourne, la surveillance attend que le jeu soit fermé (`game_running` faux pour l'ancien et le nouveau
    dossier ; inconnu = ouvert), note `autostart_wow_changed`, pose le fichier d'arrêt du pont, puis le relance (sur
    le nouveau dossier) comme un pont mort."""
    pid = os.getpid() if pid is None else pid
    home = cache_dir / "bridge"
    home.mkdir(parents=True, exist_ok=True)
    marker, state = home / STOP_MARKER, home / STATE
    other = supervisor_pid(cache_dir, alive)
    waited = 0.0
    while other is not None and other != pid and marker.exists() and waited < CHECK_S + 5:
        sleep(1.0)  # surveillance précédente en train de s'arrêter (`remove` ou `stop` juste avant)
        waited += 1.0
        other = supervisor_pid(cache_dir, alive)
    if other is not None and other != pid:
        journal.write("autostart_skip", reason=f"surveillance déjà en marche (pid {other})")
        return 0
    marker.unlink(missing_ok=True)  # demande laissée par la session précédente
    state.write_text(json.dumps({"pid": pid, "started_at": format_utc(journal.now())}), encoding="utf-8")
    journal.write("autostart_start", pid=pid)
    last_launch: float | None = None
    watching_lock = False
    since: float | None = None  # pont vu en marche depuis
    watching = False  # un pont tourne (ou vient d'être lancé) : sa mort sera notée
    failures = 0
    next_at = 0.0
    env_error: str | None = None  # dernier échec de la vérification de l'environnement, noté une fois
    launched_for: Path | None = None  # dossier du pont en marche (LN1), relu à chaque lancement
    moving = False  # arrêt demandé au pont pour changer d'installation
    try:
        while True:
            if marker.exists():
                marker.unlink(missing_ok=True)
                if not watching_lock and last_launch is not None and clock() - last_launch < FAST_DEATH_S:
                    _stop_starting_bridge(cache_dir, alive, sleep)  # lancé juste avant le `stop`, sans verrou encore
                journal.write("autostart_stop", reason="arrêt demandé (forever bridge stop ou autostart remove)")
                return 0
            now = clock()
            watching_lock = _bridge_running(cache_dir, alive)
            if watching_lock:
                since = now if since is None else since
                if now - since >= FAST_DEATH_S:
                    failures = 0
                watching = True
                if resolve is not None and not moving:
                    moving = _follow_choice(cache_dir, journal, resolve, game_running, launched_for)
                    if moving and on_switch is not None:
                        try:  # sauvegarde avant la bascule (LN1) : son échec n'arrête pas la surveillance
                            on_switch()
                        except OSError as exc:
                            journal.write("error", where="sauvegarde avant bascule", error=str(exc))
            else:
                if watching:
                    watching = False
                    started = last_launch if last_launch is not None else since
                    lived = now - started if started is not None else 0.0
                    failures = failures + 1 if lived < FAST_DEATH_S + CHECK_S else 0
                    delay = min(MAX_DELAY_S, CHECK_S * 2**failures) if failures else 0.0
                    next_at = now + delay
                    journal.write("autostart_bridge_down", lived_s=round(lived), next_in_s=round(delay))
                since = None
                if now >= next_at:
                    moving = False
                    if resolve is not None:
                        try:
                            launched_for = resolve()
                        except Exception:  # noqa: BLE001 : le pont choisit lui-même son installation
                            launched_for = None
                    try:
                        log = launch()
                    except spawn.EnvironmentBroken as exc:
                        # rien n'a été lancé : pas de pont à surveiller, nouvelle vérification plus tard
                        if str(exc) != env_error:
                            env_error = str(exc)
                            journal.write("autostart_env_error", error=env_error, next_in_s=round(ENV_RETRY_S))
                        next_at = now + ENV_RETRY_S
                        sleep(CHECK_S)
                        continue
                    except OSError as exc:
                        journal.write("error", where="lancement du pont", error=str(exc))
                    else:
                        env_error = None
                        journal.write("autostart_launch", log=str(log) if log else None)
                    last_launch, watching = now, True
            sleep(CHECK_S)
    finally:
        doc = _read_json(state)
        if isinstance(doc, dict) and doc.get("pid") == pid:
            state.unlink(missing_ok=True)


def _follow_choice(
    cache_dir: Path,
    journal: Journal,
    resolve: Callable[[], Path | None],
    game_running: Callable[[Path | None, Path | None], bool | None] | None,
    launched_for: Path | None,
) -> bool:
    """Choix changé et jeu fermé : arrêt du pont demandé (vrai) ; sinon rien (faux). Une résolution en échec ne
    change rien : la surveillance continue sur le dossier en cours."""
    try:
        current = resolve()
    except Exception:  # noqa: BLE001 : la surveillance ne s'arrête jamais pour un choix illisible
        return False
    if current is None or current == launched_for:
        return False
    running = game_running(launched_for, current) if game_running is not None else None
    if running is not False:
        return False  # jeu ouvert, ou état inconnu : jamais de bascule en pleine partie
    journal.write("autostart_wow_changed", old=str(launched_for), new=str(current))
    (cache_dir / "bridge" / "stop").write_text("", encoding="utf-8")
    return True


def backup_before_switch(cache_dir: Path, now: datetime) -> Path:
    """`forever backup` lancé détaché avec l'interpréteur réel avant une bascule d'installation (LN1) ; rend son
    journal."""
    exe, env = spawn.current_interpreter()
    env = {**env, "FOREVER_CACHE_DIR": str(cache_dir)}
    log = cache_dir / "bridge" / f"backup-{now:%Y%m%d-%H%M%S}.log"
    spawn.spawn_detached(
        [exe, "-u", "-m", "forever", "backup", "--reason", "avant bascule d'installation"], log, env=env
    )
    return log


def _game_running(old: Path | None, new: Path | None) -> bool | None:
    """Le client d'un des deux dossiers tourne-t-il ? None si la liste des processus est illisible."""
    from forever.pipeline.live_logs import detect_game_running

    states = [detect_game_running(folder) for folder in (old, new)]
    if any(s is True for s in states):
        return True
    return None if any(s is None for s in states) else False


def resolve_wow_dir(cache_dir: Path, environ: Mapping[str, str] | None = None) -> Path | None:
    """Dossier du client choisi par `forever.installs` (`FOREVER_WOW_FORCE`, version finale adoptée, bêta,
    `FOREVER_WOW_DIR`), avec les disques fixes du poste ; None si aucun (LN1)."""
    from forever.installs import fixed_drives, no_drives, survey

    env = os.environ if environ is None else environ
    drives = no_drives if env.get("FOREVER_WOW_NO_DRIVES", "") not in ("", "0") else fixed_drives
    data_dir = Path(__file__).resolve().parent.parent / "data"
    choice, _ = survey(env, drives=drives, cache_dir=cache_dir, data_dir=data_dir)
    return choice.folder


def _stop_starting_bridge(
    cache_dir: Path, alive: Callable[[object], bool | None] | None, sleep: Callable[[float], None]
) -> None:
    """Pont lancé par la surveillance mais pas encore en possession du verrou quand l'arrêt arrive : on attend qu'il
    le prenne (30 s au plus), puis on pose son fichier d'arrêt (obéi : posé après la prise du verrou)."""
    for _ in range(30):
        if _bridge_running(cache_dir, alive):
            (cache_dir / "bridge" / "stop").write_text("", encoding="utf-8")
            return
        sleep(1.0)


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée de la tâche planifiée (`pythonw.exe -m forever.bridge.autostart`) : aucune console, tout va
    dans le journal du pont."""
    parser = argparse.ArgumentParser(prog="python -m forever.bridge.autostart")
    parser.add_argument("--wow-dir", type=Path, help="dossier forcé (sinon : choix de forever.installs, LN1)")
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    journal = Journal(args.cache_dir / "bridge" / "journal", lambda: datetime.now(UTC))
    forced: Path | None = args.wow_dir
    try:
        return supervise(
            args.cache_dir,
            lambda: launch_bridge(forced, args.cache_dir, datetime.now(UTC)),
            journal=journal,
            resolve=None if forced is not None else (lambda: resolve_wow_dir(args.cache_dir)),
            game_running=_game_running,
            on_switch=lambda: backup_before_switch(args.cache_dir, datetime.now(UTC)),
        )
    except Exception as exc:  # noqa: BLE001 : sans console, l'erreur n'a que le journal
        journal.write("error", where="surveillance", error=f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
