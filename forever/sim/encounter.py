"""Scénarios provisoires de donjon et de raid (T05, décision 82) : boss de donjon, paquet de monstres, boss de raid
(`mechanics.json`, `build.scenarios`, suppose ; affinés en DJ1 et T09).

Tank présent : aucun coup reçu, aucun recul, aucune course ; le Mage lance depuis sa portée. Mana bornée : réserve
plus régénération en combat, sans Évocation ni potion ; une fois la mana épuisée (coût du lancer suivant supérieur à la
réserve), plus aucun lancer. Boss insensibles au gel (`freeze_immune`, règle Classic supposée) : ni Frostbite ni gel.
Arcane Power à 0 s puis à chaque recharge (lancers qui finissent dans la fenêtre, comme en leveling). Aucune formule de
combat ici : les règles viennent de `forever/engine/`.

Métrique : dégâts par seconde. Monte Carlo : un lancer n'est commencé que s'il finit dans la durée ; sans fin de mana,
dégâts / fin du dernier lancer (la fraction de lancer qui ne tient pas dans la durée est un artefact de découpage) ;
avec fin de mana, dégâts / durée ; paquet : jusqu'à la mort du dernier monstre. Les coups des lancers finis comptent
même si le projectile arrive après la durée ; les tics de DoT et d'Ignite comptent jusqu'à la durée.

Registre : H3, H5, I1"""

from __future__ import annotations

import heapq
import math
import random
import statistics
from typing import Any, NamedTuple, TypedDict

from forever.engine.buffs import (
    ARCANE_MISSILES,
    HOT_STREAK_SPELLS,
    PYROBLAST,
    SPELL,
    ArcaneBlastAura,
    arcane_blast_active,
    arcane_blast_after_spell,
    arcane_blast_bonus,
    arcane_power_buffs,
    arcane_power_windows,
    hot_streak_buffs,
    hot_streak_rules,
    merge_buffs,
    missile_barrage_buffs,
    missile_barrage_chance,
)
from forever.engine.cast import expected_cast
from forever.engine.casting import cast_time, cooldown_period, spell_cooldown
from forever.engine.character import character
from forever.engine.damage import (
    IgniteState,
    dot_sp_per_tick,
    dot_tick_damage,
    dot_tick_period_s,
    dot_tick_times,
    ignite_damage,
    ignite_tick_times,
    ignite_ticks_due,
    roll_base_damage,
    roll_ignite,
)
from forever.engine.encounter import cast_fits, encounter_length, scenario_hp
from forever.engine.mana import (
    arcane_blast_cost,
    clearcast_cost_factor,
    in_combat_regen_fraction,
    mana_cost,
    master_of_elements_refund,
)
from forever.engine.model import (
    SCHOOL_FIRE,
    SCHOOL_FROST,
    Buffs,
    CastEstimate,
    Character,
    CharacterOverrides,
    GameData,
    Points,
    Scenario,
)
from forever.engine.monsters import MOB_SOURCES
from forever.engine.movement import frostbite_chance, frostbite_freeze_s, spell_range, travel_time
from forever.engine.spells import SPELL_LEVELS, best_rank
from forever.engine.talents import talent_value
from forever.sim.leveling_analytic import arcane_cycle
from forever.sim.leveling_mc import (
    AB_DUMPS,
    ARCANE_POWER_CHOICES,
    PERCENT,
    McStats,
    arcane_plan,
    hot_streak_plan,
)

ENCOUNTER_ROTATIONS = ("frost", "fire", "arcane", "aoe")  # aoe : paquet (sorts de zone)
AOE_FILLERS = ("arcane_explosion", "blizzard", "flamestrike")  # sort de zone de remplissage de la rotation aoe
AOE_COOLDOWNS = ("blast_wave", "cone_of_cold")  # sorts de zone à recharge, lancés dès qu'ils sont prêts
MAIN = {"frost": "frostbolt", "fire": "fireball", "arcane": "arcane_blast"}
OPTIONS = (
    "armor",
    "ab_stacks",
    "ab_dump",
    "hs_stacks",
    "arcane_power",
    "low_level_penalty",
    "spell_level",
    "rules",
    "aoe_filler",
    "mob_source",
)


