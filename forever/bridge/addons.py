"""Conversation « addons » du pont (P06b, bloc F, décision 235)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ADDONS_TIMEOUT_S = 600.0
GIT_SUBCOMMANDS = ("init", "add", "commit", "status", "diff", "log", "rev-parse")


@dataclass(frozen=True)
class AddonsConfig:
    source: Path
    deploy: Path | None = None


def check_folder(path: Path, addons_dir: Path) -> None:
    raise NotImplementedError


def snapshot(config: AddonsConfig, cache_dir: Path, stamp: str) -> Path:
    raise NotImplementedError


def commit(config: AddonsConfig, message: str, *, run: Any = subprocess.run) -> Any:
    raise NotImplementedError


def deploy(config: AddonsConfig) -> Any:
    raise NotImplementedError


def restore(config: AddonsConfig, cache_dir: Path, stamp: str | None, now: str) -> Any:
    raise NotImplementedError


class AddonsTurn:
    def __init__(self, **kwargs: Any) -> None:
        raise NotImplementedError
