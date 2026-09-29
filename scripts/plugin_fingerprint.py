"""Empreinte des fichiers du plugin (T06b, décision D8) : squelette."""

from __future__ import annotations

from pathlib import Path


def files(plugin: Path) -> list[Path]:
    raise NotImplementedError("T06b : empreinte du plugin")


def compute(plugin: Path) -> str:
    raise NotImplementedError("T06b : empreinte du plugin")
