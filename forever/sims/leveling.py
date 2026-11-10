"""Objectif leveling en solo (SIM2 §10, demande du 2026-11-10 : « les builds sont au DPS, pas au leveling : assez de
mana, assez de vie ») : aucun calcul de jeu ici, seulement la composition de la rencontre envoyée à wowsims et la
lecture de sa sortie ; le cycle (combat, course, repos) est fait par le moteur (`forever/engine/monsters.py`).

- Rencontre : une cible normale du niveau du personnage, PV de `monsters.json` (mes journaux, sinon Questie corrigé),
  armure et DPS d'attaque d'ExpectedStat (`character_scaling.json`, bloc `creature`), coups sans écart ni puissance
  d'attaque (dégâts par coup = DPS d'attaque × cadence), joueur déclaré tank pour que la cible le frappe ; la durée
  est le temps pour tuer (wowsims n'arrête pas le combat à la mort de la cible : amorce, puis PV / DPS de l'amorce).
- Sonde : un tirage d'une itération avec le journal de débogage et une rotation vide : mana et vie maximales
  (« of N total ») et régénération de mana hors incantation (tics `{OtherID: 2, Tag: 2}` de wowsims)."""

from __future__ import annotations

import copy
import re
import statistics
from collections.abc import Mapping
from itertools import pairwise
from typing import Any

from forever.engine.model import GameData

MODEL = "leveling-1"  # version du modèle d'objectif, dans la clé de l'analyse gardée (une analyse au DPS est périmée)
OBJECTIVES = ("leveling", "dps")  # solo : XP par heure avec repos (défaut des outils) ; DPS du combat de référence
STAT_ARMOR, STAT_HEALTH = 27, 29  # indices de StatArmor et StatHealth dans l'enum Stat du proto de wowsims
DEFAULT_SWING_S = 2.0  # cadence de la cible de référence de wowsims (swingSpeed), si la rencontre n'en donne pas
PRIME_S = 30.0  # durée de l'amorce (paramètre du calcul, pas une valeur du jeu) avant la durée au temps pour tuer
PROBE_S = 4.0  # durée de la sonde de repos : tics de régénération et au moins un coup reçu (vie maximale)
EXECUTE_20, EXECUTE_35 = 0.2, 0.35  # part du combat sous 20 % et 35 % de vie à DPS constant (seuils des sorts)
TANK = [{"type": "Player", "index": 0}]

_TOTAL = re.compile(r"(mana|health) .*\(([\d.]+) --> ([\d.]+)\) of ([\d.]+) total")
_TICK = re.compile(r"^\[(-?[\d.]+)\].*Gained ([\d.]+) mana from \{OtherID: 2, Tag: 2\}")


def mob_from(gd: GameData, scaling: Mapping[str, Any], level: int) -> dict[str, Any] | None:
    """Monstre normal du niveau : PV (`mob_hp`), armure et DPS d'attaque d'ExpectedStat ; None si l'un manque."""
    from forever.engine.monsters import mob_hp
    from forever.sims.base_stats import pet_stats_at

    creature = pet_stats_at(scaling, level)
    if creature is None:
        return None
    try:
        hp = mob_hp(gd, level)
    except ValueError:
        return None
    return {"hp": float(hp.value), "armor": creature["creature_armor"],
            "auto_attack_dps": creature["creature_auto_attack_dps"], "certainty": hp.certainty,
            "source": f"PV : {hp.source} ; armure et DPS d'attaque : ExpectedStat du client"}  # fmt: skip


def leveling_encounter(
    reference: Mapping[str, Any] | None, level: int, mob: Mapping[str, Any], *, duration: float
) -> dict[str, Any]:
    """Rencontre d'un monstre du niveau (voir le module) de durée `duration`, sans variation."""
    ref_target = dict(((reference or {}).get("targets") or [{}])[0])
    swing = float(ref_target.get("swingSpeed") or DEFAULT_SWING_S)
    stats = [0.0] * max(len(ref_target.get("stats") or []), STAT_HEALTH + 1)
    stats[STAT_ARMOR] = float(mob["armor"])
    stats[STAT_HEALTH] = float(mob["hp"])
    target = {k: copy.deepcopy(v) for k, v in ref_target.items() if k in ("id", "name", "mobType")}
    target.update({"level": level, "stats": stats, "minBaseDamage": float(mob["auto_attack_dps"]) * swing,
                   "damageSpread": 0, "swingSpeed": swing, "canCrush": False})  # fmt: skip
    return {"duration": duration, "durationVariation": 0, "executeProportion20": EXECUTE_20,
            "executeProportion35": EXECUTE_35, "targets": [target]}  # fmt: skip


def as_tank(request: dict[str, Any]) -> dict[str, Any]:
    """Requête dont le joueur est le tank de la rencontre : la cible le frappe."""
    out = copy.deepcopy(request)
    out["raid"]["tanks"] = copy.deepcopy(TANK)
    return out


def as_probe(request: dict[str, Any]) -> dict[str, Any]:
    """Requête de la sonde : une itération, journal de débogage, rotation vide (rien n'est lancé)."""
    out = copy.deepcopy(request)
    out["simOptions"] = {**out.get("simOptions", {}), "iterations": 1, "debugFirstIteration": True}
    out["raid"]["parties"][0]["players"][0]["rotation"] = {"type": "TypeAPL"}
    return out


def pools_from_logs(logs: str) -> dict[str, Any]:
    """Mana et vie maximales et régénération de mana hors incantation (médiane des tics) lues dans le journal."""
    pools: dict[str, Any] = {"max_mana": None, "max_hp": None, "rest_mana_per_s": 0.0}
    ticks: list[tuple[float, float]] = []
    for line in logs.splitlines():
        m = _TOTAL.search(line)
        if m:
            key = "max_mana" if m.group(1) == "mana" else "max_hp"
            pools[key] = max(float(m.group(4)), pools[key] or 0.0)
        t = _TICK.search(line)
        if t:
            ticks.append((float(t.group(1)), float(t.group(2))))
    rates = [amount / (t1 - t0) for (t0, _), (t1, amount) in pairwise(ticks) if t1 > t0]
    if rates:
        pools["rest_mana_per_s"] = statistics.median(rates)
    return pools


NOTES = (
    (
        "objectif leveling (solo) : un monstre normal du niveau (PV de monsters.json ; armure et DPS d'attaque "
        "d'ExpectedStat du client, multiplicateur de créature normale pris à 1, suppose) qui frappe le joueur ; durée = "
        "temps pour tuer (amorce puis PV / DPS) ; part du combat sous 20 % et 35 % de vie à DPS constant"
    ),
    (
        "repos : boisson et repas conjurés du niveau (spells.json du Mage, pris pour toutes les classes : suppose) plus la "
        "régénération hors incantation de wowsims (sonde) pour la mana, leveling.rest_hp_regen_fraction pour la vie ; "
        "régénération aussi pendant la course entre deux monstres ; soins entre les combats non comptés"
    ),
    (
        "classement en solo : rotations à l'XP par heure avec repos (le DPS reste affiché) ; armes et poids des "
        "statistiques mesurés au DPS sur la rencontre de leveling"
    ),
)
