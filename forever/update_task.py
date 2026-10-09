"""Relais de la tâche planifiée « WoW Forever - mise à jour » (décision 226) : `pythonw.exe -m forever.update_task`.

La tâche lance ce module avec le `pythonw.exe` de l'interpréteur de base (aucune fenêtre : l'environnement n'a pas de
`pythonw.exe`, et une tâche qui lance une console l'ouvre sur le bureau pendant tout le passage) ; il n'importe donc
que la bibliothèque standard. Il lance `forever update --auto --json --log`, la commande du hook de démarrage, avec le
vrai interpréteur dans l'environnement du dépôt et sans console : même verrou (`<cache>/update/lock`, pris par le
passage) et même journal (`<cache>/update/run-<horodatage>.log`, ouvert par `--log`). Il attend la fin du passage et
rend son code ; le passage est retenu dans un objet de tâche fermé à la mort du relais, pour que la limite de 2 h de la
tâche (qui tue le relais) l'atteigne aussi."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping, Sequence

from forever import spawn

_NO_WINDOW = 0x08000000


def command(exe: str) -> list[str]:
    return [exe, "-u", "-m", "forever", "update", "--auto", "--json", "--log"]


def _kill_on_close_job() -> int | None:
    """Objet de tâche Windows qui tue ses processus quand son dernier descripteur se ferme (mort du relais) ; les
    processus que le passage lance en sortent (`SILENT_BREAKAWAY_OK`, comme le lanceur de l'environnement)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class Extended(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", Basic),
            ("IoInfo", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
    kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000 | 0x1000  # KILL_ON_JOB_CLOSE | SILENT_BREAKAWAY_OK
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        return None
    return int(job)


def run_held(args: Sequence[str], env: Mapping[str, str]) -> int:
    """Lance `args` sans console, retenu dans un objet de tâche sous Windows ; attend et rend son code."""
    job = _kill_on_close_job() if sys.platform == "win32" else None
    process = subprocess.Popen(  # liste d'arguments, sans shell
        list(args),
        env=dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,  # `--log` : le passage écrit lui-même son journal
        stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if sys.platform == "win32" and job is not None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        kernel32.AssignProcessToJobObject(job, int(process._handle))  # type: ignore[attr-defined]
    return process.wait()


def main() -> int:
    exe, env = spawn.current_interpreter()
    return run_held(command(exe), env)


if __name__ == "__main__":
    sys.exit(main())
