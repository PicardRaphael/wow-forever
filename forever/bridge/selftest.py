"""Autotest de la bande (P06a, bloc A) : hors jeu, la bande de test dessinée puis relue ; en jeu (`--live`), la bande
de `/fv test` capturée dans la fenêtre du jeu et comparée cellule par cellule à la bande attendue. Le rapport détaille
chaque étape (fenêtre, zone client, premier plan, sonde, décodage) : c'est l'instrument de la sonde en jeu."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.bridge.capture import GameWindow, Rect, WindowsCapture
from forever.bridge.codec import BandError, Decoded


@dataclass
class SelftestReport:
    ok: bool = False
    lines: list[str] = field(default_factory=list)
    window: GameWindow | None = None
    client: Rect | None = None
    foreground_seen: bool = False
    marker_seen: bool = False
    probe_cells: list[int] | None = None
    decoded: Decoded | BandError | None = None
    mismatches: list[tuple[int, int, int, int]] | None = None
    saved: Path | None = None

    def to_json(self) -> dict[str, Any]:
        raise NotImplementedError


def selftest_offline() -> SelftestReport:
    """Bande de test dessinée en mémoire puis décodée."""
    raise NotImplementedError


def selftest_live(
    capture: WindowsCapture,
    *,
    wait_s: float = 60.0,
    interval_s: float = 0.25,
    save: Path | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> SelftestReport:
    """Attend jusqu'à `wait_s` que le jeu soit au premier plan avec la bande de test, puis la lit et la compare."""
    raise NotImplementedError