class EncounterLog(NamedTuple):
    """Lancer relevé par `encounter_fight(log=…)` : début et fin de l'incantation, sort, mana payée, dégâts des coups
    directs de ce lancer (toutes cibles)."""

    start: float
    end: float
    key: str
    cost: float
    dmg: float


class EncounterResult(TypedDict):
    dps: float
    dmg: float
    duration_s: float
    oom_s: float | None  # instant où la mana manque pour le lancer suivant (None : jamais)
    taken: float
    rotation: str


def _options(gd: GameData, scenario: str, rotation: str, options: dict[str, Any]) -> tuple[Scenario, dict[str, Any]]:
    unknown = sorted(set(options) - set(OPTIONS))
    if unknown:
        raise ValueError(f"option inconnue : {', '.join(unknown)} ({', '.join(OPTIONS)} attendues)")
    if scenario not in gd.build.scenarios:
        raise ValueError(f"scénario inconnu « {scenario} » ({', '.join(gd.build.scenarios)} attendu)")
    if rotation not in ENCOUNTER_ROTATIONS:
        raise ValueError(f"rotation inconnue « {rotation} » ({', '.join(ENCOUNTER_ROTATIONS)} attendue)")
    o = {
        "armor": "auto",
        "ab_stacks": None,
        "ab_dump": None,
        "hs_stacks": None,
        "arcane_power": "auto",
        "low_level_penalty": None,
        "spell_level": "character",
        "rules": "forever",
        "aoe_filler": None,
        "mob_source": gd.leveling.mob_source,
        **options,
    }
    if o["rules"] != "forever":
        raise ValueError(
            f"rules « {o['rules']} » : les scénarios n'existent qu'en mode forever (rules forever attendu)"
        )
    if o["arcane_power"] not in ARCANE_POWER_CHOICES:
        raise ValueError(f"arcane_power « {o['arcane_power']} » ({' ou '.join(ARCANE_POWER_CHOICES)} attendu)")
    if o["aoe_filler"] is not None and o["aoe_filler"] not in AOE_FILLERS:
        raise ValueError(f"aoe_filler inconnu « {o['aoe_filler']} » ({', '.join(AOE_FILLERS)} attendu)")
    if o["ab_dump"] is not None and o["ab_dump"] not in AB_DUMPS:
        raise ValueError(f"ab_dump inconnu « {o['ab_dump']} » ({', '.join(AB_DUMPS)} attendu)")
    if o["spell_level"] not in SPELL_LEVELS:
        raise ValueError(f"spell_level inconnu « {o['spell_level']} » ({' ou '.join(SPELL_LEVELS)} attendu)")
    if o["mob_source"] not in MOB_SOURCES:
        raise ValueError(f"mob_source inconnu « {o['mob_source']} » ({' ou '.join(MOB_SOURCES)} attendu)")
    if o["hs_stacks"] is not None and rotation != "fire":
        raise ValueError(f"hs_stacks sans effet hors de la rotation fire (rotation {rotation})")
    for key in ("ab_stacks", "ab_dump"):
        if o[key] is not None and rotation != "arcane":
            raise ValueError(f"{key} sans effet hors de la rotation arcane (rotation {rotation})")
    return gd.build.scenarios[scenario], o


def _eng(o: dict[str, Any]) -> dict[str, Any]:
    return {"spell_level": o["spell_level"], "rules": o["rules"], "low_level_penalty": o["low_level_penalty"]}


def _learned(gd: GameData, level: int, pts: Points, keys: tuple[str, ...]) -> list[str]:
    return [k for k in keys if best_rank(gd, k, level, pts) is not None]


# --- Analytique ---------------------------------------------------------------------------------------------------


