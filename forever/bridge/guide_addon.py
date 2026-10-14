"""Repli de livraison d'un guide RestedXP, jeu fermé (RX1, bloc D, décision 266).

Un seul dossier `Interface/AddOns/ForeverRoute/` : `ForeverRoute.toc` (dépend de RXPGuides ; ligne `## Interface`
reprise du `.toc` de ForeverBridge installé, jamais devinée) et `Guide.lua` (`RXPGuides.RegisterGuide([==[…]==])`,
niveau de crochets absent du texte). Écrit seulement jeu fermé, ancien dossier sauvegardé hors des addons, réécrit en
entier ; aucun autre chemin."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

ADDON_NAME = "ForeverRoute"


def bridge_interface(addons: Path) -> str:
    """Valeur `## Interface` du `.toc` de ForeverBridge installé ; InvalidArgumentError s'il manque."""
    raise NotImplementedError


def bracket_level(text: str) -> int:
    """Plus petit nombre de `=` d'une chaîne longue Lua dont la fermeture n'apparaît pas dans `text`."""
    raise NotImplementedError


def guide_lua(text: str) -> str:
    """Contenu de `Guide.lua` : enregistrement du guide auprès de RestedXP (chaîne longue)."""
    raise NotImplementedError


def write_guide_addon(
    addons: Path,
    text: str,
    *,
    game_running: Callable[[], bool],
    backup_dir: Path,
    now: datetime,
) -> Path:
    """Écrit `ForeverRoute/` (jeu fermé seulement) ; rend le dossier écrit. InvalidArgumentError si le jeu tourne."""
    raise NotImplementedError
