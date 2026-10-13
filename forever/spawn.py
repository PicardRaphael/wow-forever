"""Lancement détaché d'un passage de `forever update` (T08d, blocs E et G).

Le passage tourne dans un processus séparé, sans fenêtre et sans bloquer la session ni la commande qui le lance ; sa
sortie va dans `<cache>/update/run-<horodatage>.log`, écrite au fil de l'eau (`python -u`). Aucun réseau ici : c'est
le passage lancé qui y accède, par `forever/pipeline/`.

Un relais coupe la filiation (correctif du 2026-10-06) : la commande qui lance (hook, `forever update approve`)
démarre un relais, qui démarre le passage puis se termine aussitôt, avant que la commande reprenne la main. Le
passage n'a plus alors de parent vivant : la fin de l'arbre de processus qui l'a lancé (session fermée,
`taskkill /T`, groupe de processus tué) ne l'atteint plus. Sonde du 2026-10-06 : sans relais, `taskkill /T` sur la
commande tuait aussi le passage, malgré `DETACHED_PROCESS`.

Vrai interpréteur (décision 226) : sous Windows, `.venv/Scripts/python.exe` n'est qu'un lanceur, qui démarre
l'interpréteur de base et le retient dans un objet de tâche fermé à sa mort (`KILL_ON_JOB_CLOSE`) ; tuer le lanceur
tue l'interpréteur. Un processus qui doit durer (le pont) est donc lancé directement avec l'interpréteur de base,
`__PYVENV_LAUNCHER__` désignant le lanceur : l'interpréteur se place alors lui-même dans l'environnement (paquets
compris), comme quand le lanceur le démarre. Ce module n'importe que la bibliothèque standard : la tâche planifiée
l'utilise depuis l'interpréteur de base, hors de l'environnement."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath
from typing import Any

# Drapeaux de Windows : processus détaché, nouveau groupe (Ctrl+C de la session ne le tue pas), sans fenêtre.
_DETACHED = 0x00000008 | 0x00000200 | 0x08000000
_BREAKAWAY_FROM_JOB = 0x01000000  # hors de l'objet job du lanceur, quand le job le permet
_NO_WINDOW = 0x08000000
_RELAY_TIMEOUT_S = 60.0
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5
VENV_LAUNCHER = "__PYVENV_LAUNCHER__"
# Python retire `__PYVENV_LAUNCHER__` de son propre environnement au démarrage : le relais la reçoit sous ce nom et la
# remet pour le processus final (décision 241 ; sans elle, le pont tournait sans les paquets du projet).
FORWARDED_LAUNCHER = "FOREVER_PYVENV_LAUNCHER"
REPO_ROOT = Path(__file__).resolve().parents[1]
# Vérification de l'environnement au démarrage (décision 241) : l'interpréteur choisi importe le point d'entrée du
# projet et ses dépendances ; l'état d'un échec est gardé dans `<dossier>/environment.json`.
PROBE_CODE = "import forever.cli"
PROBE_TIMEOUT_S = 120.0
ENV_STATE = "environment.json"
ENV_HINT = "lancer `uv sync` à la racine du dépôt (environnement du projet incomplet), puis relancer la tâche planifiée"


class EnvironmentBroken(OSError):
    """L'interpréteur choisi n'importe pas les dépendances du projet : rien n'est lancé."""


