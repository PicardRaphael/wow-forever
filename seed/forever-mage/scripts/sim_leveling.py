"""sim_leveling.py — temps par monstre en leveling (combat + repos), XP/heure.

Deux moteurs qui partagent les mêmes mécaniques (fm.py) :
  - kill_mc()      : simulation physique pas à pas (distance, course et ralentis du monstre, vol des
                     projectiles, recul d'incantation, gel Frostbite/Nova, Fingers of Frost, Winter's Chill,
                     DoT et Ignite, critiques du monstre, armure, mana, repos). Référence.
  - kill_analytic(): espérance fermée, 1000× plus rapide, utilisée par l'optimiseur. Les tests exigent
                     qu'elle reste à moins de 12 % du Monte Carlo.
Usage : python sim_leveling.py --level 16 --race Orc --talents improvedFrostbolt=5,elementalPrecision=1
"""
import argparse, random, statistics as st
import fm

# --------------------------------------------------------------------------- monde
def mob_hp(level):
    a = {int(k): v for k, v in fm.data().lv["mob_model"]["hp_anchors"].items()}
    ks = sorted(a)
    if level <= ks[0]: return a[ks[0]]
    for lo, hi in zip(ks, ks[1:]):
        if lo <= level <= hi:
            return a[lo] + (a[hi] - a[lo]) * (level - lo) / (hi - lo)
    return a[ks[-1]]

def mob_hit_raw(level):
    return 0.8 * level + 0.02 * level * level

def mob_xp(level):
    return 45 + 5 * level

def armor_dr(armor, attacker_level):
    return armor / (armor + 400 + 85 * attacker_level)

def consumables(level):
    u = fm.data().utility
    def pick(key):
        lv = u[key]["spell_levels"]; vals = u[key]["restore"]
        idx = max([i for i, l in enumerate(lv) if l <= level] or [0])
        amt, dur = vals[idx]
        return amt / dur
    return pick("conjure_water"), pick("conjure_food")

def in_combat_regen_frac(pts, level):
    f = fm.tval(pts, "arcaneMeditation") / 100.0
    if level >= 34:
        f = max(f, fm.data().utility["mage_armor"]["regen_while_casting"])  # Armure de mage (Forever 50 %)
    return min(1.0, f)

DEFAULTS = dict(level_diff=0, nova=False, nova_break=1.0, run_between=6.0, flee=False)

def _opener(rotation):
    return "frostbolt" if rotation == "frost" else "fireball"

