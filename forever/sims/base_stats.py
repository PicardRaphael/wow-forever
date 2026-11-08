"""Statistiques de base au niveau du personnage pour wowsims corrigé (SIM2 bloc 4, décision 305 ; correctif
`0003-base-stats`) : aucun calcul de jeu ici, seulement le fichier que le binaire lit.

- Mana de base et critique par point d'Intelligence ou d'Agilité : tables du client au niveau
  (`character_scaling.json`, PlayerExpectedStat), en pour cent comme wowsims les compte (la donnée est une fraction).
- Attributs sans équipement : relevés en jeu (ForeverLogger), transmis tels quels ; le correctif retire l'écart de race
  de wowsims et interpole entre eux et ses tables du niveau 60 (`suppose`)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError

CHARACTER_FILE = "character_scaling.json"
PERCENT = 100  # fraction du client -> pour cent de wowsims
PATCH = "0003-base-stats.patch"


def client_scaling(deps: Deps, class_name: str, level: int) -> dict[str, float]:
    """Mana de base et critique par point (pour cent) de la classe au niveau, lus dans les données du client."""
    from forever.store import load_version

    rows = (load_version(deps).read_json(CHARACTER_FILE).get("classes") or {}).get(class_name)
    if not rows:
        raise InvalidArgumentError(f"{class_name} absent de {CHARACTER_FILE}.", "vérifier la classe (nom anglais)")
    i = level - 1
    return {
        "mana": float(rows["base_mana"][i]),
        "crit_per_int": float(rows["spell_crit_per_intellect"][i]) * PERCENT,
        "crit_per_agi": float(rows["crit_per_agility"][i]) * PERCENT,
    }


def base_stats_doc(
    class_token: str, scaling: Mapping[str, float], anchors: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Fichier lu par le correctif 0003-base-stats (`--forever-base-stats=`)."""
    return {"class": class_token, **scaling, "anchors": [dict(a) for a in anchors]}


def anchor_note(anchors: Sequence[Mapping[str, Any]], level: int) -> str:
    """Ce que valent les attributs sans équipement au niveau : interpolés entre relevés, ou ceux du niveau 60."""
    below = sorted({int(a["level"]) for a in anchors if int(a["level"]) <= level})
    if not below:
        return (f"attributs sans équipement du niveau 60 (aucun relevé ForeverLogger au niveau {level} ou en dessous) : "
                "dégâts surestimés")  # fmt: skip
    above = sorted({int(a["level"]) for a in anchors if level < int(a["level"]) < 60})
    upper = above[0] if above else 60
    return (
        f"attributs sans équipement interpolés entre le relevé ForeverLogger du niveau {below[-1]} et "
        f"{'le relevé du niveau ' + str(upper) if above else 'les tables du niveau 60 de wowsims'} (suppose)"
    )


def anchors_from_logger(db: Any, class_token: str) -> list[dict[str, Any]]:
    raise NotImplementedError


def logger_anchors(deps: Deps, class_token: str) -> tuple[list[dict[str, Any]], list[Any]]:
    raise NotImplementedError
