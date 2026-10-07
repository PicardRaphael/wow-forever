"""Journal de combat en cours d'écriture (décision 205, demande de l'utilisateur du 2026-10-07).

`forever update` et `forever measures refresh` ne mesurent un journal que si le jeu est fermé (aucun processus du
client) ou si le journal n'a pas été modifié depuis `LOG_QUIET_S` ; sinon le journal est noté « en cours
d'écriture » et reproposé au passage suivant. Cas réel : le journal du 2026-10-07 a grossi entre la simulation
montrée à l'utilisateur et l'écriture, qui a mesuré des PNJ qu'il n'avait pas vus.

État du jeu : liste des processus du système (`tasklist` sous Windows, `ps` ailleurs), comparée aux exécutables
`Wow*.exe` du dossier du client ; une détection en échec rend None, traité comme « jeu ouvert » (seul le délai de
repos décide). Aucun réseau ; lecture seule."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOG_QUIET_S = 30 * 60  # délai de repos d'un journal quand le jeu est ouvert (réglage de l'outil, décision 205)
DEFAULT_EXECUTABLES = ("WowB.exe", "Wow.exe", "WowClassic.exe", "WowClassicB.exe", "WowClassicT.exe", "WowT.exe")
_TIMEOUT_S = 10


def client_executables(wow_dir: Path | None) -> set[str]:
    """Exécutables du client présents dans son dossier (`Wow*.exe`) ; à défaut, les noms connus des clients."""
    found = {p.name for p in wow_dir.glob("Wow*.exe")} if wow_dir is not None and wow_dir.is_dir() else set()
    return found or set(DEFAULT_EXECUTABLES)


def game_running_from(listing: str, executables: Collection[str]) -> bool:
    """Le client tourne-t-il d'après une liste de processus : sortie CSV de `tasklist` (premier champ entre
    guillemets) ou de `ps -A -o comm=` (un chemin par ligne) ; casse ignorée."""
    wanted = {name.lower() for name in executables}
    for line in listing.splitlines():
        line = line.strip()
        if not line:
            continue
        image = line[1:].split('"', 1)[0] if line.startswith('"') else line.replace("\\", "/").rsplit("/", 1)[-1]
        if image.lower() in wanted:
            return True
    return False


def detect_game_running(wow_dir: Path | None) -> bool | None:
    """État du jeu sur ce poste ; None si la liste des processus est illisible."""
    command = ["tasklist", "/FO", "CSV", "/NH"] if sys.platform == "win32" else ["ps", "-A", "-o", "comm="]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=_TIMEOUT_S, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return game_running_from(done.stdout, client_executables(wow_dir))


def split_live(
    paths: Sequence[Path], *, now: datetime, running: bool | None, quiet_s: int = LOG_QUIET_S
) -> tuple[list[Path], list[dict[str, Any]]]:
    """Journaux à mesurer et journaux en cours d'écriture (nom, âge en secondes depuis la dernière modification).
    Jeu fermé : tout est à mesurer ; jeu ouvert ou état inconnu : un journal modifié depuis moins de `quiet_s` (ou
    daté dans le futur) est tenu."""
    if running is False:
        return list(paths), []
    ready: list[Path] = []
    writing: list[dict[str, Any]] = []
    for path in paths:
        age = (now - datetime.fromtimestamp(path.stat().st_mtime, UTC)).total_seconds()
        if age >= quiet_s:
            ready.append(path)
        else:
            writing.append({"name": path.name, "age_s": round(age)})
    return ready, writing


def writing_note(writing: Sequence[dict[str, Any]]) -> str:
    """Hypothèse de provenance pour les journaux tenus."""
    names = ", ".join(w["name"] for w in writing)
    return (
        f"{len(writing)} journal(aux) en cours d'écriture ({names}) : jeu ouvert et modifié depuis moins de "
        f"{LOG_QUIET_S // 60} min, non mesuré(s), reproposé(s) au passage suivant (décision 205)"
    )
