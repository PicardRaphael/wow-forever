"""Talents Forever installé (FA1, décision 209) : disposition de ses listes de talents, table de correspondance avec
nos talents, export de nos builds en code v6, builds populaires et comparaison.

La table est reconstruite à chaque appel depuis l'addon installé (jamais stockée dans `forever/data/`) ; lecture
locale par `forever/pipeline/lua_table.py`, jamais de Lua exécuté ; rien de l'addon n'est recopié dans le dépôt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps

ADDON_FOLDER = "TalentsForeverBook"


@dataclass(frozen=True)
class TfLayout:
    """Disposition d'une classe : notre clé par position de liste de l'addon (None : sans correspondance)."""

    file: str
    class_name: str
    slug: str
    tree_names: tuple[str, ...]
    trees: tuple[tuple[str | None, ...], ...]
    max_ranks: tuple[tuple[int, ...], ...]
    unmatched: tuple[dict[str, Any], ...] = ()
    renumbered: tuple[dict[str, Any], ...] = ()
    prereq_gaps: tuple[dict[str, Any], ...] = ()
    tree_name_gaps: tuple[dict[str, Any], ...] = ()
    blocked: str | None = None

    @property
    def exportable(self) -> bool:
        return self.blocked is None


@dataclass(frozen=True)
class TfAddon:
    folder: Path
    version: str | None
    head: dict[str, Any]
    fingerprint: str
    game_version: str
    layouts: dict[str, TfLayout]
    checks: tuple[str, ...] = ()
    popular: dict[str, Any] | None = None

    @property
    def supported(self) -> bool:
        raise NotImplementedError


def load_addon(deps: Deps) -> TfAddon | None:
    raise NotImplementedError


def crosscheck_report(addon: TfAddon) -> dict[str, Any]:
    raise NotImplementedError


def render_crosscheck(report: dict[str, Any]) -> str:
    raise NotImplementedError
