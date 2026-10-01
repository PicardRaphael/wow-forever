"""Lecteur local de l'addon Forever Bestiary et de sa sauvegarde `ForeverBestiaryDB` (CH0, bloc B).

Lecture sur disque seulement, jamais par le réseau ; rien n'est copié dans le dépôt (décision 133 : addon sans
licence, seuls des agrégats). Anonymisation à la lecture : empreintes de joueurs, noms de tiers, GUID et clés
`self*` sont supprimés dès le décodage (liste blanche des champs gardés)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ADDON_NAME = "ForeverBestiary"
SAVED_VARIABLE = "ForeverBestiaryDB"


def read_bestiary(addon_dir: Path) -> dict[str, Any]:
    """Base de l'addon : version, empreinte, date et build de la base, familles, capacités, bêtes, carte
    communautaire (PathNotFoundError si l'addon manque)."""
    raise NotImplementedError


def read_bestiary_saved(path: Path) -> dict[str, Any]:
    """Sauvegarde `ForeverBestiaryDB` : mes observations et mes familiers, sans aucune donnée de tiers."""
    raise NotImplementedError