def _cycle(
    gd: GameData,
    level: int,
    pts: Points,
    ch: Character,
    rotation: str,
    sc: Scenario,
    o: dict[str, Any],
    extra: Buffs | None,
    filler: str | None,
) -> tuple[float, float]:
    """(dégâts par seconde par cible, mana par seconde) en espérance du cycle stationnaire de la rotation."""
    eng = _eng(o)
    ld = sc.level_offset
    gcd = gd.rules.gcd_s
    if rotation == "aoe":
        assert filler is not None
        f = expected_cast(gd, filler, level, pts, ch, ld, buffs=extra, **eng)
        assert f is not None
        busy, dmg, mana = 0.0, 0.0, 0.0  # part du temps, dégâts et mana par seconde des sorts à recharge
        for key in _learned(gd, level, pts, AOE_COOLDOWNS):
            e = expected_cast(gd, key, level, pts, ch, ld, buffs=extra, **eng)
            assert e is not None
            cd = spell_cooldown(gd, key, e["rank"], pts)
            busy += e["cast_s"] / cd
            dmg += e["dmg"] / cd
            mana += e["mana"] / cd
        rest = max(0.0, 1 - busy)
        return dmg + rest * f["dmg"] / f["cast_s"], mana + rest * f["mana"] / f["cast_s"]
    if rotation == "arcane":
        cyc = arcane_cycle(
            gd, level, pts, ch, ld, ab_stacks=o["ab_stacks"], ab_dump=o["ab_dump"], extra_buffs=extra, **eng
        )
        return cyc["dmg"] / cyc["time_s"], cyc["mana"] / cyc["time_s"]
    lv = gd.leveling
    wc = talent_value(gd, pts, "wintersChill", 1, 0) * min(
        1.0, talent_value(gd, pts, "wintersChill", 0) / PERCENT * lv.analytic_winters_chill_casts
    )
    main = MAIN[rotation]
    e = expected_cast(gd, main, level, pts, ch, ld, wc_stacks=wc, buffs=extra, **eng)
    if e is None:
        raise ValueError(f"{main} n'est pas appris au niveau {level}")
    time, dmg, mana = e["cast_s"], e["dmg"], e["mana"]
    if rotation == "frost" and best_rank(gd, "ice_lance", level, pts) is not None:
        il = expected_cast(gd, "ice_lance", level, pts, ch, ld, frozen=True, wc_stacks=wc, buffs=extra, **eng)
        assert il is not None
        freeze = 0.0 if sc.freeze_immune else frostbite_chance(gd, pts) * e["hit"] * frostbite_freeze_s(gd) / gcd
        charges = talent_value(gd, pts, "fingersOfFrost", 1, 1)
        fof = talent_value(gd, pts, "fingersOfFrost", 0) / PERCENT * e["hit"] * charges
        casts = freeze + fof  # Ice Lance par Frostbolt : pendant le gel, puis une par charge de Fingers of Frost
        time, dmg, mana = time + casts * gcd, dmg + casts * il["dmg"], mana + casts * il["mana"]
    if rotation == "fire":
        # taux par seconde : x Fireball, Fire Blast à chaque recharge, un Pyroblast tous les hs_n critiques
        k_fb = e["hit"] * e["crit"]
        fbl = expected_cast(gd, "fire_blast", level, pts, ch, ld, buffs=extra, **eng)
        # période effective : Fire Blast attend la fin de la Fireball en cours (recharge arrondie aux incantations)
        f_rate = (
            1 / cooldown_period(gd, spell_cooldown(gd, "fire_blast", fbl["rank"], pts), e["cast_s"]) if fbl else 0.0
        )
        k_fbl = fbl["hit"] * fbl["crit"] if fbl else 0.0
        hs_n = hot_streak_plan(gd, level, pts, rotation, o)
        py = None
        if hs_n:
            py_buffs = merge_buffs(hot_streak_buffs(gd, pts, hs_n), extra)
            py = expected_cast(gd, PYROBLAST, level, pts, ch, ld, buffs=py_buffs, **eng)
            assert py is not None
        c_py = py["cast_s"] / hs_n if py else 0.0
        x = (1 - f_rate * gcd - c_py * k_fbl * f_rate) / (e["cast_s"] + c_py * k_fb)
        p_rate = (x * k_fb + f_rate * k_fbl) / hs_n if py else 0.0
        dps = x * e["dmg"] + (f_rate * fbl["dmg"] if fbl else 0.0) + (p_rate * py["dmg"] if py else 0.0)
        mps = x * e["mana"] + (f_rate * fbl["mana"] if fbl else 0.0) + (p_rate * py["mana"] if py else 0.0)
        return dps, mps
    return dmg / time, mana / time


