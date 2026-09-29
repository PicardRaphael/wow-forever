"""Profil PvP d'un build (T05, bloc G) : dégâts d'ouverture (burst), contrôle, survie, dégâts soutenus en kite.
Portage de seed/forever-mage/scripts/pvp.py (statut EST du seed : `suppose`) : modèle de scénarios qui compare des
builds entre eux, sans simulation de duel. Barème du seed dans `mechanics.json` (`pvp.profile`), poids par contexte
(`pvp.weights`) ; recharges du client (`spell_scaling.json.talent_cooldowns`) et sorts utilitaires (`spells.json`).

Registre : I5"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple, cast

from forever.engine.buffs import AP_DMG, ARCANE_POWER
from forever.engine.cast import expected_cast
from forever.engine.character import character
from forever.engine.model import CastEstimate, Character, CharacterOverrides, GameData, Points
from forever.engine.spells import best_rank
from forever.engine.talents import talent_value


class PvpProfile(NamedTuple):
    """Composantes brutes du profil, score pondéré et séquence d'ouverture retenue."""

    score: float
    burst_seq: str
    burst: float
    control: float
    survival: float
    sustain: float


BLINK, ICE_BLOCK, ICE_BARRIER, COLD_SNAP = "blink", "iceBlock", "iceBarrier", "coldSnap"
SECONDS_PER_MINUTE = 60.0  # conversion d'unité : composantes en secondes par minute
PERCENT = 100.0  # conversion d'unité : talents exprimés en %
COMPONENTS = ("burst", "control", "survival", "sustain")


def _estimate(
    gd: GameData, key: str, level: int, pts: Points, ch: Character, rules: str, **kw: Any
) -> CastEstimate | None:
    spell_level = "rank" if rules == "seed" else "character"
    return expected_cast(gd, key, level, pts, ch, 0, rules=rules, spell_level=spell_level, **kw)


