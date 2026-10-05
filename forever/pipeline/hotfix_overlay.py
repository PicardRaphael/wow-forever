"""Valeurs des correctifs du serveur appliquées aux tables du build en mode forever (T08c, bloc C).

Les entrées applicables de `DBCache.bin` (poussées réelles, `VALID` et `DELETE`, la plus haute poussée l'emportant)
sont décodées selon la disposition de WoWDBDefs du build, validée table par table contre le CSV du build
(`forever.pipeline.dbd.validate_layout`), puis superposées aux lignes lues par les décodeurs : une ligne `VALID`
remplace celle de même identifiant ou s'ajoute, une ligne `DELETE` est retirée (absente : listée). Une table sans
disposition validée n'est jamais appliquée ; si l'une de ses entrées vise une ligne lue par un décodeur, le décodage
est refusé. La valeur d'un correctif vaut pour le build du client qui l'a reçue : un `DBCache.bin` d'un autre build
est refusé. Origine des valeurs appliquées : `correctif_serveur` (`origins.json`), avec poussées et date vue par le
client (journal des correctifs). Aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.pipeline.dbcache import DBCache, Resolved
from forever.pipeline.dbd import Layout, LayoutCheck
from forever.pipeline.tables import Row

SERVER_ORIGIN = "correctif_serveur"
HOTFIX_KEY = "hotfix"


class HotfixSource(NamedTuple):
    path: Path
    locale: str
    cache: DBCache
    resolved: Resolved
    names: dict[int, str]
    layouts: dict[str, Layout]
    dbd: dict[str, Any]  # repo, commit, empreintes des `.dbd`
    seen_at: dict[int, str | None]  # poussée -> première ligne du journal du même build (heure locale du client)
    read_at: str


class Applied(NamedTuple):
    table: str
    rec_id: int
    status: str  # VALID ou DELETE
    push_id: int
    unique_id: int
    seen_at: str | None
    before: Row | None
    after: Row | None


class Overlay(NamedTuple):
    tables: dict[str, list[Row]]
    applied: list[Applied]
    listed: dict[str, Any]
    checks: dict[str, LayoutCheck]


def hotfix_source(
    path: Path,
    layouts: Mapping[str, Layout],
    dbd: Mapping[str, Any],
    journal: Sequence[Mapping[str, Any]],
    version: str,
    rules: Mapping[str, Any],
    read_at: str,
    *,
    locale: str = "enUS",
) -> HotfixSource:
    raise NotImplementedError


def load_dbd_layouts(cache_dir: Path, version: str, tables: Sequence[str]) -> tuple[dict[str, Layout], dict[str, Any]]:
    raise NotImplementedError


def apply_hotfixes(
    tables: Mapping[str, Sequence[Row]],
    source: HotfixSource,
    csv_dir: Path,
    *,
    schemas: Mapping[str, str] | None = None,
) -> Overlay:
    raise NotImplementedError
