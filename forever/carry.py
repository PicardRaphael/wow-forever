"""Report des changements faits à la main d'une version à la suivante (T08d, bloc C, décision 180, clause b).

Une version contient des valeurs qui ne viennent pas du décodage : règles d'origine `manuel` et `journal`
(`origins.json`), changements écrits à la main dans une révision (`manual_changes` de `revisions.json`), état du jeu
relevé en jeu (`meta.json` `game_state`). Avant toute installation automatique, chacune est classée :

- `gardé` : même valeur au même chemin dans la nouvelle version (métadonnées exclues) ;
- `réappliqué` : absente ou différente dans un fichier **hérité** de la nouvelle version, réécrite par `carry_apply` ;
- `remplacé` : le fichier est désormais décodé et le client donne une autre valeur (la valeur du client l'emporte,
  après accord) ;
- `perdu` : absente sans explication (jamais approuvable).

Lecture et écriture locales seulement ; aucun chiffre de jeu ici."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple


class ManualValue(NamedTuple):
    file: str
    pointer: str
    value: Any
    origin: str  # manuel | journal
    revision: int | None
    reason: str


class CarryReport(NamedTuple):
    kept: list[ManualValue]
    reapplied: list[ManualValue]
    superseded: list[tuple[ManualValue, Any]]
    lost: list[ManualValue]


def manual_values(version_dir: Path) -> list[ManualValue]:
    """Valeurs `manuel` et `journal`, chemins des `manual_changes` et `meta.json` `game_state` d'une version."""
    raise NotImplementedError


def carry_check(old_dir: Path, new_dir: Path) -> CarryReport:
    """Classe chaque valeur faite à la main de `old_dir` face à `new_dir`."""
    raise NotImplementedError


def carry_apply(old_dir: Path, new_dir: Path, report: CarryReport) -> list[Path]:
    """Réécrit les valeurs `réappliqué` dans `new_dir` (en octets), puis le manifeste de son dossier de données."""
    raise NotImplementedError
