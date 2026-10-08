"""Autotest de la bande (P06a, bloc A) : hors jeu, la bande de test dessinée puis relue ; en jeu (`--live`), la bande
de `/fv test` capturée dans la fenêtre du jeu et comparée cellule par cellule à la bande attendue. Le rapport détaille
chaque étape (fenêtre, zone client, premier plan, sonde, décodage) : c'est l'instrument de la sonde en jeu."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from forever.bridge.capture import GameWindow, Rect, WindowsCapture, band_rect, probe_rect
from forever.bridge.codec import (
    CELLS_PER_ROW,
    MARKER_CELLS,
    SELFTEST_ID,
    BandError,
    Decoded,
    cell_mismatches,
    cell_values,
    decode_band,
    encode_cells,
    marker_present,
    render_band,
    selftest_payload,
)
from forever.bridge.image import write_bmp


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
        decoded: dict[str, Any] | None
        if isinstance(self.decoded, Decoded):
            decoded = {"message_id": self.decoded.message_id, "bytes": len(self.decoded.payload)}
        elif isinstance(self.decoded, BandError):
            decoded = {"error": self.decoded.reason}
        else:
            decoded = None
        return {
            "ok": self.ok,
            "lines": list(self.lines),
            "window": asdict(self.window) if self.window is not None else None,
            "client": asdict(self.client) if self.client is not None else None,
            "foreground_seen": self.foreground_seen,
            "marker_seen": self.marker_seen,
            "probe_cells": self.probe_cells,
            "decoded": decoded,
            "mismatches": len(self.mismatches) if self.mismatches is not None else None,
            "first_mismatches": [
                {"row": r, "column": c, "expected": e, "read": g} for r, c, e, g in (self.mismatches or [])[:_SHOWN]
            ],
            "saved": str(self.saved) if self.saved is not None else None,
        }


_SHOWN = 5


def _expected() -> tuple[bytes, list[int]]:
    payload = selftest_payload()
    return payload, encode_cells(SELFTEST_ID, payload)


def _verdict(report: SelftestReport, payload: bytes, cells: list[int]) -> None:
    """Conclusion du rapport d'après le décodage et la comparaison des cellules."""
    rows = -(-len(cells) // CELLS_PER_ROW)
    decoded = report.decoded
    if decoded == Decoded(SELFTEST_ID, payload) and not report.mismatches:
        report.ok = True
        report.lines.append(f"vecteur reconnu ({len(payload)} octets, {rows} rangées, {len(cells)} cellules)")
        return
    if isinstance(decoded, Decoded):
        report.lines.append(
            f"message lu mais ce n'est pas la bande de test (message {decoded.message_id}, "
            f"{len(decoded.payload)} octets) : taper /fv test"
        )
    elif isinstance(decoded, BandError):
        report.lines.append(f"bande rejetée ({decoded.reason})")
    if report.mismatches and isinstance(decoded, BandError):
        shown = " ; ".join(
            f"rangée {r}, colonne {c} (attendue {e}, lue {g})" for r, c, e, g in report.mismatches[:_SHOWN]
        )
        report.lines.append(f"{len(report.mismatches)} cellule(s) différente(s) : {shown}")


def selftest_offline() -> SelftestReport:
    """Bande de test dessinée en mémoire puis décodée."""
    payload, cells = _expected()
    image = render_band(cells)
    report = SelftestReport(decoded=decode_band(image), mismatches=cell_mismatches(image, cells))
    report.lines.append("Bande de test dessinée hors jeu puis relue :")
    _verdict(report, payload, cells)
    return report


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
    payload, cells = _expected()
    report = SelftestReport()
    deadline = clock() + wait_s
    while True:
        late = clock() >= deadline
        if capture.window is None and capture.find() is None:
            if late:
                break
            sleep(1.0)
            continue
        if report.window is None:
            window = report.window = capture.window
            assert window is not None
            report.lines.append(f"Fenêtre du jeu : {window.executable} (pid {window.pid}) « {window.title} »")
        client = capture.client()
        if client is not None and client != report.client:
            report.client = client
            report.lines.append(f"Zone client : {client.width} × {client.height} en ({client.left}, {client.top})")
        if client is None or not capture.allowed():
            if late:
                break
            sleep(interval_s)
            continue
        if not report.foreground_seen:
            report.foreground_seen = True
            report.lines.append("Jeu au premier plan : lecture de la sonde du marqueur")
        probe_r, band_r = probe_rect(client), band_rect(client)
        if probe_r is None or band_r is None:
            report.lines.append("zone client plus petite que la sonde : agrandir la fenêtre du jeu")
            return report
        probe = capture.grab(probe_r)
        if probe is not None:
            report.probe_cells = cell_values(probe, 1)[: len(MARKER_CELLS)]
            if marker_present(probe):
                band = capture.grab(band_r)
                if band is not None:
                    report.marker_seen = True
                    report.decoded = decode_band(band)
                    report.mismatches = cell_mismatches(band, cells)
                    if save is not None:
                        write_bmp(band, save)
                        report.saved = save
                    break
        if late:
            break
        sleep(interval_s)
    if report.window is None:
        report.lines.append("fenêtre du jeu introuvable : lancer le jeu (mode fenêtré ou plein écran fenêtré)")
    elif not report.foreground_seen:
        report.lines.append(
            f"le jeu n'est jamais passé au premier plan en {wait_s:g} s : rien n'a été lu "
            "(capture permise seulement quand le jeu est au premier plan)"
        )
    elif not report.marker_seen:
        read = ", ".join(str(v) for v in report.probe_cells or [])
        report.lines.append(f"marqueur absent : sonde lue [{read}], attendu [6, 1, 6, 1, 5] ; taper /fv test en jeu")
    else:
        _verdict(report, payload, cells)
    if report.saved is not None:
        report.lines.append(f"bande enregistrée : {report.saved}")
    return report
