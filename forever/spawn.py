"""Lancement détaché d'un passage de `forever update` (T08d, blocs E et G).

Le passage tourne dans un processus séparé, sans fenêtre et sans bloquer la session ni la commande qui le lance ; sa
sortie va dans `<cache>/update/run-<horodatage>.log`. Aucun réseau ici : c'est le passage lancé qui y accède, par
`forever/pipeline/`."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Drapeaux de Windows : processus détaché, nouveau groupe (Ctrl+C de la session ne le tue pas), sans fenêtre.
_DETACHED = 0x00000008 | 0x00000200 | 0x08000000


def update_command(*extra: str) -> list[str]:
    """`python -m forever update --auto --json …` avec l'interpréteur de l'installation courante."""
    return [sys.executable, "-m", "forever", "update", "--auto", "--json", *extra]


def spawn_detached(args: Sequence[str], log_path: Path) -> None:
    """Lance `args` détaché, sortie dans `log_path` ; lève OSError si le lancement échoue (l'appelant l'attrape)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        if os.name == "nt":
            subprocess.Popen(  # liste d'arguments, sans shell
                list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=_DETACHED, close_fds=True
            )
        else:
            subprocess.Popen(  # liste d'arguments, sans shell
                list(args), stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True
            )
