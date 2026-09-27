"""Installation de l'addon — squelette T04 (tests rouges)."""

from datetime import datetime
from pathlib import Path


class InstallError(Exception):
    pass


def install(src: Path, wow_dir: Path, *, dry_run: bool, now: datetime) -> list[str]:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError
