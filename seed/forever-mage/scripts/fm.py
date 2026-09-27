"""fm.py — cœur de l'agent Mage WoW Forever.

Règle d'or : toute formule de combat passe par ce module. Aucun script ne recalcule
un toucher, un critique ou un coefficient de son côté : c'est ce qui garantit
qu'aucun mécanisme n'est oublié (voir tests/test_mechanics.py).

Chaque valeur porte un statut : FC (client Forever), FS (simulateur Forever),
PC (règle Classic supposée inchangée), EST (estimation à calibrer).
"""
import json, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# --------------------------------------------------------------------------- données
def _vkey(b):
    return tuple(int(x) for x in b.split("."))

def builds():
    return sorted([d for d in os.listdir(DATA) if d[0].isdigit()], key=_vkey)

class Data:
    def __init__(self, build=None):
        self.build = build or builds()[-1]
        d = os.path.join(DATA, self.build)
        ld = lambda n: json.load(open(os.path.join(d, n), encoding="utf-8"))
        self.talents_raw = ld("talents.json")
        self.spells = ld("spells.json")["spells"]
        self.utility = ld("spells.json")["utility"]
        self.racials = ld("racials.json")
        self.lv = ld("leveling.json")
        self.respec = ld("respec.json")
        self.meta = ld("meta.json")
        self.T = {}
        for tr in self.talents_raw["trees"]:
            for t in tr["talents"]:
                t = dict(t); t["tree"] = tr["name"]; self.T[t["key"]] = t
        self.by_pos = {(t["tree"], t["tier"], t["col"]): k for k, t in self.T.items()}

_D = None
def data(build=None):
    global _D
    if _D is None or (build and _D.build != build):
        _D = Data(build)
    return _D

# --------------------------------------------------------------------------- talents
def rank(pts, key):
    return pts.get(key, 0)

def tval(pts, key, i=0, default=0.0):
    """Valeur i du rang actuel du talent (0 si non pris)."""
    r = pts.get(key, 0)
    if r <= 0:
        return default
    ranks = data().T[key]["ranks"]
    v = ranks[min(r, len(ranks)) - 1]
    return v[i] if i < len(v) else default

def points_available(level, talented_bonus=0):
    """Points = niveau - 9 ; le bonus Legacy 'Talented' avance le premier point (non actif en bêta)."""
    return max(0, level - 9 + talented_bonus)

def check_build(pts, level=60, talented_bonus=0):
    """Renvoie la liste des erreurs de légalité (vide = build légal)."""
    D = data(); err = []
    total = sum(pts.values())
    if total > points_available(level, talented_bonus):
        err.append(f"{total} points pour {points_available(level, talented_bonus)} disponibles au niveau {level}")
    for k, r in pts.items():
        if r <= 0:
            continue
        if k not in D.T:
            err.append(f"talent inconnu : {k}"); continue
        t = D.T[k]
        if r > t["max"]:
            err.append(f"{t['name']} : {r}/{t['max']}")
        before = sum(v for kk, v in pts.items() if kk in D.T and D.T[kk]["tree"] == t["tree"] and D.T[kk]["tier"] < t["tier"])
        if before < 5 * (t["tier"] - 1):
            err.append(f"{t['name']} (palier {t['tier']}) exige {5*(t['tier']-1)} points avant, {before} dépensés")
        if t["prereq"]:
            pk = D.by_pos.get((t["tree"], t["prereq"]["tier"], t["prereq"]["col"]))
            if pk and pts.get(pk, 0) < D.T[pk]["max"]:
                err.append(f"{t['name']} exige {D.T[pk]['name']} au maximum")
    return err

def legal_additions(pts, level=60, talented_bonus=0):
    """Talents auxquels on peut ajouter 1 point maintenant."""
    out = []
    if sum(pts.values()) >= points_available(level, talented_bonus):
        return out
    for k in data().T:
        p2 = dict(pts); p2[k] = p2.get(k, 0) + 1
        if not check_build(p2, level, talented_bonus):
            out.append(k)
    return out

def tree_split(pts):
    s = {"Arcane": 0, "Fire": 0, "Frost": 0}
    for k, r in pts.items():
        s[data().T[k]["tree"]] += r
    return s

# --------------------------------------------------------------------------- personnage
def int_per_crit(level):
    """Int pour 1 % de critique des sorts. 59,5 au niveau 60 (Mage Classic ; Forever : 54-60 pour les lanceurs).
    Entre 1 et 60 : interpolation linéaire depuis 6 (EST, à remplacer par la table du client ou la fiche perso)."""
    return 6.0 + (59.5 - 6.0) * (max(1, min(60, level)) - 1) / 59.0

def character(level, race="Orc", over=None):
    """Stats du personnage. `over` (import de fiche) remplace toute estimation : c'est la voie à privilégier."""
    over = over or {}
    L = level
    c = {"level": L, "race": race}
    c["int"] = over.get("int", 21 + 1.76 * (L - 1) + 0.8 * max(0, L - 5))
    c["spirit"] = over.get("spirit", (22 + 1.66 * (L - 1) + 0.5 * max(0, L - 5)) * (1.05 if race == "Human" else 1.0))
    c["sp"] = over.get("sp", 0.4 * L if L >= 10 else 0.0)
    base_mana = 100 + 18.9 * (L - 1)
    c["base_mana"] = over.get("base_mana", base_mana)
    mana = base_mana + min(c["int"], 20) + 15 * max(0.0, c["int"] - 20)
    if race == "Gnome":
        mana *= 1.05
    c["mana"] = over.get("mana", mana)
    if "spell_crit" in over:
        c["crit"] = over["spell_crit"]           # fiche perso : critique des sorts affiché (fraction)
    else:
        c["crit"] = 0.002 + c["int"] / int_per_crit(L) / 100.0 + over.get("crit_gear", 0.0)
        if race == "Human" and over.get("sword"):
            c["crit"] += 0.02
    c["hit_gear"] = over.get("hit_gear", 0.0)
    c["haste"] = over.get("haste", 0.0)
    c["hp"] = over.get("hp", 40 + 12 * L + 0.25 * L * L)
    c["armor"] = over.get("armor", 2 * (20 + 0.5 * L) + 4 * L)
    c["spirit_regen"] = (13 + c["spirit"] / 4.0) / 2.0          # mana/s hors règle des 5 s (PC)
    c["over"] = over
    return c

# --------------------------------------------------------------------------- sorts
SCHOOL_FROST = {"frost", "frostfire"}
SCHOOL_FIRE = {"fire", "frostfire"}

def spell(key):
    return data().spells[key]

def best_rank(key, level, pts):
    """Plus haut rang appris. Les sorts de talent exigent le talent (rang 1 = talent)."""
    s = spell(key)
    if "talent" in s and pts.get(s["talent"], 0) <= 0:
        return None
    ok = [r for r in s["ranks"] if r[0] <= level]
    if "talent" in s:
        ok = [s["ranks"][0]] + [r for r in s["ranks"][1:] if r[0] <= level]
    return ok[-1] if ok else None

# coefficients : direct = incantation/3,5 (1,5..3,5), ×0,95 si ralenti ; canalisé = durée/3,5 ; zone : valeurs Classic (PC) ; Ice Lance : EST
COEF_FIXED = {"fire_blast": 1.5 / 3.5, "scorch": 1.5 / 3.5, "ice_lance": 0.1429, "arcane_explosion": 0.143, "frost_nova": 0.043,
              "cone_of_cold": 0.143 * 0.95, "blast_wave": 0.143, "blizzard": 0.333, "flamestrike": 0.157}

def coefficient(key, r):
    lvl, mn, mx, dot, dotdur, cast, mana, cd = r
    if key in COEF_FIXED:
        c = COEF_FIXED[key]
    elif spell(key).get("channel"):
        c = min(cast, 5.0) / 3.5
    else:
        c = min(3.5, max(1.5, cast)) / 3.5
        if spell(key).get("slow"):
            c *= 0.95
    if lvl < 20:
        c *= max(0.0, 1 - 0.0375 * (20 - lvl))
    return c

def hit_chance(school, level_diff, pts, ch):
    rules = data().lv["combat_rules"]
    t = rules["spell_miss_by_level_diff"]
    miss = t.get(str(level_diff), t["-"] if level_diff < 0 else t["5"])
    if school in SCHOOL_FROST or school in SCHOOL_FIRE:
        miss -= tval(pts, "elementalPrecision") / 100.0
    if school == "arcane":
        miss -= tval(pts, "arcaneFocus") / 100.0
    miss -= ch.get("hit_gear", 0.0)
    return 1.0 - max(rules["min_miss"], miss)

def crit_chance(key, school, pts, ch, frozen=False, wc_stacks=0, buffs=None):
    buffs = buffs or {}
    c = ch["crit"]
    c += tval(pts, "arcaneInstability", 1) / 100.0
    if school in SCHOOL_FIRE:
        c += tval(pts, "criticalMass") / 100.0
    if school == "arcane":
        c += tval(pts, "arcaneImpact") / 100.0
    if key in ("fire_blast", "ice_lance", "arcane_blast", "scorch"):
        c += tval(pts, "incineration") / 100.0
    if frozen:
        c += tval(pts, "shatter") / 100.0
    if key in ("frostbolt", "ice_lance"):
        c += 0.02 * wc_stacks
    c += buffs.get("crit", 0.0)
    return max(0.0, min(1.0, c))

def crit_mult(school, pts):
    base_bonus = data().lv["combat_rules"]["crit_mult_spell"] - 1.0      # +50 %
    if school in SCHOOL_FROST:
        return 1 + base_bonus * (1 + tval(pts, "iceShards") / 100.0)
    if school == "arcane":
        return 1 + base_bonus * (1 + tval(pts, "arcaneMind", 1) / 100.0)
    return 1 + base_bonus

