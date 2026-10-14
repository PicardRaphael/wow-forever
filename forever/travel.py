"""Graphe des trajets d'une feuille de route (RX1, bloc B), assemblé hors du moteur.

Points de vol et trajets de `travel.json` (client, décision 266 : le client prime), filtrés par camp ; cartes de zone
pour convertir une position de carte en position monde. Le moteur (`forever/engine/travel.py`) calcule ensuite les
temps. Registre : I19."""

from __future__ import annotations

from typing import Any

from forever.config import Deps
from forever.engine.travel import Graph, MapRect


def load_travel(deps: Deps, faction: str) -> tuple[Graph, dict[int, MapRect]]:
    """Graphe des vols du camp `faction` (« horde » ou « alliance ») et cartes de zone de la version installée."""
    raise NotImplementedError


def graph_from_doc(doc: dict[str, Any], faction: str) -> tuple[Graph, dict[int, MapRect]]:
    raise NotImplementedError
