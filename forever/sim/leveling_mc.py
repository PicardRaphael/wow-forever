"""Simulation Monte Carlo du leveling : temps par monstre (combat, repos), mana, dégâts subis, XP par heure.

Portage de seed/forever-mage/scripts/sim_leveling.py (`kill_mc`, `mc`) : simulation pas à pas où les projectiles
volent pendant que le Mage enchaîne l'incantation suivante (impact différé : dégâts, ralenti, gel, Fingers of Frost,
Winter's Chill), avec course et ralentis du monstre, recul d'incantation, DoT et Ignite, coups critiques du monstre,
armure, mana et repos. Les tirages `rng.random()` suivent l'ordre du seed : à graine égale, résultat égal.

Option `rules` (T04c) : `seed` reproduit le seed à l'identique (parité) ; `forever` (défaut) applique les corrections
de T04c : armure portée selon le niveau d'apprentissage du client (`armor`), régénération cumulée d'Arcane
Meditation et de Mage Armor, Ignite roulant (posé à l'impact du critique, reste perdu à la mort du monstre). Aucune
correction ne consomme de tirage.
T04e (`forever`) : coefficients du client, puissance des sorts et période des tics de DoT lues dans le client ;
option `low_level_penalty` (pénalité des sorts de bas niveau, défaut des données, refusée à False en `seed`).

Aucune formule de combat ici : chaque règle vient de `forever/engine/` ; ce module n'orchestre que le temps, les
événements et les tirages. Registre : I1 (rotations frost, fire, arcane), I6 (leveling), J2 (graine)."""

from __future__ import annotations

import random
import statistics
from typing import Any, NamedTuple, TypedDict, cast

from forever.engine.armor import ARMOR_CHOICES, worn_armor
from forever.engine.buffs import (
    ArcaneBlastAura,
    arcane_blast_active,
    arcane_blast_after_spell,
    arcane_blast_bonus,
    arcane_blast_max_stacks,
)
from forever.engine.cast import expected_cast
from forever.engine.casting import cast_time, pushback_resist_chance, pushback_s, spell_cooldown
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
from forever.engine.mana import (
    arcane_blast_cost,
    downtime,
    in_combat_regen_fraction,
    mana_cost,
    master_of_elements_refund,
)
from forever.engine.model import (
    SCHOOL_FIRE,
    SCHOOL_FROST,
    CastEstimate,
    Character,
    CharacterOverrides,
    GameData,
    Points,
    Rank,
)
from forever.engine.monsters import MOB_SOURCES, mob_hit_taken, mob_hp, mob_swing_damage, mob_xp
from forever.engine.movement import (
    attacker_swing_s,
    chill_duration,
    frostbite_chance,
    frostbite_freeze_s,
    frostbolt_slow,
    mob_speed,
    spell_range,
    travel_time,
)
from forever.engine.spells import SPELL_LEVELS, best_rank
from forever.engine.talents import talent_value

ROTATIONS = {"frost": "frostbolt", "fire": "fireball", "arcane": "arcane_blast"}  # sort principal de chaque rotation
AB_DUMPS = ("frostbolt", "fireball", "arcane_missiles")  # sorts de décharge de la rotation arcane
OPTIONS = (
    "level_diff",
    "nova",
    "nova_break",
    "run_between_s",
    "mob_source",
    "spell_level",
    "rules",
    "armor",
    "ab_stacks",
    "ab_dump",
    "low_level_penalty",
)
# Règles du simulateur : `forever` (corrections de T04c) ou `seed` (comportement du seed à l'identique, parité).
RULES = ("forever", "seed")
# Paramètres de méthode (pas des chiffres de jeu) : pas de temps, garde contre une boucle sans fin, marges de temps.
STEP_S = 0.05
GUARD_CASTS = 500
EPSILON_S = 1e-9
LOOKAHEAD_S = 0.01
SECONDS_PER_HOUR = 3600.0
PERCENT = 100.0  # conversion d'unité : les talents sont exprimés en %


class CastLog(NamedTuple):
    """Lancer relevé par `kill_mc(log=…)` : instant de fin d'incantation, sort, cumuls d'Arcane Blast actifs au
    lancer, mana payée (0 sous Clearcasting)."""

    t: float
    key: str
    stacks: int
    cost: float


class KillResult(TypedDict):
    combat: float
    mana: float
    taken: float
    downtime: float
    total: float
    xp_h: float


