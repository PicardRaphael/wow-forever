"""Contrôle statique des règles de l'addon — squelette T04 (tests rouges)."""

from pathlib import Path


def check_lua(path: Path) -> list[str]:
    raise NotImplementedError


def check_toc(path: Path) -> list[str]:
    raise NotImplementedError


def check_addon(directory: Path) -> list[str]:
    raise NotImplementedError
