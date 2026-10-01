"""Veille des notes officielles du forum de Blizzard (T08b, bloc F). Squelette."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps

ROBOTS_URL = "https://us.forums.blizzard.com/robots.txt"


def category_url(category_id: int) -> str:
    raise NotImplementedError


def topic_url(topic_id: int) -> str:
    raise NotImplementedError


def read_notes(deps: Deps, state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    raise NotImplementedError


def issue_body(note: Mapping[str, Any]) -> str:
    raise NotImplementedError


def state_from_issues(issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    raise NotImplementedError
