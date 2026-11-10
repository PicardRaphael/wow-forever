"""Temps pour tuer et XP par heure par tranche (SIM2, plan 3c), ajoutés aux lignes de `run_brackets` : aucun calcul
ici, seulement les fonctions du moteur (`forever/engine/`) appliquées au DPS de chaque ligne.

- PV d'un monstre normal du niveau : `mob_hp` (`monsters.json`, mesure des journaux, sinon Questie corrigé) ;
- temps pour tuer : `time_to_kill` (PV / DPS de la ligne) ;
- XP d'un monstre de même niveau : `mob_kill_xp` (`PerKill` du client, `character_scaling.json`) ;
- temps hors combat : course entre deux monstres du moteur du Mage (`leveling.defaults.run_between_s`) ;
- XP par heure : `grind_xp_per_hour`.

Objectif DPS (combat de référence) : repos non compté, XP par heure plafond, dit dans la provenance. Objectif leveling
(SIM2 §10, `cycle`) : mana dépensée et dégâts subis lus dans wowsims sur un monstre du niveau, repos par monstre
(`rest_per_kill`) et XP par heure repos compris ; ces lignes gardent leurs champs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.config import Deps
from forever.engine.mana import consumables
from forever.engine.model import GameData
from forever.engine.monsters import (
    grind_xp_per_hour,
    grind_xp_per_hour_rested,
    kills_per_bar,
    mob_hp,
    rest_per_kill,
    time_to_kill,
)
from forever.engine.route import weakest
from forever.engine.xp import mob_kill_xp

NOTES = (
    (
        "temps pour tuer (ttk_s) : PV d'un monstre normal du niveau de la tranche (monsters.json : journaux, sinon Questie "
        "corrigé, certitude par ligne) / DPS de la ligne (wowsims, suppose) ; combat seul, sans soin ni fuite du monstre"
    ),
    (
        "XP par heure (xp_per_hour) : XP d'un monstre de même niveau (PerKill du client, character_scaling.json) sur le "
        "temps pour tuer plus la course entre deux monstres du moteur (leveling.defaults.run_between_s, suppose) ; repos "
        "(mana, vie) entre les combats non compté : wowsims ne rend ni la mana dépensée ni les dégâts subis ; XP par heure "
        "surestimée (plafond, suppose) ; objectif leveling : repos compté (voir les lignes « leveling »)"
    ),
)


def row_rates(gd: GameData, level: int, dps: float) -> dict[str, Any]:
    """Champs ajoutés à une ligne : `ttk_s`, `xp_per_hour` et leurs entrées (`rates`), ou `rates_missing` (raison)."""
    try:
        hp = mob_hp(gd, level)
    except ValueError as exc:
        return {"rates_missing": f"temps pour tuer et XP par heure absents : {exc}"}
    try:
        ttk = time_to_kill(float(hp.value), dps)
    except ValueError as exc:
        return {"rates_missing": f"temps pour tuer et XP par heure absents au niveau {level} : {exc}"}
    out: dict[str, Any] = {"ttk_s": ttk}
    between = gd.leveling.default_run_between_s
    rates: dict[str, Any] = {
        "mob_hp": {"level": level, "value": hp.value, "certainty": hp.certainty, "source": hp.source},
        "between_s": between,
    }
    kill = mob_kill_xp(gd, level, level)
    if level >= gd.level_cap:
        out["rates_missing"] = f"XP par heure absente : niveau {level} au plafond (spell_scaling.json), plus d'XP"
    elif kill.xp <= 0:
        out["rates_missing"] = f"XP par heure absente : aucune XP de monstre connue au niveau {level}"
    else:
        out["xp_per_hour"] = grind_xp_per_hour(kill.xp, ttk, between)
        rates["xp_per_kill"] = {"value": kill.xp, "certainty": weakest(*(t.certainty for t in kill.terms))}
    rates["certainty"] = weakest(hp.certainty, "suppose")  # DPS de wowsims : suppose
    out["rates"] = rates
    return out


def add_rates(deps: Deps, out: dict[str, Any], *, gd: GameData | None = None) -> dict[str, Any]:
    """Ajoute à chaque ligne réussie de `run_brackets` le temps pour tuer et l'XP par heure (voir le module), et les
    hypothèses à la provenance ; les lignes en erreur restent telles quelles."""
    if gd is None:
        from forever.gamedata import build_game_data
        from forever.store import load_version

        gd = build_game_data(load_version(deps))
    for row in out["rows"]:
        if "error" in row or row.get("dps") is None or "leveling" in row:
            continue
        row.update(row_rates(gd, int(row["level"]), float(row["dps"])))
    out["provenance"]["assumptions"] = [*out["provenance"]["assumptions"], *NOTES]
    return out


def cycle(
    gd: GameData, level: int, mob: Mapping[str, Any], out: Mapping[str, Any], pools: Mapping[str, Any], duration: float
) -> dict[str, Any]:
    """Champs d'une ligne en objectif leveling : temps pour tuer (PV / DPS du combat au niveau), ressources par monstre
    (coûts du combat de `duration` secondes ramenés au temps pour tuer), repos par monstre et XP par heure avec et sans
    repos ; `rates_missing` (raison) quand l'XP ou le temps manque."""
    fight = out.get("fight") or {}
    try:
        ttk = time_to_kill(float(mob["hp"]), float(out["dps"]))
    except ValueError as exc:
        return {"objective": "leveling", "rates_missing": f"temps pour tuer absent au niveau {level} : {exc}"}
    scale = ttk / duration if duration > 0 else 1.0
    has_mana = pools.get("max_mana") is not None
    spent = float(fight.get("mana_spent") or 0.0) * scale if has_mana else 0.0
    gained = float(fight.get("mana_gained") or 0.0) * scale if has_mana else 0.0
    taken = float(fight.get("damage_taken") or 0.0) * scale
    regen = float(pools.get("rest_mana_per_s") or 0.0)
    max_hp = float(pools.get("max_hp") or 0.0)
    hp_regen = gd.leveling.rest_hp_regen_fraction * max_hp
    water, food = consumables(gd, level)
    between = gd.leveling.default_run_between_s
    rest, limiter = rest_per_kill(mana_net=spent - gained, mana_regen=regen, mana_rest_rate=water + regen,
                                  hp_lost=taken, hp_regen=hp_regen, hp_rest_rate=food + hp_regen,
                                  between=between)  # fmt: skip
    lv: dict[str, Any] = {
        "mob": dict(mob), "fight_s": duration, "mana_spent": spent, "mana_gained": gained, "damage_taken": taken,
        "max_mana": pools.get("max_mana"), "max_hp": pools.get("max_hp"), "rest_mana_per_s": regen,
        "drink_per_s": water, "food_per_s": food, "rest_s": rest, "limited_by": limiter,
        "kills_per_mana_bar": kills_per_bar(float(pools["max_mana"]), spent - gained - regen * between)
        if has_mana else None,
        "kills_per_hp_bar": kills_per_bar(max_hp, taken - hp_regen * between) if max_hp else None,
        "tto_s": fight.get("tto_s"), "oom_s": fight.get("oom_s"), "death_chance": fight.get("death_chance"),
        "certainty": weakest(str(mob.get("certainty") or "suppose"), "suppose"),
    }  # fmt: skip
    row: dict[str, Any] = {"objective": "leveling", "ttk_s": ttk, "leveling": lv}
    kill = mob_kill_xp(gd, level, level)
    if level >= gd.level_cap or kill.xp <= 0:
        row["rates_missing"] = f"XP par heure absente au niveau {level} (plafond ou XP de monstre inconnue)"
        return row
    row["xp_per_hour"] = grind_xp_per_hour_rested(kill.xp, ttk, between, rest)
    row["xp_per_hour_no_rest"] = grind_xp_per_hour(kill.xp, ttk, between)
    lv["rest_share"] = rest / (ttk + between + rest)
    lv["xp_per_kill"] = kill.xp
    return row
