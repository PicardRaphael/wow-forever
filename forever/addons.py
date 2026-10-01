"""Versions et empreintes des addons de données (`forever addons status`, T08b, bloc D). Squelette."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.config import Deps

STATE_NAME = "state.json"
DATA_ADDONS: Mapping[str, Any] = {}


def addons_status(deps: Deps, *, save: bool = False) -> dict[str, Any]:
    raise NotImplementedError
