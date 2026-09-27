"""Construction de `GameData` depuis les fichiers d'une version (seul module qui lit le JSON brut du moteur).

Le moteur reste pur : il reçoit `GameData` en paramètre. Tout écart de schéma lève `DataSchemaError`."""

from __future__ import annotations

from forever.config import Deps
from forever.engine.model import GameData
from forever.store import VersionData

MECHANICS_FILE = "mechanics.json"


def build_game_data(version: VersionData) -> GameData:
    """Données typées d'une version déjà vérifiée ; lève DataSchemaError si une clé manque ou a un mauvais type."""
    raise NotImplementedError


def load_game_data(deps: Deps) -> GameData:
    """Version courante, après contrôle d'intégrité (DataIntegrityError, ManifestMissingError)."""
    raise NotImplementedError
