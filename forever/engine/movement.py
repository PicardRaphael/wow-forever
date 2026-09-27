"""Déplacements du combat de leveling : temps de vol, course du monstre, ralentis, gel, portée, cadence des coups."""

from __future__ import annotations

from forever.engine.model import GameData, Points, Rank
from forever.engine.talents import talent_value

PERCENT = 100.0  # conversion d'unité : les talents sont exprimés en %


def travel_time(gd: GameData, key: str, distance_yd: float, *, analytic: bool = False) -> float:
    """Temps de vol d'un sort sur `distance_yd` : vitesse du projectile (`spells.json`), sinon vitesse par défaut
    de l'analytique ou vitesse « instantanée » du Monte Carlo (`leveling.projectile_speed`, comme le seed).

    Registre : C1"""
    speed = gd.spells[key].projectile_speed
    if speed is None:
        lv = gd.leveling
        speed = lv.projectile_speed_default if analytic else lv.projectile_speed_instant
    return distance_yd / speed


def frostbolt_slow(gd: GameData, pts: Points) -> float:
    """Ralenti de Frostbolt (fraction de vitesse retirée), Permafrost compris.

    Registre : C5"""
    slow = gd.spells["frostbolt"].slow
    assert slow is not None  # spells.json : Frostbolt ralentit
    return slow + talent_value(gd, pts, "permafrost", 1) / PERCENT


def chill_duration(gd: GameData, rank: Rank, pts: Points) -> float:
    """Durée du ralenti d'un rang de Frostbolt, allongée par Permafrost.

    Registre : C5"""
    durations = gd.spells["frostbolt"].slow_dur
    assert durations is not None  # spells.json : slow_dur par rang
    return durations[rank.position - 1] * (1 + talent_value(gd, pts, "permafrost", 0) / PERCENT)


def mob_speed(gd: GameData, slow: float) -> float:
    """Vitesse de course du monstre (m/s) sous un ralenti `slow` (0 : sans ralenti).

    Registre : C5"""
    return gd.mob_model.run_speed * (1 - slow)


def frostbite_chance(gd: GameData, pts: Points) -> float:
    """Chance qu'un Frostbolt qui touche gèle la cible (Frostbite).

    Registre : C5"""
    return talent_value(gd, pts, "frostbite") / PERCENT


def frostbite_freeze_s(gd: GameData) -> float:
    """Durée du gel de Frostbite (`leveling.frostbite_freeze_s`).

    Registre : C5"""
    return gd.leveling.frostbite_freeze_s


def spell_range(gd: GameData, key: str, pts: Points) -> float:
    """Portée d'un sort (portée par défaut des données sans portée publiée) ; Arctic Reach allonge Frostbolt
    seulement, comme le seed.

    Registre : C2"""
    base = gd.spells[key].range_yd
    base = gd.constants.default_range_yd if base is None else base
    return float(base) * ((1 + talent_value(gd, pts, "arcticReach") / PERCENT) if key == "frostbolt" else 1)


def attacker_swing_s(gd: GameData, *, frost_armor: bool) -> float:
    """Intervalle entre deux coups du monstre, ralenti par Frost Armor après un coup reçu.

    Registre : C5"""
    swing = gd.mob_model.swing_s
    return swing * (1 + gd.utility.frost_armor_swing_slow) if frost_armor else swing