def _best_filler(gd: GameData, scenario: str, level: int, pts: Points, race: str, over: Any, o: dict[str, Any]) -> str:
    fillers = _learned(gd, level, pts, AOE_FILLERS)
    if not fillers:
        raise ValueError(f"aucun sort de zone appris au niveau {level} ({', '.join(AOE_FILLERS)})")
    if o["aoe_filler"] is not None:
        if o["aoe_filler"] not in fillers:
            raise ValueError(f"aoe_filler {o['aoe_filler']} n'est pas appris au niveau {level}")
        return str(o["aoe_filler"])
    base = {k: v for k, v in o.items() if k != "aoe_filler"}
    scores = {
        f: encounter_analytic(gd, scenario, level, pts, race, "aoe", over, aoe_filler=f, **base)["dps"] for f in fillers
    }
    return max(fillers, key=lambda f: scores[f])


def encounter_analytic(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    over: CharacterOverrides | None = None,
    **options: Any,
) -> EncounterResult:
    """Espérance d'un scénario : cycle de la rotation (dégâts et mana par seconde, Arcane Power dans ses fenêtres), fin
    de mana, par segments de temps ; paquet : cibles identiques, mortes ensemble, dégâts de zone sur chaque cible
    (sans plafond de cibles, C7).

    Registre : H3, H5, I1"""
    sc, o = _options(gd, scenario, rotation, options)
    if rotation == "arcane":
        arcane_plan(gd, level, pts, o["ab_stacks"], o["ab_dump"])
    ch = character(gd, level, race, over)
    filler = _best_filler(gd, scenario, level, pts, race, over, o) if rotation == "aoe" else None
    duration = sc.duration_s
    windows = arcane_power_windows(gd, pts, duration) if o["arcane_power"] == "auto" else []
    plain = _cycle(gd, level, pts, ch, rotation, sc, o, None, filler)
    buffed = _cycle(gd, level, pts, ch, rotation, sc, o, arcane_power_buffs(gd, pts), filler) if windows else plain
    # rotation de zone : chaque cible touchée, mortes ensemble ; à une cible : une cible après l'autre
    targets = sc.targets if rotation == "aoe" else 1
    end = duration
    if sc.hp == "mob":
        hp = scenario_hp(gd, sc, level, o["mob_source"])
        need = hp[0] if rotation == "aoe" else sum(hp)
        end = min(duration, _kill_time(need, windows, plain[0], buffed[0], duration))
    regen = in_combat_regen_fraction(gd, pts, level, armor=o["armor"], rules=o["rules"]) * ch.spirit_regen
    if rotation == "arcane" and sc.hp == "boss":
        return _arcane_walk(gd, level, pts, ch, sc, o, windows, regen)
    pool, t, dmg, oom = ch.mana, 0.0, 0.0, None
    for a, b, (dps, mps) in _segments(windows, plain, buffed, end):
        drain = mps - regen
        if drain > 0 and pool < drain * (b - a):
            oom = a + pool / drain
            dmg += targets * dps * (oom - a)
            t = oom
            break
        pool = min(ch.mana, pool - drain * (b - a))
        dmg += targets * dps * (b - a)
        t = b
    length = t if sc.hp == "mob" else duration
    return {
        "dps": dmg / length if length > 0 else 0.0,
        "dmg": dmg,
        "duration_s": length,
        "oom_s": oom,
        "taken": 0.0,
        "rotation": rotation if filler is None else f"aoe:{filler}",
    }