# --------------------------------------------------------------------------- Monte Carlo
def kill_mc(level, pts, ch, rotation="frost", rng=None, **o):
    """Simulation pas à pas (0,05 s). Les projectiles volent pendant que le Mage enchaîne l'incantation
    suivante : l'impact est un événement différé (dégâts, ralenti, gel, Fingers of Frost, Winter's Chill)."""
    o = {**DEFAULTS, **o}; rng = rng or random.Random()
    D = fm.data(); rules = D.lv["combat_rules"]; mm = D.lv["mob_model"]
    mlevel = level + o["level_diff"]; st_ = {"hp": mob_hp(mlevel)}
    hit_raw = mob_hit_raw(mlevel) * (1 - armor_dr(ch["armor"], mlevel))
    main = _opener(rotation)
    r_main = fm.best_rank(main, level, pts)
    has_il = fm.best_rank("ice_lance", level, pts) is not None
    has_fbl = fm.best_rank("fire_blast", level, pts) is not None
    nova_r = fm.best_rank("frost_nova", level, pts)
    perma_dur = 1 + fm.tval(pts, "permafrost", 0) / 100.0
    slow = fm.spell("frostbolt")["slow"] + fm.tval(pts, "permafrost", 1) / 100.0
    fbite = fm.tval(pts, "frostbite") / 100.0
    fof_p = fm.tval(pts, "fingersOfFrost", 0) / 100.0; fof_n = int(fm.tval(pts, "fingersOfFrost", 1, 1))
    wc_p = fm.tval(pts, "wintersChill", 0) / 100.0; wc_max = int(fm.tval(pts, "wintersChill", 1, 0))
    burning = fm.tval(pts, "burningSoul", 0) / 100.0
    regen_c = in_combat_regen_frac(pts, level) * ch["spirit_regen"]
    s = dict(t=0.0, mana=0.0, taken=0.0, aggro=False, chill=-1.0, frozen=-1.0, nova=False, swing=None,
             farmor=-1.0, nova_ready=0.0, fbl_ready=0.0, fof=0, wc=0, cc=False)
    rng_main = float(fm.spell(main)["range"]) * ((1 + fm.tval(pts, "arcticReach") / 100.0) if main == "frostbolt" else 1)
    s["dist"] = rng_main
    dots = []; impacts = []                     # (instant, dégâts) ; (instant, clé, dégâts, touché)
    def fire_spell(key, frozen):
        e = fm.expected_cast(key, level, pts, ch, o["level_diff"], frozen=frozen, wc_stacks=s["wc"])
        if not s["cc"]:
            s["mana"] += fm.mana_cost(key, e["rank"], pts, ch)
        s["cc"] = False
        landed = rng.random() < e["hit"]; dmg = 0.0
        if landed:
            r = e["rank"]
            base = r[1] + (r[2] - r[1]) * rng.random() + fm.coefficient(key, r) * fm.spell_power(ch)
            if key == "ice_lance" and frozen:
                base *= fm.spell(key).get("frozen_mult", 4.0)
            crit = rng.random() < e["crit"]
            dmg = base * e["dmg_mult"] * (e["crit_mult"] if crit else 1.0)
            if crit and e["school"] in (fm.SCHOOL_FIRE | fm.SCHOOL_FROST):
                s["mana"] -= fm.tval(pts, "masterOfElements") / 100.0 * (r[6] or e["mana"])
            if rng.random() < fm.tval(pts, "arcaneConcentration") / 100.0:
                s["cc"] = True
            travel = (s["dist"] if key != "frost_nova" else 0.0) / fm.spell(key).get("projectile_speed", 1e9)
            if r[3]:
                n = max(1, int(r[4] / 2)); tick = r[3] * e["dmg_mult"] / n
                for i in range(1, n + 1):
                    dots.append((s["t"] + travel + 2 * i, tick * (e["crit_mult"] if rng.random() < e["crit"] else 1.0)))
            if crit and e["school"] in fm.SCHOOL_FIRE and fm.tval(pts, "ignite"):
                ig = dmg * fm.tval(pts, "ignite") / 100.0
                dots.append((s["t"] + travel + 2, ig / 2)); dots.append((s["t"] + travel + 4, ig / 2))
        else:
            travel = s["dist"] / fm.spell(key).get("projectile_speed", 1e9) if key != "frost_nova" else 0.0
        impacts.append((s["t"] + travel, key, dmg, landed))
        return e
    def on_impact(key, dmg, landed, now):
        s["aggro"] = True
        if not landed:
            return
        st_["hp"] -= dmg
        if s["nova"] and key != "frost_nova" and dmg > 0 and rng.random() < o["nova_break"]:
            s["nova"] = False
        if key == "frostbolt":
            s["chill"] = now + fm.spell("frostbolt")["slow_dur"][fm.spell("frostbolt")["ranks"].index(r_main)] * perma_dur
            if fbite and rng.random() < fbite:
                s["frozen"] = now + 5.0
            if fof_p and rng.random() < fof_p:
                s["fof"] = fof_n
        if key in ("frostbolt", "ice_lance", "frost_nova") and wc_max and rng.random() < wc_p:
            s["wc"] = min(wc_max, s["wc"] + 1)
    def advance(t1, casting, fire_school=False):
        push = 0.0
        while s["t"] < t1 - 1e-9:
            dt = min(0.05, t1 - s["t"]); nt = s["t"] + dt
            for im in sorted([x for x in impacts if x[0] <= nt]):
                impacts.remove(im); on_impact(im[1], im[2], im[3], im[0])
            for d in [x for x in dots if x[0] <= nt]:
                dots.remove(d); st_["hp"] -= d[1]
            frozen = s["t"] < s["frozen"] or s["nova"]
            if s["aggro"] and not frozen:
                if s["dist"] > mm["melee_range"]:
                    sp = mm["run_speed"] * ((1 - slow) if s["t"] < s["chill"] else 1.0)
                    s["dist"] = max(mm["melee_range"], s["dist"] - sp * dt)
                    if s["dist"] <= mm["melee_range"] and s["swing"] is None:
                        s["swing"] = nt
                elif s["swing"] is not None and nt >= s["swing"]:
                    if rng.random() > mm["avoid_vs_mage"]:
                        s["taken"] += hit_raw * (mm["crit_mult"] if rng.random() < mm["crit"] else 1.0)
                        s["farmor"] = nt + D.utility["frost_armor"]["dur"]
                        if casting and not (fire_school and rng.random() < burning):
                            push += rules["pushback_s"]
                    s["swing"] = nt + mm["swing_s"] * ((1 + D.utility["frost_armor"]["attacker_swing_slow"]) if nt < s["farmor"] else 1.0)
            elif frozen and s["swing"] is not None:
                s["swing"] = max(s["swing"], nt)
            s["t"] = nt
            if st_["hp"] <= 0:
                break
        return push
    guard = 0
    while st_["hp"] > 0 and guard < 500:
        guard += 1
        frozen_now = s["t"] < s["frozen"] or s["nova"]
        if o["nova"] and nova_r and s["aggro"] and s["dist"] <= mm["melee_range"] and s["t"] >= s["nova_ready"] and not frozen_now:
            fire_spell("frost_nova", False)
            s["nova"] = True; s["nova_ready"] = s["t"] + nova_r[7] - fm.tval(pts, "improvedFrostNova")
            advance(s["t"] + rules["gcd"], False); s["dist"] = 10.0; s["swing"] = None
            continue
        if rotation == "frost" and has_il and (frozen_now or s["fof"] > 0):
            if s["fof"] > 0 and not frozen_now:
                s["fof"] -= 1
            fire_spell("ice_lance", True)
            advance(s["t"] + rules["gcd"], False)
            continue
        if rotation == "fire" and has_fbl and s["t"] >= s["fbl_ready"] and s["aggro"] and s["dist"] <= fm.spell("fire_blast")["range"]:
            e = fire_spell("fire_blast", False)
            s["fbl_ready"] = s["t"] + e["cooldown"] - fm.tval(pts, "wakeOfFire", 0)
            advance(s["t"] + rules["gcd"], False)
            continue
        # jeu expert : ne pas lancer un sort si les projectiles déjà en vol suffisent à tuer
        if impacts and sum(x[2] for x in impacts) >= st_["hp"]:
            advance(min(x[0] for x in impacts) + 0.01, False)
            continue
        treat_frozen = frozen_now or s["fof"] > 0
        if s["fof"] > 0 and not frozen_now:
            s["fof"] -= 1
        end = s["t"] + fm.cast_time(main, r_main, pts, ch)
        while True:
            p = advance(end, True, fire_school=(main == "fireball"))
            if st_["hp"] <= 0 or p <= 0:
                break
            end = s["t"] + p
        if st_["hp"] <= 0:
            break
        fire_spell(main, treat_frozen)
        if not impacts and st_["hp"] > 0:
            continue
    # laisser arriver les projectiles en vol
    if st_["hp"] > 0 and impacts:
        advance(max(x[0] for x in impacts) + 0.01, False)
    combat = s["t"]
    mana_used = max(0.0, s["mana"] - regen_c * combat)
    water, food = consumables(level)
    down = max(mana_used / (water + ch["spirit_regen"]), s["taken"] / (food + 0.02 * ch["hp"]))
    total = combat + down + o["run_between"]
    return {"combat": combat, "mana": mana_used, "taken": s["taken"], "downtime": down, "total": total,
            "xp_h": mob_xp(level) * 3600.0 / total}