def burst(gd: GameData, pts: Points, level: int, ch: Character, rules: str = "forever") -> tuple[str, float]:
    """Dégâts attendus dans la fenêtre d'ouverture, meilleure séquence disponible (givre, feu, arcanes), comme le seed.

    Registre : I5"""
    prof = gd.pvp.profile
    gcd = gd.rules.gcd_s
    seqs: list[tuple[str, float]] = []
    fb = _estimate(gd, "frostbolt", level, pts, ch, rules)
    il_f = _estimate(gd, "ice_lance", level, pts, ch, rules, frozen=True)
    fb_f = _estimate(gd, "frostbolt", level, pts, ch, rules, frozen=True)
    nova = _estimate(gd, "frost_nova", level, pts, ch, rules)
    if fb:
        s = fb["dmg"] + (nova["dmg"] if nova else 0)
        t = fb["cast_s"] + (gcd if nova else 0)
        if nova and il_f:
            n_il = max(0, int((prof["burst_window_s"] - t) // gcd))
            s += n_il * il_f["dmg"] * (prof["ice_lance_repeat_factor"] if n_il > 1 else 1.0)
        elif nova and fb_f:
            s += fb_f["dmg"]
        seqs.append(("Givre : Éclair, Nova, Javelot(s) sur gel", s))
    fi = _estimate(gd, "fireball", level, pts, ch, rules)
    fbl = _estimate(gd, "fire_blast", level, pts, ch, rules)
    py = _estimate(gd, "pyroblast", level, pts, ch, rules)
    bw = _estimate(gd, "blast_wave", level, pts, ch, rules)
    if fi:
        s = fi["dmg"] + (fbl["dmg"] if fbl else 0) + (bw["dmg"] if bw else 0)
        if py and pts.get("presenceOfMind"):
            s += py["dmg"]
        if pts.get("combustion"):
            s *= prof["combustion_factor"]
        seqs.append(("Feu : Boule, Trait, (Présence + Pyro), Vague", s))
    ab = _estimate(gd, "arcane_blast", level, pts, ch, rules)
    am = _estimate(gd, "arcane_missiles", level, pts, ch, rules)
    if am:
        mult = 1 + talent_value(gd, pts, ARCANE_POWER, AP_DMG) / PERCENT
        s = am["dmg"] * mult
        if ab:
            without_pom = 1.0 if pts.get("presenceOfMind") else prof["arcane_without_pom_factor"]
            s = (prof["arcane_blasts"] * ab["dmg"] + am["dmg"] * prof["arcane_missiles_factor"]) * mult * without_pom
        seqs.append(("Arcanes : (Puissance) Déflagrations + Projectiles", s))
    return max(seqs, key=lambda x: x[1]) if seqs else ("aucune", 0.0)


def control(gd: GameData, pts: Points, level: int) -> float:
    """Secondes de contrôle utile par minute : gel de Frost Nova et de Frostbite, ralentis pondérés, étourdissements
    d'Impact, Blast Wave, silence et verrouillage d'école de Counterspell, comme le seed.

    Registre : I5"""
    prof = gd.pvp.profile
    u = gd.utility
    c = 0.0
    nova = best_rank(gd, "frost_nova", level, pts)
    if nova:
        cd = nova.cooldown_s - talent_value(gd, pts, "improvedFrostNova")
        c += SECONDS_PER_MINUTE / cd * prof["freeze_s"]
    casts = SECONDS_PER_MINUTE / prof["average_cast_s"]
    c += casts * talent_value(gd, pts, "frostbite") / PERCENT * prof["freeze_s"] * prof["frost_share"]
    if best_rank(gd, "frostbolt", level, pts):
        c += (
            prof["slow_weight"]
            * prof["frostbolt_slow_s_per_min"]
            * (1 + talent_value(gd, pts, "permafrost", 0) / PERCENT)
        )
    if best_rank(gd, "cone_of_cold", level, pts):
        c += prof["slow_weight"] * prof["cone_slow_s"] * prof["cone_per_min"]
    c += casts * talent_value(gd, pts, "impact") / PERCENT * prof["impact_stun_s"] * prof["slow_weight"]
    if pts.get("blastWave"):
        c += prof["slow_weight"] * prof["blast_wave_slow_s"] * SECONDS_PER_MINUTE / gd.talent_cooldowns_s["blastWave"]
    if level >= u.counterspell_level:
        lock = u.counterspell_lockout_s * prof["school_lock_weight"]
        c += SECONDS_PER_MINUTE / u.counterspell_cooldown_s * (talent_value(gd, pts, "improvedCounterspell") + lock)
    return float(c)


def survival(gd: GameData, pts: Points, level: int, race: str) -> float:
    """Secondes de survie gagnées par minute face à un mêlée de référence : Ice Block (Cold Snap), Ice Barrier, Blink,
    talents défensifs, bonus racial, comme le seed.

    Registre : I5"""
    prof = gd.pvp.profile
    u = gd.utility
    cds = gd.talent_cooldowns_s
    s = 0.0
    if pts.get(ICE_BLOCK):
        s += (
            prof["ice_block_s"]
            * SECONDS_PER_MINUTE
            / cds[ICE_BLOCK]
            * (prof["cold_snap_factor"] if pts.get(COLD_SNAP) else 1.0)
        )
    ib = [r for r in u.ice_barrier if r[0] <= level] if pts.get(ICE_BARRIER) else []
    if ib:
        s += ib[-1][1] / prof["barrier_divisor"] * SECONDS_PER_MINUTE / cds[ICE_BARRIER] * prof["barrier_factor"]
    if level >= u.blink_level:
        s += SECONDS_PER_MINUTE / u.blink_cooldown_s * prof["blink_melee_avoided_s"]
    s += (
        talent_value(gd, pts, "frostWarding") / PERCENT * prof["frost_warding_factor"]
        + talent_value(gd, pts, "arcaneResilience") / PERCENT * prof["arcane_resilience_factor"]
    )
    s += (
        talent_value(gd, pts, "improvedFrostNova") * prof["improved_frost_nova_s"]
        + talent_value(gd, pts, "permafrost", 1) * prof["permafrost_factor"]
    )
    return float(s + prof["racial_s"].get(race, prof["racial_default_s"]))


def sustain(gd: GameData, pts: Points, level: int, ch: Character, rules: str = "forever") -> float:
    """Dégâts par seconde soutenus en kite : meilleur sort incanté hors mouvement, instantanés en mouvement, comme le
    seed.

    Registre : I5"""
    prof = gd.pvp.profile
    gcd = gd.rules.gcd_s
    best = 0.0
    for key in ("frostbolt", "fireball", "arcane_missiles", "arcane_blast"):
        e = _estimate(gd, key, level, pts, ch, rules)
        if e:
            best = max(best, e["dmg"] / e["cast_s"])
    inst = 0.0
    for key in ("fire_blast", "ice_lance", "cone_of_cold"):
        e = _estimate(gd, key, level, pts, ch, rules)
        if e:
            factor = prof["ice_lance_sustain_factor"] if key == "ice_lance" else 1.0
            inst += e["dmg"] / max(gcd, e["cooldown_s"] or gcd) * factor
    moving = prof["moving_share"]
    return float(best * (1 - moving) + min(inst, best) * moving)


def pvp_score(
    gd: GameData,
    pts: Points,
    level: int = 60,
    race: str = "Orc",
    weights: Mapping[str, float] | None = None,
    over: CharacterOverrides | None = None,
    *,
    rules: str = "forever",
) -> PvpProfile:
    """Profil PvP : chaque composante normalisée par sa référence, plafonnée, pondérée (poids du contexte `bg` par
    défaut), mise à l'échelle ; fiche du barème au niveau où elle existe si `over` n'est pas donné.

    Registre : I5"""
    prof = gd.pvp.profile
    w = {**gd.pvp.weights["bg"], **(weights or {})}
    sheet = prof["sheets"].get(str(level))
    ch = character(gd, level, race, over or (cast(CharacterOverrides, dict(sheet)) if sheet else None))
    b_name, b = burst(gd, pts, level, ch, rules)
    comp = {
        "burst": b,
        "control": control(gd, pts, level),
        "survival": survival(gd, pts, level, race),
        "sustain": sustain(gd, pts, level, ch, rules),
    }
    sc = sum(w[k] * min(prof["cap"], comp[k] / prof["ref"][k]) for k in w) * prof["scale"]
    return PvpProfile(sc, b_name, comp["burst"], comp["control"], comp["survival"], comp["sustain"])


def seed_rounded(p: PvpProfile) -> dict[str, object]:
    """Profil arrondi comme le seed (`pvp.score`) : score et composantes à 0,1 près, statut EST.

    Registre : I5"""
    return {
        "score": round(p.score, 1),
        "burst_seq": p.burst_seq,
        **{k: round(getattr(p, k), 1) for k in COMPONENTS},
        "statut": "EST",
    }
