"""Sources locales des trajets et des maîtres de classe d'une feuille de route (RX1, bloc F, décision 133).

Lus en local dans les addons installés, jamais recopiés dans le dépôt :

- Naowh Forever Journeys (droits réservés) : bateaux, zeppelins, portails et tram (`Data/Network.lua`), vitesses
  et frais d'embarquement (`Constants.lua`), graphe de marche par continent (`NaowhForever_JourneysData/Data/
  Map<continent>.lua` : base64, deflate, CBOR ; nœuds en yards du monde, arêtes pondérées en yards de marche) ;
- Naowh Forever Training : niveaux où la classe apprend de nouveaux sorts (`Data/TrainingData.lua`) ;
- Questie : maîtres de classe (titre « <Classe> Trainer » de `classicNpcDB.lua`) et leurs positions.

Les vols restent ceux du client (`travel.json`, le client prime) ; les durées des transports sont `suppose`."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

JOURNEYS = "NaowhForever_Journeys"
JOURNEYS_DATA = "NaowhForever_JourneysData"
TRAINING = "NaowhForever_Training"


class Dock(NamedTuple):
    continent: int
    x: float
    y: float
    ui_map: int | None
    name: str
    wait: float  # secondes d'attente au quai (valeur de l'addon)
    length: float  # yards jusqu'au quai suivant


class Ship(NamedTuple):
    kind: str  # Boat | Zeppelin
    sides: str  # « A », « H » ou « AH »
    docks: tuple[Dock, ...]


class Link(NamedTuple):
    kind: str  # Portal | Tram
    sides: str
    seconds: float
    a: tuple[int, float, float, str]  # continent, x, y, nom
    b: tuple[int, float, float, str]


class JourneysNetwork(NamedTuple):
    ships: tuple[Ship, ...]
    links: tuple[Link, ...]
    speeds: dict[str, float]  # yards par seconde par sorte de navire
    board_s: float
    loading_s: float
    version: str | None


class TrainerNpc(NamedTuple):
    npc: int
    name: str
    title: str
    sides: str
    ui_map: int
    x: float  # pourcentage de la carte
    y: float


def read_journeys_network(addons: Path) -> JourneysNetwork | None:
    """Transports de Journeys (None si l'addon manque ou ne se lit pas)."""
    raise NotImplementedError


def read_journeys_walks(addons: Path) -> dict[int, tuple[list[tuple[float, float]], list[tuple[int, int, float]]]]:
    """Graphe de marche par continent : (nœuds (x, y), arêtes (a, b, yards), indices de 0) ; vide sans l'addon."""
    raise NotImplementedError


def read_training_levels(addons: Path) -> dict[int, tuple[int, ...]]:
    """Niveaux où chaque classe (identifiant du client) apprend un sort chez son maître (sorts de quête exclus)."""
    raise NotImplementedError


def read_questie_trainers(addons: Path, title: str) -> list[TrainerNpc]:
    """PNJ de Questie dont le titre est exactement `title` (« Mage Trainer »), une position par point d'apparition."""
    raise NotImplementedError