def dmg_mult(school, pts, buffs=None):
    buffs = buffs or {}
    m = 1 + tval(pts, "arcaneInstability") / 100.0
    if school in SCHOOL_FROST:
        m *= 1 + tval(pts, "piercingIce") / 100.0
    if school in SCHOOL_FIRE:
        m *= 1 + tval(pts, "firePower") / 100.0
    m *= 1 + buffs.get("dmg", 0.0)
    return m

def cast_time(key, r, pts, ch, buffs=None):
    buffs = buffs or {}
    cast = r[5]
    if key == "frostbolt":
        cast -= tval(pts, "improvedFrostbolt")
    if key in ("fireball", "frostfire_bolt"):
        cast -= tval(pts, "improvedFireball")
    if cast <= 0 or spell(key).get("channel"):
        return max(data().lv["combat_rules"]["gcd"], cast)
    cast /= (1 + ch.get("haste", 0.0) + buffs.get("haste", 0.0))
    return max(data().lv["combat_rules"]["gcd"], cast)

def mana_cost(key, r, pts, ch, buffs=None):
    buffs = buffs or {}
    s = spell(key)
    if s.get("mana_pct_base"):
        m = s["mana_pct_base"] * ch["base_mana"]
    elif r[6] is None:
        nxt = [x for x in s["ranks"] if x[6]]
        m = nxt[0][6] * 0.75 if nxt else 50.0                  # EST : rang de talent sans coût publié
    else:
        m = r[6]
    if s["school"] in SCHOOL_FROST:
        m *= 1 - tval(pts, "frostChanneling") / 100.0
    m *= 1 + buffs.get("cost", 0.0)
    return m

def spell_power(ch, buffs=None):
    buffs = buffs or {}
    return ch["sp"] * (1 + buffs.get("sp_pct", 0.0)) + buffs.get("sp_flat", 0.0)

def expected_cast(key, level, pts, ch, level_diff=0, frozen=False, wc_stacks=0, buffs=None, frozen_mult=True):
    """Espérance d'un sort : dégâts (toucher, critique, multiplicateurs, DoT qui critiquent, Ignite),
    mana (Frost Channeling, Master of Elements, Clearcasting), temps d'incantation. None si non appris."""
    r = best_rank(key, level, pts)
    if not r:
        return None
    s = spell(key); school = s["school"]
    hit = hit_chance(school, level_diff, pts, ch)
    crit = crit_chance(key, school, pts, ch, frozen, wc_stacks, buffs)
    cm = crit_mult(school, pts)
    dm = dmg_mult(school, pts, buffs)
    sp = spell_power(ch, buffs)
    base = (r[1] + r[2]) / 2.0 + coefficient(key, r) * sp
    if key == "ice_lance" and frozen and frozen_mult:
        base *= s.get("frozen_mult", 4.0)
    direct = base * dm * (1 + crit * (cm - 1))
    dot = r[3] * dm * (1 + (crit * (cm - 1) if data().lv["combat_rules"]["dot_can_crit"] else 0.0))
    ignite = 0.0
    if school in SCHOOL_FIRE:
        ignite = crit * base * dm * cm * tval(pts, "ignite") / 100.0
    dmg = hit * (direct + dot + ignite)
    mana = mana_cost(key, r, pts, ch, buffs)
    base_mana_cost = r[6] if r[6] else mana
    if school in SCHOOL_FIRE or school in SCHOOL_FROST:
        mana -= hit * crit * tval(pts, "masterOfElements") / 100.0 * base_mana_cost
    mana *= 1 - hit * tval(pts, "arcaneConcentration") / 100.0
    return {"key": key, "rank": r, "school": school, "hit": hit, "crit": crit, "crit_mult": cm, "dmg_mult": dm,
            "dmg": dmg, "direct_per_hit": direct, "dot": dot, "ignite": ignite, "mana": mana,
            "cast": cast_time(key, r, pts, ch, buffs), "range": s.get("range", 30), "cooldown": r[7]}

def mechanics_used():
    """Inventaire vérifié par les tests : chaque entrée doit influencer au moins un calcul."""
    return ["toucher/écart de niveau", "plafond de toucher", "Elemental Precision", "Arcane Focus", "critique Int/niveau",
            "critique d'équipement", "critique épée Humain", "Arcane Instability", "Critical Mass", "Arcane Impact",
            "Incineration", "Shatter (gelé)", "Winter's Chill", "multiplicateur de critique", "Ice Shards", "Arcane Mind",
            "DoT qui critiquent", "Ignite", "Piercing Ice", "Fire Power", "coefficients", "pénalité < 20",
            "Improved Frostbolt", "Improved Fireball", "hâte", "temps de recharge global", "Frost Channeling",
            "Master of Elements", "Arcane Concentration", "sorts en % du mana de base"]