def options_with_defaults(gd: GameData, rotation: str, options: dict[str, Any]) -> dict[str, Any]:
    """Options du simulateur complétées par les défauts des données (`leveling.defaults`) ; ValueError si une option,
    une rotation, une source de PV ou un niveau de sort est inconnu."""
    unknown = sorted(set(options) - set(OPTIONS))
    if unknown:
        raise ValueError(f"option inconnue : {', '.join(unknown)} ({', '.join(OPTIONS)} attendues)")
    if rotation not in ROTATIONS:
        raise ValueError(f"rotation inconnue « {rotation} » ({' ou '.join(ROTATIONS)} attendue)")
    lv = gd.leveling
    o = {
        "level_diff": lv.default_level_diff,
        "nova": False,
        "nova_break": lv.default_nova_break,
        "run_between_s": lv.default_run_between_s,
        "mob_source": "measured",
        "spell_level": "character",
        "rules": "forever",
        "armor": "auto",
        "ab_stacks": None,
        "ab_dump": None,
        "low_level_penalty": None,
        **options,
    }
    if o["mob_source"] not in MOB_SOURCES:
        raise ValueError(f"mob_source inconnu « {o['mob_source']} » ({' ou '.join(MOB_SOURCES)} attendu)")
    if o["spell_level"] not in SPELL_LEVELS:
        raise ValueError(f"spell_level inconnu « {o['spell_level']} » ({' ou '.join(SPELL_LEVELS)} attendu)")
    if o["rules"] not in RULES:
        raise ValueError(f"rules inconnu « {o['rules']} » ({' ou '.join(RULES)} attendu)")
    if o["armor"] not in ARMOR_CHOICES:
        raise ValueError(f"armor inconnue « {o['armor']} » ({', '.join(ARMOR_CHOICES)} attendue)")
    if o["rules"] == "seed" and o["armor"] != "auto":
        raise ValueError(f"armor « {o['armor']} » sans effet avec rules seed (le seed porte Frost Armor)")
    if o["low_level_penalty"] is not None and not isinstance(o["low_level_penalty"], bool):
        raise ValueError(f"low_level_penalty « {o['low_level_penalty']} » : True, False ou None (données) attendu")
    if o["rules"] == "seed" and o["low_level_penalty"] is False:
        raise ValueError("low_level_penalty False sans effet avec rules seed (le seed applique toujours la pénalité)")
    if rotation == "arcane" and o["rules"] == "seed":
        raise ValueError("rotation arcane absente du seed : rules forever attendu (rules seed refusé)")
    for key in ("ab_stacks", "ab_dump"):
        if o[key] is not None and rotation != "arcane":
            raise ValueError(f"{key} sans effet hors de la rotation arcane (rotation {rotation})")
    if o["ab_dump"] is not None and o["ab_dump"] not in AB_DUMPS:
        raise ValueError(f"ab_dump inconnu « {o['ab_dump']} » ({', '.join(AB_DUMPS)} attendu)")
    if o["ab_stacks"] is not None and (isinstance(o["ab_stacks"], bool) or not isinstance(o["ab_stacks"], int)):
        raise ValueError(f"ab_stacks « {o['ab_stacks']} » : nombre entier de cumuls attendu")
    return o


def arcane_plan(gd: GameData, level: int, pts: Points, ab_stacks: int | None, ab_dump: str | None) -> tuple[int, str]:
    """(cumuls d'Arcane Blast avant la décharge, sort de décharge) de la rotation arcane ; ValueError si Arcane Blast
    ou la décharge n'est pas appris, ou si `ab_stacks` sort de 0 au maximum du talent (défaut : maximum).

    Registre : I1"""
    first = gd.spells["arcane_blast"].ranks[0].level  # rang 1 du talent : niveau du sort (spells.json)
    if best_rank(gd, "arcane_blast", level, pts) is None or level < first:
        raise ValueError(
            f"arcane_blast n'est pas appris au niveau {level} (talent arcaneBlast requis, rang 1 au niveau {first})"
        )
    top = arcane_blast_max_stacks(gd, pts)
    stacks = top if ab_stacks is None else ab_stacks
    if not 0 <= stacks <= top:
        raise ValueError(f"ab_stacks {stacks} hors de 0-{top} (cumuls maximum du talent arcaneBlast)")
    dump = ab_dump or AB_DUMPS[0]
    if best_rank(gd, dump, level, pts) is None:
        raise ValueError(f"ab_dump {dump} n'est pas appris au niveau {level}")
    return stacks, dump