def _arcane_walk(
    gd: GameData,
    level: int,
    pts: Points,
    ch: Character,
    sc: Scenario,
    o: dict[str, Any],
    windows: list[tuple[float, float]],
    regen: float,
) -> EncounterResult:
    """Rotation arcane sur un boss, déroulée lancer par lancer en espérance : `ab_stacks` Arcane Blast à coût
    croissant puis la décharge (raccourcie et gratuite avec la probabilité de Missile Barrage), Arcane Power sur les
    lancers qui finissent dans ses fenêtres, fin de mana au premier lancer trop cher ; le cycle incomplet de la fin du
    combat compte (Arcane Blast de montée sans décharge), comme au Monte Carlo.

    Registre : B14, B15, H5, I1"""
    eng = _eng(o)
    ld = sc.level_offset
    n, dump = arcane_plan(gd, level, pts, o["ab_stacks"], o["ab_dump"])
    ap = arcane_power_buffs(gd, pts)
    mb = missile_barrage_buffs(gd, pts) if dump == ARCANE_MISSILES else {}
    duration = sc.duration_s

    def estimate(key: str, stacks: int, buffed: bool) -> CastEstimate:
        bonus = arcane_blast_bonus(gd, pts, stacks, for_spell=key)
        buffs = merge_buffs(bonus, ap) if buffed else bonus
        e = expected_cast(gd, key, level, pts, ch, ld, buffs=buffs, **eng)
        assert e is not None  # vérifié par arcane_plan
        return e

    ab0 = estimate(SPELL, 0, False)
    p_mb = 1 - (1 - missile_barrage_chance(gd, pts, SPELL) * ab0["hit"]) ** n if mb and n else 0.0
    free = clearcast_cost_factor(gd, pts, ab0["hit"])
    pool, t, dmg, oom = ch.mana, 0.0, 0.0, None
    step = 0
    while True:
        i = step % (n + 1)
        key = SPELL if i < n else dump
        stacks = i if key == SPELL else n
        e_plain = estimate(key, stacks, False)
        time = e_plain["cast_s"] * ((1 - p_mb * mb.get("cast_reduction", 0.0)) if key == dump and mb else 1.0)
        end = t + time
        if not cast_fits(end, duration):
            break
        buffed = any(a <= end < b for a, b in windows)
        e = estimate(key, stacks, True) if buffed else e_plain
        cost_mult = 1 + (ap.get("cost", 0.0) if buffed else 0.0)
        if key == SPELL:
            cost = arcane_blast_cost(gd, e["rank"], pts, ch, stacks) * free * cost_mult
        else:
            cost = e["mana"] * ((1 + p_mb * mb.get("cost", 0.0)) if mb else 1.0)
        if cost > pool:
            oom = t
            break
        pool = min(ch.mana, pool - cost + regen * time)
        dmg += e["dmg"]
        t = end
        step += 1
    length = encounter_length(duration, t, oom, None)
    return {
        "dps": dmg / length if length > 0 else 0.0,
        "dmg": dmg,
        "duration_s": duration,
        "oom_s": oom,
        "taken": 0.0,
        "rotation": "arcane",
    }


def _segments(
    windows: list[tuple[float, float]],
    plain: tuple[float, float],
    buffed: tuple[float, float],
    end: float,
) -> list[tuple[float, float, tuple[float, float]]]:
    """Découpe [0, end] en segments (début, fin, rythme) : rythme d'Arcane Power dans ses fenêtres, ordinaire sinon."""
    out: list[tuple[float, float, tuple[float, float]]] = []
    t = 0.0
    for a, b in windows:
        if a >= end:
            break
        if a > t:
            out.append((t, a, plain))
        out.append((a, min(b, end), buffed))
        t = min(b, end)
    if t < end:
        out.append((t, end, plain))
    return out


def _kill_time(hp: float, windows: list[tuple[float, float]], dps: float, dps_ap: float, duration: float) -> float:
    """Instant où une cible de `hp` PV meurt au rythme par cible donné (Arcane Power dans ses fenêtres)."""
    left = hp
    for a, b, (rate, _) in _segments(windows, (dps, 0.0), (dps_ap, 0.0), duration):
        if rate * (b - a) >= left:
            return a + left / rate
        left -= rate * (b - a)
    return math.inf


# --- Monte Carlo --------------------------------------------------------------------------------------------------


