"""Statistiques de base au niveau du personnage pour wowsims corrigé (SIM2 bloc 4, décision 305 ; correctif
`0003-base-stats`) : aucun calcul de jeu ici, seulement le fichier que le binaire lit.

- Mana de base et critique par point d'Intelligence ou d'Agilité : tables du client au niveau
  (`character_scaling.json`, PlayerExpectedStat), en pour cent comme wowsims les compte (la donnée est une fraction).
- Attributs sans équipement : relevés en jeu (ForeverLogger), transmis tels quels ; le correctif retire l'écart de race
  de wowsims et interpole entre eux et ses tables du niveau 60 (`suppose`).
- Familiers (correctif `0006-pets`) : valeurs de créature du client au niveau (`character_scaling.json`, bloc
  `creature`, ExpectedStat), passées à part par `run_sim` (`--forever-pet-stats=`) ; sans elles, valeurs du 60."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.sims.wowsims import PETS_KEY, PETS_PATCH

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
    class_token: str,
    scaling: Mapping[str, float],
    anchors: Sequence[Mapping[str, Any]],
    pets: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Fichier lu par le correctif 0003-base-stats (`--forever-base-stats=`). `pets` : valeurs de créature au niveau,
    que `run_sim` sépare dans le fichier du correctif 0006-pets (`--forever-pet-stats=`)."""
    doc: dict[str, Any] = {"class": class_token, **scaling, "anchors": [dict(a) for a in anchors]}
    if pets is not None:
        doc[PETS_KEY] = dict(pets)
    return doc


PET_KEYS = {"health": "creature_health", "armor": "creature_armor", "auto_attack_dps": "creature_auto_attack_dps"}


def pet_stats_at(scaling: Mapping[str, Any], level: int) -> dict[str, float] | None:
    """Valeurs de créature du client au niveau (bloc `creature` de character_scaling.json), clés du correctif
    0006-pets ; None si les données n'ont pas encore ce bloc (familiers aux valeurs du niveau 60, rien d'inventé)."""
    creature = scaling.get("creature")
    if not isinstance(creature, Mapping) or not all(k in creature for k in PET_KEYS):
        return None
    return {name: float(creature[key][level - 1]) for key, name in PET_KEYS.items()}


def client_pet_stats(deps: Deps, level: int) -> dict[str, float] | None:
    """Valeurs de créature au niveau, lues dans les données installées (voir `pet_stats_at`)."""
    from forever.store import load_version

    return pet_stats_at(load_version(deps).read_json(CHARACTER_FILE), level)


def pet_note(pets: Mapping[str, float] | None, level: int, *, pinned: bool) -> str:
    """Ce que valent les familiers (Chasseur, Démoniste) au niveau du calcul."""
    if not pinned:
        return f"familiers aux valeurs du niveau 60 : binaire sans le correctif {PETS_PATCH} (lancer `forever sims update`)"
    if level >= 60:
        return "familiers aux valeurs de créature du niveau 60 (client)"
    if pets is None:
        return (f"familiers aux valeurs du niveau 60 (surestimés au niveau {level}) : valeurs de créature par niveau "
                f"absentes de {CHARACTER_FILE} (relancer `forever update`)")  # fmt: skip
    return f"familiers aux valeurs de créature du client au niveau {level} (ExpectedStat)"


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


ATTRIBUTES = ("strength", "agility", "stamina", "intellect", "spirit")
RACE_FILES = {"Scourge": "Undead"}  # nom de fichier de race du client -> nom du proto de wowsims, s'ils diffèrent
LOGGER_GLOB = "WTF/Account/*/SavedVariables/ForeverLogger.lua"


def anchors_from_logger(db: Any, class_token: str) -> list[dict[str, Any]]:
    """Relevés complets des personnages de la classe (`ClassMage` <- `MAGE`) : valeur sans équipement de chaque
    attribut (effectif - bonus - malus de UnitStat), un point par race et niveau (le plus récent), triés par niveau."""
    from forever.sims.wowsims import race_enum

    wanted = class_token.removeprefix("Class").upper()
    best: dict[tuple[int, str], tuple[int, dict[str, Any]]] = {}
    for character in db.characters.values():
        if (character.class_ or "").upper() != wanted or not character.race:
            continue
        race = race_enum(RACE_FILES.get(character.race, character.race))
        for snap in character.snapshots:
            attrs = snap.attributes or {}
            if snap.level is None or any(
                not {"effective", "pos", "neg"} <= set(attrs.get(a) or {}) for a in ATTRIBUTES
            ):
                continue
            point = {"level": snap.level, "race": race}
            for a in ATTRIBUTES:
                v = attrs[a]
                point[a] = v["effective"] - v["pos"] - v["neg"]
            key, when = (snap.level, race), snap.time or 0
            if key not in best or when >= best[key][0]:
                best[key] = (when, point)
    return [p for _, p in sorted(best.values(), key=lambda wp: (wp[1]["level"], wp[1]["race"]))]


def logger_anchors(deps: Deps, class_token: str) -> tuple[list[dict[str, Any]], list[Any]]:
    """Points d'appui lus dans toutes les SavedVariables de ForeverLogger du dossier du jeu (lecture sur disque) ;
    ([], []) sans dossier du jeu."""
    from forever.pipeline.addon_sv import read_logger_db

    if deps.wow_dir is None:
        return [], []
    files = sorted(deps.wow_dir.glob(LOGGER_GLOB))
    merged: dict[tuple[int, str], dict[str, Any]] = {}
    for path in files:
        for point in anchors_from_logger(read_logger_db(path), class_token):
            merged[(point["level"], point["race"])] = point
    return [merged[k] for k in sorted(merged)], files
