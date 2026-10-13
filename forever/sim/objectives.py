"""Objectifs de leveling (T04d, bloc F) : XP par heure par zone et par donjon, pour toutes les classes.

Pour un personnage (classe, camp, niveau, repos), chaque zone et chaque donjon accessibles :

- zone : XP des quêtes disponibles non grises (modèle d'XP, `forever/engine/xp.py`) + XP des monstres de leurs
  objectifs, sur le temps total (monstres × temps par monstre + surcoût par quête) ;
- donjon, **premier passage avec quêtes** : XP des monstres (bonus de donjon, élite, groupe) + XP de toutes ses
  quêtes accessibles (prérequis manquants listés), sur le temps total (prise des quêtes, trajet, donjon, retour) ;
- donjon, **passages suivants** : XP des monstres seule, sur la durée du donjon.

Temps par monstre : moteur pour le Mage (simulateur de leveling, analytique), sinon mesuré ou estimé
(`forever/kill_time.py`) ; la source est rendue. Hypothèses de temps (`leveling.objectives` de `mechanics.json`,
`suppose`) : le classement peut en dépendre plus que de l'XP, la sortie le dit. La phrase de conseil est construite
ici à partir des chiffres de l'objectif, jamais par un modèle de langage. Aucun chiffre de jeu ici."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from forever.config import Deps

KINDS = ("zone", "dungeon_first", "dungeon_repeat")


def objectives(
    deps: Deps,
    *,
    class_name: str,
    level: int,
    faction: str | None = None,
    race: str | None = None,
    rested: float = 0.0,
    party: int = 1,
    dungeon_party: int | None = None,
    limit: int = 5,
    wow_dir: Path | None = None,
) -> dict[str, Any]:
    """Objectifs classés par XP par heure, temps par monstre et sa source, conseil, provenance."""
    raise NotImplementedError
