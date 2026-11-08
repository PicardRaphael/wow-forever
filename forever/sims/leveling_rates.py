"""Temps pour tuer et XP par heure par tranche (SIM2, plan 3c), ajoutés aux lignes de `run_brackets` : aucun calcul
ici, seulement les fonctions du moteur (`forever/engine/`) appliquées au DPS de chaque ligne.

- PV d'un monstre normal du niveau : `mob_hp` (`monsters.json`, mesure des journaux, sinon Questie corrigé) ;
- temps pour tuer : `time_to_kill` (PV / DPS de la ligne) ;
- XP d'un monstre de même niveau : `mob_kill_xp` (`PerKill` du client, `character_scaling.json`) ;
- temps hors combat : course entre deux monstres du moteur du Mage (`leveling.defaults.run_between_s`) ;
- XP par heure : `grind_xp_per_hour`.

Le repos (mana et vie) n'est pas compté : le repos du moteur (`downtime`) demande la mana dépensée et les dégâts
subis, que wowsims ne rend pas ; l'XP par heure est donc un plafond, dit dans la provenance."""

from __future__ import annotations

from typing import Any

from forever.config import Deps
from forever.engine.model import GameData
from forever.engine.monsters import grind_xp_per_hour, mob_hp, time_to_kill
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
        "surestimée (plafond, suppose)"
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
        if "error" in row or row.get("dps") is None:
            continue
        row.update(row_rates(gd, int(row["level"]), float(row["dps"])))
    out["provenance"]["assumptions"] = [*out["provenance"]["assumptions"], *NOTES]
    return out
