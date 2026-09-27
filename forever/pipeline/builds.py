"""Seul point d'accès réseau de T01 : versions publiées du client (wago.tools)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from forever.config import HttpGet
from forever.errors import ForeverError

BUILDS_URL = "https://wago.tools/api/builds"


@dataclass(frozen=True)
class Build:
    version: str
    created_at: datetime


class BuildsUnavailable(ForeverError):
    def __init__(self, message: str) -> None:
        super().__init__("builds_unavailable", message, "réessayer plus tard ou vérifier sur https://wago.tools/builds")


def version_key(version: str) -> tuple[int, ...]:
    raise NotImplementedError


def fetch_builds(http_get: HttpGet) -> object:
    raise NotImplementedError


def parse_builds(payload: object, product: str, prefix: str) -> list[Build]:
    raise NotImplementedError


def latest_build(builds: Sequence[Build]) -> Build | None:
    raise NotImplementedError