def encounter_fight(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    rng: random.Random | None = None,
    log: list[EncounterLog] | None = None,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> EncounterResult:
    """Un combat du scénario simulé lancer par lancer : pour chaque cible touchée, tirages de toucher, de dégâts, de
    critique et des tics de DoT ; puis Missile Barrage, Frostbite, Fingers of Frost, Winter's Chill et Clearcasting.

    Registre : H3, H5, I1, J2"""
    sc, o = _options(gd, scenario, rotation, options)
    rng = rng or random.Random()
    ch = character(gd, level, race, over)
    eng = _eng(o)
    ld = sc.level_offset
    duration = sc.duration_s
    filler = _best_filler(gd, scenario, level, pts, race, over, o) if rotation == "aoe" else None
    arcane = rotation == "arcane"
    ab_n, dump = arcane_plan(gd, level, pts, o["ab_stacks"], o["ab_dump"]) if arcane else (0, "")
    hs_n = hot_streak_plan(gd, level, pts, rotation, o)
    hs_rules = hot_streak_rules(gd, pts) if hs_n else None
    mb_on = arcane and dump == ARCANE_MISSILES and bool(missile_barrage_buffs(gd, pts))
    windows = arcane_power_windows(gd, pts, duration) if o["arcane_power"] == "auto" else []
    ap = arcane_power_buffs(gd, pts)
    has_il = rotation == "frost" and best_rank(gd, "ice_lance", level, pts) is not None
    has_fbl = rotation == "fire" and best_rank(gd, "fire_blast", level, pts) is not None
    fbite = 0.0 if sc.freeze_immune else frostbite_chance(gd, pts)
    fof_p = talent_value(gd, pts, "fingersOfFrost", 0) / PERCENT
    fof_n = int(talent_value(gd, pts, "fingersOfFrost", 1, 1))
    wc_p = talent_value(gd, pts, "wintersChill", 0) / PERCENT
    wc_max = int(talent_value(gd, pts, "wintersChill", 1, 0))
    clearcast = talent_value(gd, pts, "arcaneConcentration") / PERCENT
    ignite = talent_value(gd, pts, "ignite")
    rolling = gd.leveling.ignite_rule == "rolling"
    n = sc.targets
    hp = scenario_hp(gd, sc, level, o["mob_source"])
    wc = [0] * n
    frozen_until = [-1.0] * n
    ig_state: list[IgniteState | None] = [None] * n
    events: list[tuple[float, int, int, float, bool]] = []  # (instant, ordre, cible, dégâts, coup direct)
    order = [0]
    regen = in_combat_regen_fraction(gd, pts, level, armor=o["armor"], rules=o["rules"]) * ch.spirit_regen
    s: dict[str, Any] = {"t": 0.0, "pool": ch.mana, "dealt": 0.0, "cc": False, "fof": 0, "hs": 0, "hs_exp": -1.0}
    s.update({"mb": False, "fbl": 0.0, "last_end": 0.0, "dead_at": None})
    ready: dict[str, float] = dict.fromkeys(AOE_COOLDOWNS, 0.0)
    aura: list[ArcaneBlastAura | None] = [None]

    def push(at: float, target: int, dmg: float, direct: bool = False) -> None:
        order[0] += 1
        heapq.heappush(events, (at, order[0], target, dmg, direct))

    def deal(until: float) -> None:
        while events and events[0][0] <= until:
            at, _, i, dmg, direct = heapq.heappop(events)
            if (at > duration and not direct) or hp[i] <= 0:  # coup direct d'un lancer fini : compté
                continue
            done = min(dmg, hp[i])
            hp[i] -= done
            s["dealt"] += done
            if all(h <= 0 for h in hp) and s["dead_at"] is None:
                s["dead_at"] = at
        for i in range(n):  # tics d'Ignite roulant échus
            if ig_state[i] is not None and hp[i] > 0:
                due, ig_state[i] = ignite_ticks_due(ig_state[i], min(until, duration))
                if due:
                    done = min(due, hp[i])
                    hp[i] -= done
                    s["dealt"] += done
                    if all(h <= 0 for h in hp) and s["dead_at"] is None:
                        s["dead_at"] = until

    def in_window(t: float) -> bool:
        return any(a <= t < b for a, b in windows)

    def pick(t: float) -> tuple[str, Buffs | None, bool]:
        if rotation == "aoe":
            for key in _learned(gd, level, pts, AOE_COOLDOWNS):
                if t >= ready[key]:
                    return key, None, False
            assert filler is not None
            return filler, None, False
        if rotation == "frost" and has_il and (s["fof"] > 0 or t < frozen_until[_target()]):
            return "ice_lance", None, False
        if has_fbl and t >= s["fbl"]:
            return "fire_blast", None, False
        if hs_n and (s["hs"] if t < s["hs_exp"] else 0) >= hs_n:
            return PYROBLAST, hot_streak_buffs(gd, pts, s["hs"]), False
        if arcane and arcane_blast_active(aura[0], t) >= ab_n:
            if mb_on and s["mb"]:
                return dump, missile_barrage_buffs(gd, pts), True
            return dump, None, False
        return MAIN[rotation], None, False

    def _target() -> int:
        return next(i for i in range(n) if hp[i] > 0)

    while any(h > 0 for h in hp):
        t = s["t"]
        key, extra, free = pick(t)
        rank = best_rank(gd, key, level, pts)
        if rank is None:
            raise ValueError(f"{key} n'est pas appris au niveau {level}")
        end = t + cast_time(gd, key, rank, pts, ch, extra)
        if not cast_fits(end, duration):
            break
        stacks = arcane_blast_active(aura[0], end) if arcane else 0
        buffs: Buffs | None = arcane_blast_bonus(gd, pts, stacks, for_spell=key) if arcane else None
        if extra or in_window(end):
            buffs = merge_buffs(buffs, extra, ap if in_window(end) else None)
        frozen = key == "ice_lance"
        tgt = _target()
        e = expected_cast(gd, key, level, pts, ch, ld, frozen=frozen, wc_stacks=wc[tgt], buffs=buffs, **eng)
        assert e is not None
        cost = 0.0
        if not s["cc"] and not free:
            if key == SPELL:
                cost = arcane_blast_cost(gd, e["rank"], pts, ch, stacks) * (1 + (buffs or {}).get("cost", 0.0))
            else:
                cost = mana_cost(gd, key, e["rank"], pts, ch, buffs)
        s["pool"] = min(ch.mana, s["pool"] + regen * (t - s["last_end"]))
        if cost > s["pool"]:
            s["oom"] = t
            break
        s["pool"] -= cost
        s["cc"] = False
        if free:
            s["mb"] = False
        if key == PYROBLAST:
            s["hs"], s["hs_exp"] = 0, -1.0
        if rotation == "frost" and key == "ice_lance" and s["fof"] > 0 and not t < frozen_until[tgt]:
            s["fof"] -= 1
        deal(end)
        s["pool"] = min(ch.mana, s["pool"] + regen * (end - t))
        s["t"], s["last_end"] = end, end
        if arcane:
            aura[0] = arcane_blast_after_spell(gd, pts, aura[0], end, key)
        if key == "fire_blast":
            s["fbl"] = t + spell_cooldown(gd, key, rank, pts)
        if key in ready:
            ready[key] = t + spell_cooldown(gd, key, rank, pts)
        hit_targets = [i for i in range(n) if hp[i] > 0] if rotation == "aoe" else [_target()]
        total = _resolve(gd, key, e, hit_targets, end, ch, pts, o, buffs, rng, s, wc, frozen_until, ig_state, push)
        if total[1] and hs_rules is not None and key in HOT_STREAK_SPELLS:
            active = s["hs"] if end < s["hs_exp"] else 0
            s["hs"], s["hs_exp"] = min(hs_rules[2], active + 1), end + hs_rules[0]
        if mb_on and total[2] and (chance := missile_barrage_chance(gd, pts, key)) and rng.random() < chance:
            s["mb"] = True
        if key == "frostbolt" and total[2]:
            if fbite and rng.random() < fbite:
                frozen_until[tgt] = end + frostbite_freeze_s(gd)
            if fof_p and rng.random() < fof_p:
                s["fof"] = fof_n
        if key in ("frostbolt", "ice_lance") and total[2] and wc_max and rng.random() < wc_p:
            wc[tgt] = min(wc_max, wc[tgt] + 1)
        if clearcast and total[2] and rng.random() < clearcast:
            s["cc"] = True
        if ignite and total[3]:
            for i, amount, at in total[3]:
                if rolling:
                    due, ig_state[i] = ignite_ticks_due(ig_state[i], at)
                    push(at, i, due)
                    ig_state[i] = roll_ignite(gd, ig_state[i], at, amount)
                else:
                    ticks = ignite_tick_times(gd)
                    for dt in ticks:
                        push(at + dt, i, amount / len(ticks))
        if log is not None:
            log.append(EncounterLog(t, end, key, cost, total[0]))
    deal(math.inf)  # coups directs encore en vol ; tics au-delà de la durée écartés
    oom = s.get("oom")
    length = encounter_length(duration, s["last_end"], oom, s["dead_at"])
    return {
        "dps": s["dealt"] / length if length > 0 else 0.0,
        "dmg": s["dealt"],
        "duration_s": length,
        "oom_s": oom,
        "taken": 0.0,
        "rotation": rotation if filler is None else f"aoe:{filler}",
    }


def _resolve(
    gd: GameData,
    key: str,
    e: CastEstimate,
    targets: list[int],
    end: float,
    ch: Character,
    pts: Points,
    o: dict[str, Any],
    buffs: Buffs | None,
    rng: random.Random,
    s: dict[str, Any],
    wc: list[int],
    frozen_until: list[float],
    ig_state: list[IgniteState | None],
    push: Any,
) -> tuple[float, bool, bool, list[tuple[int, float, float]]]:
    """Tirages d'un lancer sur chaque cible touchée : (dégâts directs, critique sur la première cible, première cible
    touchée, Ignite à poser (cible, montant, instant))."""
    r = e["rank"]
    travel = travel_time(gd, key, spell_range(gd, key, pts, rules=o["rules"]) if key != "frost_nova" else 0.0)
    direct, first_crit, first_hit = 0.0, False, False
    ignites: list[tuple[int, float, float]] = []
    for j, i in enumerate(targets):
        landed = rng.random() < e["hit"]
        if not landed:
            continue
        base = roll_base_damage(
            gd,
            key,
            r,
            ch,
            rng.random(),
            frozen=key == "ice_lance",
            rules=o["rules"],
            low_level_penalty=o["low_level_penalty"],
        )
        crit = rng.random() < e["crit"]
        dmg = base * e["dmg_mult"] * (e["crit_mult"] if crit else 1.0)
        if j == 0:
            first_crit, first_hit = crit, True
        direct += dmg
        push(end + travel, i, dmg, True)
        if crit and e["school"] in (SCHOOL_FIRE | SCHOOL_FROST) and j == 0:
            s["pool"] = min(ch.mana, s["pool"] + master_of_elements_refund(gd, pts, r, e["mana"]))
        if r.dot_total:
            ticks = dot_tick_times(gd, r.dot_duration_s, dot_tick_period_s(gd, key, r, rules=o["rules"]))
            per_tick = dot_sp_per_tick(
                gd, key, r, ch, buffs, rules=o["rules"], low_level_penalty=o["low_level_penalty"]
            )
            tick = dot_tick_damage(gd, r.dot_total, e["dmg_mult"], len(ticks), sp_per_tick=per_tick)
            for at in ticks:
                tick_crit = gd.rules.dot_can_crit and rng.random() < e["crit"]
                push(end + travel + at, i, tick * (e["crit_mult"] if tick_crit else 1.0))
        if crit and e["school"] in SCHOOL_FIRE:
            ignites.append((i, ignite_damage(gd, pts, dmg), end + travel))
    return direct, first_crit, first_hit, ignites


def encounter_mc(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    n: int = 400,
    seed: int = 12345,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> McStats:
    """Statistiques des dégâts par seconde sur `n` combats du scénario, générateur à graine fixe.

    Registre : H3, H5, J2"""
    if n < 2:
        raise ValueError(f"n = {n} : au moins deux combats pour une dispersion (n ≥ 2)")
    rng = random.Random(seed)
    values = [
        encounter_fight(gd, scenario, level, pts, race, rotation, rng, None, over, **options)["dps"] for _ in range(n)
    ]
    sd = statistics.stdev(values)
    return McStats(statistics.mean(values), sd, sd / math.sqrt(n), n, tuple(values))