def kill_mc(
    gd: GameData,
    level: int,
    pts: Points,
    ch: Character,
    rotation: str = "frost",
    rng: random.Random | None = None,
    log: list[CastLog] | None = None,
    **options: Any,
) -> KillResult:
    """Un combat simulé pas à pas contre un monstre normal de niveau `level + level_diff`, puis le repos.

    Registre : I1, I6, J2"""
    o = options_with_defaults(gd, rotation, options)
    rng = rng or random.Random()
    mm = gd.mob_model
    gcd = gd.rules.gcd_s
    level_diff = o["level_diff"]
    mlevel = level + level_diff
    hp = [mob_hp(gd, mlevel, o["mob_source"]).value]
    hit_raw = mob_swing_damage(gd, mlevel, ch.armor)
    main = ROTATIONS[rotation]
    r_main = best_rank(gd, main, level, pts)
    if r_main is None:
        raise ValueError(f"{main} n'est pas appris au niveau {level}")
    r_frostbolt = best_rank(gd, "frostbolt", level, pts)
    arcane = rotation == "arcane"
    ab_n, dump = arcane_plan(gd, level, pts, o["ab_stacks"], o["ab_dump"]) if arcane else (0, main)
    r_dump = best_rank(gd, dump, level, pts)
    aura: list[ArcaneBlastAura | None] = [None]  # rotation arcane : aura d'Arcane Blast
    has_il = best_rank(gd, "ice_lance", level, pts) is not None
    has_fbl = best_rank(gd, "fire_blast", level, pts) is not None
    nova_r = best_rank(gd, "frost_nova", level, pts)
    slow = frostbolt_slow(gd, pts)
    fbite = frostbite_chance(gd, pts)
    fof_p = talent_value(gd, pts, "fingersOfFrost", 0) / PERCENT
    fof_n = int(talent_value(gd, pts, "fingersOfFrost", 1, 1))
    wc_p = talent_value(gd, pts, "wintersChill", 0) / PERCENT
    wc_max = int(talent_value(gd, pts, "wintersChill", 1, 0))
    burning = pushback_resist_chance(gd, pts, fire_school=True)
    clearcast = talent_value(gd, pts, "arcaneConcentration") / PERCENT
    ignite = talent_value(gd, pts, "ignite")
    forever = o["rules"] == "forever"
    # armure portée (forever) : ralenti des coups du monstre seulement sous Frost ou Ice Armor ; seed : toujours
    slows = worn_armor(gd, level, o["armor"]).slows_attackers if forever else True
    regen_c = in_combat_regen_fraction(gd, pts, level, armor=o["armor"], rules=o["rules"]) * ch.spirit_regen
    s: dict[str, Any] = {
        "t": 0.0,
        "mana": 0.0,
        "taken": 0.0,
        "aggro": False,
        "chill": -1.0,
        "frozen": -1.0,
        "nova": False,
        "swing": None,
        "farmor": -1.0,
        "nova_ready": 0.0,
        "fbl_ready": 0.0,
        "fof": 0,
        "wc": 0,
        "cc": False,
        "dist": spell_range(gd, main, pts),
    }
    dots: list[tuple[float, float]] = []  # (instant, dégâts)
    ignites: list[tuple[float, float]] = []  # forever : (instant de l'impact, part d'Ignite posée)
    ig_state: list[IgniteState | None] = [None]  # forever : Ignite roulant en cours sur le monstre
    impacts: list[tuple[float, str, float, bool]] = []  # (instant, sort, dégâts, touché)

    def fire_spell(key: str, frozen: bool) -> CastEstimate:
        stacks = arcane_blast_active(aura[0], s["t"]) if arcane else 0
        buffs = arcane_blast_bonus(gd, pts, stacks, for_spell=key) if arcane else None
        e = expected_cast(
            gd,
            key,
            level,
            pts,
            ch,
            level_diff,
            frozen=frozen,
            wc_stacks=s["wc"],
            buffs=buffs,
            spell_level=o["spell_level"],
            rules=o["rules"],
            low_level_penalty=o["low_level_penalty"],
        )
        assert e is not None  # seuls les sorts appris sont lancés
        paid = 0.0
        if not s["cc"]:
            if key == "arcane_blast":
                paid = arcane_blast_cost(gd, e["rank"], pts, ch, stacks)
            else:
                paid = mana_cost(gd, key, e["rank"], pts, ch)
            s["mana"] += paid
        s["cc"] = False
        if log is not None:
            log.append(CastLog(s["t"], key, stacks, paid))
        if arcane:  # Arcane Blast cumule ; tout autre sort de dégâts consomme l'aura
            aura[0] = arcane_blast_after_spell(gd, pts, aura[0], s["t"], key)
        landed = rng.random() < e["hit"]
        dmg = 0.0
        travel = travel_time(gd, key, s["dist"] if key != "frost_nova" else 0.0)
        if landed:
            r = e["rank"]
            base = roll_base_damage(
                gd,
                key,
                r,
                ch,
                rng.random(),
                frozen=frozen and key == "ice_lance",
                rules=o["rules"],
                low_level_penalty=o["low_level_penalty"],
            )
            crit = rng.random() < e["crit"]
            dmg = base * e["dmg_mult"] * (e["crit_mult"] if crit else 1.0)
            if crit and e["school"] in (SCHOOL_FIRE | SCHOOL_FROST):
                s["mana"] -= master_of_elements_refund(gd, pts, r, e["mana"])
            if rng.random() < clearcast:
                s["cc"] = True
            if r.dot_total:
                ticks = dot_tick_times(gd, r.dot_duration_s, dot_tick_period_s(gd, key, r, rules=o["rules"]))
                per_tick = dot_sp_per_tick(gd, key, r, ch, rules=o["rules"], low_level_penalty=o["low_level_penalty"])
                tick = dot_tick_damage(gd, r.dot_total, e["dmg_mult"], len(ticks), sp_per_tick=per_tick)
                for at in ticks:
                    tick_crit = gd.rules.dot_can_crit and rng.random() < e["crit"]
                    dots.append((s["t"] + travel + at, tick * (e["crit_mult"] if tick_crit else 1.0)))
            if crit and e["school"] in SCHOOL_FIRE and ignite:
                ig = ignite_damage(gd, pts, dmg)
                if forever:
                    ignites.append((s["t"] + travel, ig))
                else:
                    ig_ticks = ignite_tick_times(gd)
                    for at in ig_ticks:
                        dots.append((s["t"] + travel + at, ig / len(ig_ticks)))
        impacts.append((s["t"] + travel, key, dmg, landed))
        return e

    def on_impact(key: str, dmg: float, landed: bool, now: float) -> None:
        s["aggro"] = True
        if not landed:
            return
        hp[0] -= dmg
        if s["nova"] and key != "frost_nova" and dmg > 0 and rng.random() < o["nova_break"]:
            s["nova"] = False
        if key == "frostbolt":
            assert r_frostbolt is not None  # un Frostbolt a été lancé, il est appris
            s["chill"] = now + chill_duration(gd, r_frostbolt, pts)
            if fbite and rng.random() < fbite:
                s["frozen"] = now + frostbite_freeze_s(gd)
            if fof_p and rng.random() < fof_p:
                s["fof"] = fof_n
        if key in ("frostbolt", "ice_lance", "frost_nova") and wc_max and rng.random() < wc_p:
            s["wc"] = min(wc_max, s["wc"] + 1)

    def advance(t1: float, casting: bool, fire_school: bool = False) -> float:
        push = 0.0
        while s["t"] < t1 - EPSILON_S:
            dt = min(STEP_S, t1 - s["t"])
            nt = s["t"] + dt
            for im in sorted([x for x in impacts if x[0] <= nt]):
                impacts.remove(im)
                on_impact(im[1], im[2], im[3], im[0])
            for ig in sorted(x for x in ignites if x[0] <= nt):
                ignites.remove(ig)
                due, ig_state[0] = ignite_ticks_due(ig_state[0], ig[0])  # un tic à l'instant du critique passe avant
                hp[0] -= due
                ig_state[0] = roll_ignite(gd, ig_state[0], ig[0], ig[1])
            for d in [x for x in dots if x[0] <= nt]:
                dots.remove(d)
                hp[0] -= d[1]
            ig_dealt, ig_state[0] = ignite_ticks_due(ig_state[0], nt)
            hp[0] -= ig_dealt
            frozen = s["t"] < s["frozen"] or s["nova"]
            if s["aggro"] and not frozen:
                if s["dist"] > mm.melee_range:
                    sp = mob_speed(gd, slow if s["t"] < s["chill"] else 0.0)
                    s["dist"] = max(mm.melee_range, s["dist"] - sp * dt)
                    if s["dist"] <= mm.melee_range and s["swing"] is None:
                        s["swing"] = nt
                elif s["swing"] is not None and nt >= s["swing"]:
                    if rng.random() > mm.avoid_vs_mage:
                        s["taken"] += mob_hit_taken(gd, hit_raw, crit=rng.random() < mm.crit)
                        if slows:
                            s["farmor"] = nt + gd.utility.frost_armor_duration_s
                        if casting and not (fire_school and rng.random() < burning):
                            push += pushback_s(gd)
                    s["swing"] = nt + attacker_swing_s(gd, frost_armor=nt < s["farmor"])
            elif frozen and s["swing"] is not None:
                s["swing"] = max(s["swing"], nt)
            s["t"] = nt
            if hp[0] <= 0:
                break
        return push

    guard = 0
    while hp[0] > 0 and guard < GUARD_CASTS:
        guard += 1
        frozen_now = s["t"] < s["frozen"] or s["nova"]
        if (
            o["nova"]
            and nova_r
            and s["aggro"]
            and s["dist"] <= mm.melee_range
            and s["t"] >= s["nova_ready"]
            and not frozen_now
        ):
            fire_spell("frost_nova", False)
            s["nova"] = True
            s["nova_ready"] = s["t"] + spell_cooldown(gd, "frost_nova", nova_r, pts)
            advance(s["t"] + gcd, False)
            s["dist"] = gd.leveling.frost_nova_retreat_yd
            s["swing"] = None
            continue
        if rotation == "frost" and has_il and (frozen_now or s["fof"] > 0):
            if s["fof"] > 0 and not frozen_now:
                s["fof"] -= 1
            fire_spell("ice_lance", True)
            advance(s["t"] + gcd, False)
            continue
        if (
            rotation == "fire"
            and has_fbl
            and s["t"] >= s["fbl_ready"]
            and s["aggro"]
            and s["dist"] <= spell_range(gd, "fire_blast", pts)
        ):
            e = fire_spell("fire_blast", False)
            s["fbl_ready"] = s["t"] + spell_cooldown(gd, "fire_blast", e["rank"], pts)
            advance(s["t"] + gcd, False)
            continue
        # jeu expert : ne pas lancer un sort si les projectiles déjà en vol suffisent à tuer
        if impacts and sum(x[2] for x in impacts) >= hp[0]:
            advance(min(x[0] for x in impacts) + LOOKAHEAD_S, False)
            continue
        key, r_key = main, cast("Rank | None", r_main)
        if arcane and arcane_blast_active(aura[0], s["t"]) >= ab_n:
            key, r_key = dump, r_dump
        assert r_key is not None  # sort principal et décharge vérifiés appris
        treat_frozen = frozen_now or s["fof"] > 0
        if s["fof"] > 0 and not frozen_now:
            s["fof"] -= 1
        end = s["t"] + cast_time(gd, key, r_key, pts, ch)
        while True:
            p = advance(end, True, fire_school=(key == "fireball"))
            if hp[0] <= 0 or p <= 0 or (arcane and gd.spells[key].channel):
                break  # canalisation (décharge Arcane Missiles) : jamais prolongée par le recul (T04c)
            end = s["t"] + p
        if hp[0] <= 0:
            break
        fire_spell(key, treat_frozen)
    # laisser arriver les projectiles en vol
    if hp[0] > 0 and impacts:
        advance(max(x[0] for x in impacts) + LOOKAHEAD_S, False)
    combat = s["t"]
    mana_used = max(0.0, s["mana"] - regen_c * combat)
    down = downtime(gd, ch, level, mana_used, s["taken"])
    total = combat + down + o["run_between_s"]
    return {
        "combat": combat,
        "mana": mana_used,
        "taken": s["taken"],
        "downtime": down,
        "total": total,
        "xp_h": mob_xp(gd, level) * SECONDS_PER_HOUR / total,
    }


def mc(
    gd: GameData,
    level: int,
    pts: Points,
    race: str = "Orc",
    rotation: str = "frost",
    n: int = 1500,
    seed: int = 12345,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> KillResult:
    """Moyenne de `n` combats simulés avec un générateur à graine fixe (reproductible).

    Registre : I6, J2"""
    if n < 1:
        raise ValueError(f"n = {n} : au moins un combat (n ≥ 1)")
    options_with_defaults(gd, rotation, options)
    ch = character(gd, level, race, over)
    rng = random.Random(seed)
    rs = [kill_mc(gd, level, pts, ch, rotation, rng, **options) for _ in range(n)]
    rows = [cast("dict[str, float]", r) for r in rs]

    def avg(key: str) -> float:
        return statistics.mean(r[key] for r in rows)

    return {
        "combat": avg("combat"),
        "mana": avg("mana"),
        "taken": avg("taken"),
        "downtime": avg("downtime"),
        "total": avg("total"),
        "xp_h": avg("xp_h"),
    }
