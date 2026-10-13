"""Chaîne de quêtes du Cozy Sleeping Bag lue dans les addons installés (T04f, bloc E), en lecture locale :
Naowh Forever Discovery (`NaowhForever_Discovery/Data/SleepingBag.lua` : objets à cliquer, cartes, positions,
quêtes) et FojjiCore Dungeon Journal (`FojjiCore_DungeonJournal/Data/Guides.lua`, clé `sleepingbag` : zones,
positions, titres). Jamais recopiée dans le dépôt (décision 133) ; aucun chiffre de jeu ici."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NAOWH = ("NaowhForever_Discovery", "Data/SleepingBag.lua")
FOJJI = ("FojjiCore_DungeonJournal", "Data/Guides.lua")


@dataclass(frozen=True)
class AddonChain:
    """Chaîne lue dans un addon : niveau conseillé, objet, étapes par camp (« A », « H », ou « * » : les deux)."""

    addon: str
    version: str | None
    level: int | None
    item: int | None
    steps: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    optional: dict[str, Any] | None = None


def read_naowh_chain(addons_dir: Path) -> AddonChain | None:
    raise NotImplementedError


def read_fojji_chain(addons_dir: Path) -> AddonChain | None:
    raise NotImplementedError