def mc(level, pts, race="Orc", rotation="frost", n=1500, seed=12345, over=None, **o):
    ch = fm.character(level, race, over)
    rng = random.Random(seed)
    rs = [kill_mc(level, pts, ch, rotation, rng, **o) for _ in range(n)]
    return {k: st.mean(r[k] for r in rs) for k in rs[0]}

# --------------------------------------------------------------------------- analytique
def kill_analytic(level, pts, race="Orc", rotation="frost", over=None, **o):
    o = {**DEFAULTS, **o}
    D = fm.data(); rules = D.lv["combat_rules"]; mm = D.lv["mob_model"]
    ch = fm.character(level, race, over)
    mlevel = level + o["level_diff"]; H = mob_hp(mlevel)
    main = _opener(rotation)
    wc = fm.tval(pts, "wintersChill", 1, 0) * min(1.0, fm.tval(pts, "wintersChill", 0) / 100.0 * 3)  # empilements moyens EST
    e = fm.expected_cast(main, level, pts, ch, o["level_diff"], wc_stacks=wc)
    c = e["cast"]; D_cast = e["dmg"]; m_cast = e["mana"]
    frng = float(e["range"]) * (1 + fm.tval(pts, "arcticReach") / 100.0 if main == "frostbolt" else 1)
    speed = fm.spell(main).get("projectile_speed", 28)
    slow = (fm.spell("frostbolt")["slow"] + fm.tval(pts, "permafrost", 1) / 100.0) if main == "frostbolt" else 0.0
    run = mm["run_speed"] * (1 - slow * e["hit"])
    T0 = c + frng / speed + (frng - mm["melee_range"]) / run
    swing = mm["swing_s"] * (1 + D.utility["frost_armor"]["attacker_swing_slow"])
    p_land = 1 - mm["avoid_vs_mage"]
    burning = fm.tval(pts, "burningSoul", 0) / 100.0 if main == "fireball" else 0.0
    push_per_s = p_land / swing * rules["pushback_s"] * (1 - burning)
    c_melee = c / max(0.2, 1 - push_per_s)
    # gel : Frostbite (5 s) et Fingers of Frost -> Ice Lance
    fbite = fm.tval(pts, "frostbite") / 100.0 if main == "frostbolt" else 0.0
    frz_per_cast = fbite * e["hit"] * 5.0
    has_il = fm.best_rank("ice_lance", level, pts) is not None and rotation == "frost"
    il = fm.expected_cast("ice_lance", level, pts, ch, o["level_diff"], frozen=True, wc_stacks=wc) if has_il else None
    fof_p = fm.tval(pts, "fingersOfFrost", 0) / 100.0 if has_il else 0.0
    # cycle en mêlée : un sort principal, puis Ice Lance pendant le gel
    il_casts = (frz_per_cast / rules["gcd"] + fof_p * e["hit"]) if has_il else 0.0
    cyc_time = c_melee * (1 - min(0.9, frz_per_cast / max(c_melee, 1e-6)) * 0.0) + il_casts * rules["gcd"]
    cyc_dmg = D_cast + (il_casts * il["dmg"] if has_il else 0.0)
    cyc_mana = m_cast + (il_casts * il["mana"] if has_il else 0.0)
    if main == "fireball":
        fbl = fm.expected_cast("fire_blast", level, pts, ch, o["level_diff"])
        if fbl:
            k = rules["gcd"] / max(1.0, fbl["cooldown"])                     # part de temps sur Trait de feu
            cyc_dmg += fbl["dmg"] * c_melee / fbl["cooldown"]; cyc_mana += fbl["mana"] * c_melee / fbl["cooldown"]
            cyc_time += rules["gcd"] * c_melee / fbl["cooldown"]
    n_pre = T0 / c
    if H <= n_pre * D_cast:
        combat = H / D_cast * c + frng / speed; t_melee = 0.0; casts = H / D_cast; mana = casts * m_cast
    else:
        t_melee = (H - n_pre * D_cast) / (cyc_dmg / cyc_time)
        combat = T0 + t_melee
        mana = n_pre * m_cast + t_melee / cyc_time * cyc_mana
    frozen_frac = min(0.95, frz_per_cast / cyc_time) if t_melee else 0.0
    hit_raw = mob_hit_raw(mlevel) * (1 - armor_dr(ch["armor"], mlevel))
    taken = t_melee * (1 - frozen_frac) / swing * p_land * hit_raw * (1 + mm["crit"] * (mm["crit_mult"] - 1))
    mana = max(0.0, mana - in_combat_regen_frac(pts, level) * ch["spirit_regen"] * combat)
    water, food = consumables(level)
    down = max(mana / (water + ch["spirit_regen"]), taken / (food + 0.02 * ch["hp"]))
    total = combat + down + o["run_between"]
    return {"combat": combat, "mana": mana, "taken": taken, "downtime": down, "total": total,
            "xp_h": mob_xp(level) * 3600.0 / total}

def parse_talents(s):
    pts = {}
    for part in (s or "").split(","):
        if "=" in part:
            k, v = part.split("="); pts[k.strip()] = int(v)
    return pts

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, required=True); ap.add_argument("--race", default="Orc")
    ap.add_argument("--rotation", default="frost", choices=["frost", "fire"])
    ap.add_argument("--talents", default=""); ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--nova", action="store_true"); ap.add_argument("--profile", default=None)
    a = ap.parse_args(); pts = parse_talents(a.talents); over = None
    if a.profile:
        import import_character as ic
        pr = ic.load(a.profile); over = pr["over"]; a.race = pr["race"]; pts = pts or pr["talents"]
    err = fm.check_build(pts, a.level)
    if err: raise SystemExit("Build illégal : " + " ; ".join(err))
    m = mc(a.level, pts, a.race, a.rotation, a.n, over=over, nova=a.nova); an = kill_analytic(a.level, pts, a.race, a.rotation, over, nova=a.nova)
    print(f"build {fm.data().build} | niveau {a.level} | {a.rotation} | {a.race}")
    for k in ("combat", "mana", "taken", "downtime", "total", "xp_h"):
        print(f"  {k:9s} MC {m[k]:8.1f} | analytique {an[k]:8.1f}")
