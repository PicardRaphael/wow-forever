"""Vérification d'une version de données (dépôt ou candidate), sans chiffre de jeu.

Contrôles : intégrité du manifeste (DataIntegrityError), schéma du moteur (`build_game_data`), puis cohérence :
`len(ranks) == max` pour chaque talent, prérequis existant dans le même arbre à un palier inférieur, position
(arbre, palier, colonne) unique, rangs de sort de longueur `len(rank_format)` et de niveau croissant, chaque fichier
décrit dans `sources.json` avec une certitude valide. Les fichiers hérités (`inherited_from`) sont listés."""

from __future__ import annotations

from typing import TypedDict

from forever.config import Deps
from forever.provenance import Provenance
from forever.store import VersionData


class VerifyReport(TypedDict):
    version: str
    source: str
    ok: bool
    errors: list[str]
    warnings: list[str]
    inherited: list[str]
    provenance: Provenance


def check_version(v: VersionData) -> tuple[list[str], list[str], list[str]]:
    """(erreurs, avertissements, fichiers hérités) d'une version déjà chargée."""
    raise NotImplementedError


def verify_version(deps: Deps, source: str | None = None) -> VerifyReport:
    """`source` : identifiant de version du dépôt ou chemin d'une candidate (défaut : version locale courante)."""
    raise NotImplementedError