def probe_environment(
    exe: str, env: Mapping[str, str], *, code: str = PROBE_CODE, timeout: float = PROBE_TIMEOUT_S
) -> str | None:
    """None si `exe`, avec les variables `env`, importe le projet et ses dépendances ; sinon la dernière ligne de
    l'erreur (« ModuleNotFoundError: No module named 'yaml' »)."""
    try:
        done = subprocess.run(  # liste d'arguments, sans shell
            [exe, "-c", code],
            cwd=REPO_ROOT,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"{type(exc).__name__}: {exc}"
    if done.returncode == 0:
        return None
    lines = (done.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
    return lines[-1] if lines else f"code de sortie {done.returncode}"


def record_environment(folder: Path, error: str | None, exe: str, at: str) -> None:
    """Garde l'échec de la vérification (`error`) dans `<folder>/environment.json`, ou retire l'état (None)."""
    path = folder / ENV_STATE
    if error is None:
        path.unlink(missing_ok=True)
        return
    folder.mkdir(parents=True, exist_ok=True)
    doc = {"error": error, "interpreter": exe, "at": at, "hint": ENV_HINT}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def read_environment(folder: Path) -> dict[str, Any] | None:
    """Dernier échec de la vérification gardé dans `folder`, ou None."""
    try:
        doc = json.loads((folder / ENV_STATE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) and doc.get("error") else None


def environment_line(doc: Mapping[str, Any]) -> str:
    """Ligne des commandes d'état : « ne peut pas démarrer : … depuis … : lancer `uv sync` … »."""
    return f"ne peut pas démarrer : {doc.get('error')} (depuis {doc.get('at')}) : {doc.get('hint') or ENV_HINT}"


def real_interpreter(
    *, launcher: str, base_executable: str, environ: Mapping[str, str], windows: bool
) -> tuple[str, dict[str, str]]:
    """Interpréteur réel et variables qui le font tourner dans l'environnement du lanceur `launcher` : sous Windows,
    `python.exe` (console) à côté de l'interpréteur de base, avec `__PYVENV_LAUNCHER__` ; ailleurs, `launcher`
    lui-même (pas de lanceur qui retienne l'interpréteur)."""
    env = dict(environ)
    if not windows:
        return launcher, env
    env[VENV_LAUNCHER] = launcher
    return str(PureWindowsPath(base_executable).with_name("python.exe")), env


def current_interpreter() -> tuple[str, dict[str, str]]:
    """`real_interpreter` pour l'environnement du dépôt, depuis l'environnement (lanceur : `sys.executable`) ou
    depuis l'interpréteur de base (tâche planifiée : lanceur `.venv/Scripts/python.exe` du dépôt)."""
    in_venv = sys.prefix != sys.base_prefix
    windows = sys.platform == "win32"
    default = REPO_ROOT / ".venv" / ("Scripts/python.exe" if windows else "bin/python")
    return real_interpreter(
        launcher=sys.executable if in_venv else str(default),
        base_executable=getattr(sys, "_base_executable", sys.executable),
        environ=os.environ,
        windows=windows,
    )


def update_command(*extra: str) -> list[str]:
    """`python -u -m forever update --auto --json …` avec l'interpréteur de l'installation courante ; `-u` : sortie
    écrite sans tampon dans le journal du passage."""
    return [sys.executable, "-u", "-m", "forever", "update", "--auto", "--json", *extra]


def spawn_detached(args: Sequence[str], log_path: Path, env: Mapping[str, str] | None = None) -> None:
    """Lance `args` détaché par un relais (voir le module), sortie dans `log_path`, avec les variables `env` (défaut :
    celles du processus) ; rend la main une fois le relais terminé. Lève OSError si le lancement échoue (l'appelant
    l'attrape)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    relay = [sys.executable, "-m", "forever.spawn", str(log_path), *args]
    flags = _NO_WINDOW if sys.platform == "win32" else 0
    if env is not None and VENV_LAUNCHER in env:
        env = dict(env)
        env[FORWARDED_LAUNCHER] = env.pop(VENV_LAUNCHER)  # remise par le relais au processus final
    try:
        done = subprocess.run(  # liste d'arguments, sans shell
            relay,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=_RELAY_TIMEOUT_S,
            check=False,
            creationflags=flags,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired as exc:
        raise OSError(f"relais du lancement détaché sans réponse après {_RELAY_TIMEOUT_S:.0f} s") from exc
    if done.returncode != 0:
        detail = (done.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
        raise OSError(f"relais du lancement détaché en échec ({done.returncode}) : {detail[-1] if detail else '?'}")


def _child_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Variables du processus final : `__PYVENV_LAUNCHER__` remise depuis `FORWARDED_LAUNCHER` (voir ce nom)."""
    env = dict(environ)
    launcher = env.pop(FORWARDED_LAUNCHER, None)
    if launcher:
        env[VENV_LAUNCHER] = launcher
    return env


def _launch(args: Sequence[str], log_path: Path) -> None:
    """Démarre `args` détaché, sortie dans `log_path` (dans le relais)."""
    env = _child_env(os.environ)
    with log_path.open("ab") as log:
        if sys.platform == "win32":
            try:  # hors du job du lanceur s'il le permet, sinon dans le job (refus : OSError)
                subprocess.Popen(  # liste d'arguments, sans shell
                    list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                    creationflags=_DETACHED | _BREAKAWAY_FROM_JOB, close_fds=True, env=env,
                )  # fmt: skip
            except OSError:
                subprocess.Popen(  # liste d'arguments, sans shell
                    list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=_DETACHED,
                    close_fds=True, env=env,
                )  # fmt: skip
        else:
            subprocess.Popen(  # liste d'arguments, sans shell
                list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True,
                env=env,
            )  # fmt: skip


def pid_alive(pid: object) -> bool | None:
    """Vrai si le processus `pid` tourne, faux s'il est mort ; None si on ne peut pas le savoir. Sous Windows, par
    `OpenProcess` et `GetExitCodeProcess` : jamais `os.kill`, qui y termine le processus visé."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return bool(ctypes.get_last_error() == _ERROR_ACCESS_DENIED)  # accès refusé : le processus existe
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None
            return code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # POSIX : signal 0, aucun effet sur le processus
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def process_created(pid: object) -> float | None:
    """Heure de création du processus `pid` (secondes depuis 1970), ou None si on ne peut pas la lire (hors de
    Windows, processus mort) ; PermissionError si le processus existe mais refuse même la lecture limitée (processus
    d'un autre compte ou du système : jamais le pont ni la surveillance, qui tournent sous l'utilisateur). Sert à
    reconnaître un pid repris par un autre processus après un redémarrage du PC (décision 226)."""
    if sys.platform != "win32" or not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetProcessTimes.argtypes = (wintypes.HANDLE, *(ctypes.POINTER(wintypes.FILETIME),) * 4)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        if ctypes.get_last_error() == _ERROR_ACCESS_DENIED:
            raise PermissionError(f"processus {pid} inaccessible")
        return None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return None
        ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime  # centaines de ns depuis 1601
        return (ticks - 116444736000000000) / 1e7
    finally:
        kernel32.CloseHandle(handle)


if __name__ == "__main__":  # relais : `python -m forever.spawn <journal> <commande…>`
    if len(sys.argv) < 3:
        sys.stderr.write("usage : python -m forever.spawn <journal> <commande…>\n")
        sys.exit(2)
    _launch(sys.argv[2:], Path(sys.argv[1]))
    sys.exit(0)
