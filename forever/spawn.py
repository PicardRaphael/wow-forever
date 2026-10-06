"""Lancement détaché d'un passage de `forever update` (T08d, blocs E et G).

Le passage tourne dans un processus séparé, sans fenêtre et sans bloquer la session ni la commande qui le lance ; sa
sortie va dans `<cache>/update/run-<horodatage>.log`, écrite au fil de l'eau (`python -u`). Aucun réseau ici : c'est
le passage lancé qui y accède, par `forever/pipeline/`.

Un relais coupe la filiation (correctif du 2026-10-06) : la commande qui lance (hook, `forever update approve`)
démarre un relais, qui démarre le passage puis se termine aussitôt, avant que la commande reprenne la main. Le
passage n'a plus alors de parent vivant : la fin de l'arbre de processus qui l'a lancé (session fermée,
`taskkill /T`, groupe de processus tué) ne l'atteint plus. Sonde du 2026-10-06 : sans relais, `taskkill /T` sur la
commande tuait aussi le passage, malgré `DETACHED_PROCESS`."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Drapeaux de Windows : processus détaché, nouveau groupe (Ctrl+C de la session ne le tue pas), sans fenêtre.
_DETACHED = 0x00000008 | 0x00000200 | 0x08000000
_BREAKAWAY_FROM_JOB = 0x01000000  # hors de l'objet job du lanceur, quand le job le permet
_NO_WINDOW = 0x08000000
_RELAY_TIMEOUT_S = 60.0
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5


def update_command(*extra: str) -> list[str]:
    """`python -u -m forever update --auto --json …` avec l'interpréteur de l'installation courante ; `-u` : sortie
    écrite sans tampon dans le journal du passage."""
    return [sys.executable, "-u", "-m", "forever", "update", "--auto", "--json", *extra]


def spawn_detached(args: Sequence[str], log_path: Path) -> None:
    """Lance `args` détaché par un relais (voir le module), sortie dans `log_path` ; rend la main une fois le relais
    terminé. Lève OSError si le lancement échoue (l'appelant l'attrape)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    relay = [sys.executable, "-m", "forever.spawn", str(log_path), *args]
    flags = _NO_WINDOW if sys.platform == "win32" else 0
    try:
        done = subprocess.run(  # liste d'arguments, sans shell
            relay,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=_RELAY_TIMEOUT_S,
            check=False,
            creationflags=flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise OSError(f"relais du lancement détaché sans réponse après {_RELAY_TIMEOUT_S:.0f} s") from exc
    if done.returncode != 0:
        detail = (done.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
        raise OSError(f"relais du lancement détaché en échec ({done.returncode}) : {detail[-1] if detail else '?'}")


def _launch(args: Sequence[str], log_path: Path) -> None:
    """Démarre `args` détaché, sortie dans `log_path` (dans le relais)."""
    with log_path.open("ab") as log:
        if sys.platform == "win32":
            try:  # hors du job du lanceur s'il le permet, sinon dans le job (refus : OSError)
                subprocess.Popen(  # liste d'arguments, sans shell
                    list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                    creationflags=_DETACHED | _BREAKAWAY_FROM_JOB, close_fds=True,
                )  # fmt: skip
            except OSError:
                subprocess.Popen(  # liste d'arguments, sans shell
                    list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=_DETACHED,
                    close_fds=True,
                )  # fmt: skip
        else:
            subprocess.Popen(  # liste d'arguments, sans shell
                list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True
            )


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


if __name__ == "__main__":  # relais : `python -m forever.spawn <journal> <commande…>`
    if len(sys.argv) < 3:
        sys.stderr.write("usage : python -m forever.spawn <journal> <commande…>\n")
        sys.exit(2)
    _launch(sys.argv[2:], Path(sys.argv[1]))
    sys.exit(0)
