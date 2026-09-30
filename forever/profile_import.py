"""Import automatique minimal du profil joueur (PV1, bloc A ; décisions 99, 105, 125) : collecte, plan, écriture.

Sources, lues sur disque et jamais par le réseau : ForeverLogger (classe, race, niveau, nœuds de talents du dernier
instantané de chaque GUID), mes journaux de combat (personnages « à moi » ; classe déduite des sorts de classe
lancés, `probable`, si ForeverLogger ne connaît pas le GUID), Questie (quêtes faites, par personnage) et
Auctionator (mes prix, par royaume). Chaque champ garde sa source, sa date (UTC) et la version du client en vigueur
(`client_builds.version_at`, `null` si inconnue) ; la fusion suit `profile.merge_field`. La faction n'est jamais
importée. Rien n'est écrit sans accord : `plan_import` rend les changements, `apply_import` les écrit."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Any, TypedDict

from forever.config import Deps
from forever.provenance import Provenance
from forever.store import VersionData

LOGGER_FILE = "ForeverLogger.lua"
QUESTIE_FILE = "Questie.lua"
AUCTIONATOR_FILE = "Auctionator.lua"


class ImportPlan(TypedDict):
    status: str
    changes: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    sources: dict[str, str | None]
    notes: list[str]
    doc: dict[str, Any]
    provenance: Provenance


def class_spell_index(data: VersionData) -> dict[int, str]:
    """Identifiant de sort -> classe (nom anglais du client), d'après les sorts de classe des données."""
    raise NotImplementedError


def plan_import(
    deps: Deps,
    *,
    sv_dir: Path | None,
    logs_dir: Path | None,
    utc_offset: timedelta | None = None,
    class_spells: Mapping[int, str] | None = None,
) -> ImportPlan:
    """Changements que l'import apporterait au profil, sans rien écrire. `class_spells` : index sort -> classe
    (défaut : `class_spell_index` des données courantes)."""
    raise NotImplementedError


def apply_import(deps: Deps, plan: ImportPlan) -> None:
    """Écrit le profil planifié (après accord)."""
    raise NotImplementedError
