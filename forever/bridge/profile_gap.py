"""Écart entre le jeu et le profil joueur (P06b, bloc C, décisions 122 et 235)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Gap:
    field: str
    profile: Any
    game: Any


def game_fields(resolved: Any) -> dict[str, Any]:
    raise NotImplementedError


def profile_gaps(resolved: Any, profile: Mapping[str, Any] | None) -> list[Gap]:
    raise NotImplementedError


def gap_fingerprint(gaps: Sequence[Gap]) -> str:
    raise NotImplementedError


def gap_card(name: str, realm: str | None, gaps: Sequence[Gap], *, create: bool) -> dict[str, Any]:
    raise NotImplementedError


class ProfileWatch:
    def __init__(self, *, data: Any, deps: Any, store: Any, now: Any) -> None:
        raise NotImplementedError
