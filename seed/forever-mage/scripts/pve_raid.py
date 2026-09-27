"""pve_raid.py — DPS de raid niveau 60 d'un build (Givre, Feu, Arcanes) via le moteur analytique vérifié (engine.js).

Statut : ANALYTIQUE (FS-calibré). Le moteur a passé 20 contrôles dorés et se cale sur MythicSim avec un facteur K
(Givre/Feu/Arcanes ≈ 1,04-1,07). Pour un chiffre de référence, lancer le simulateur open source wowsims Forever
(ElliotWood/Forever ou gunba/wow-forever-sim) : voir references/data-sources.md, section « wowsimcli ».
Usage : python pve_raid.py --spec frost --talents improvedFrostbolt=5,... [--sp 600 --crit 0.18 --hit 0.05]
"""
import argparse, json, os, subprocess
import fm

BRIDGE = os.path.join(fm.ROOT, "engine", "pve_bridge.js")
BOSS_LEVEL_DIFF = 3

def params_from_build(pts):
    """Traduit les rangs de talents du build en paramètres du moteur, avec les valeurs du build de données actif."""
    D = fm.data(); S = D.spells; tv = lambda k, i=0: fm.tval(pts, k, i)
    il = S["ice_lance"]["ranks"][-1]; fb = S["frostbolt"]["ranks"][-1]; fi = S["fireball"]["ranks"][-1]
    return {
        "frost.piercing": tv("piercingIce") / 100, "frost.shards": tv("iceShards") / 100,
        "frost.wc": 0.02 * tv("wintersChill", 1), "frost.fof": tv("fingersOfFrost") / 100 * max(1, tv("fingersOfFrost", 1)),
        "frost.shatter": tv("shatter") / 100, "frost.fbCast": fb[5] - tv("improvedFrostbolt"),
        "frost.fbAvg": (fb[1] + fb[2]) / 2, "frost.fbMana": fb[6] * (1 - tv("frostChanneling") / 100),
        "frost.ilAvg": (il[1] + il[2]) / 2, "frost.ilMana": il[6] * (1 - tv("frostChanneling") / 100),
        "frost.hitT": tv("elementalPrecision"),
        "fire.power": tv("firePower") / 100, "fire.critT": tv("criticalMass"), "fire.incin": tv("incineration"),
        "fire.ignite": tv("ignite") / 100, "fire.fbCast": fi[5] - tv("improvedFireball"),
        "fire.fbAvg": (fi[1] + fi[2]) / 2, "fire.fbDot": fi[3], "fire.fbMana": fi[6],
        "fire.scorchStack": 0.15 if tv("improvedScorch") >= 100 else 0.15 * tv("improvedScorch") / 100,
        "fire.hitT": tv("elementalPrecision"),
        "arc.inst": tv("arcaneInstability") / 100, "arc.ap": 0.30 if pts.get("arcanePower") else 0.0,
        "arc.mind": tv("arcaneMind", 1) / 100, "arc.impact": tv("arcaneImpact"), "arc.mb": 0.40 if pts.get("missileBarrage") else 0.0,
        "arc.cc": tv("arcaneConcentration") / 100, "arc.hitT": tv("arcaneFocus"),
    }

def flags_from_build(pts):
    return {"wc": bool(pts.get("wintersChill")), "fof": bool(pts.get("fingersOfFrost")), "hs": bool(pts.get("hotStreak")),
            "blast": True, "ap": bool(pts.get("arcanePower")), "evoc": True}

def raid_dps(spec, pts, sp=600, crit=0.15, hit_gear=0.0, T=180, race="Gnome", haste=0.0):
    ch = fm.character(60, race, {"sp": sp, "spell_crit": crit, "hit_gear": hit_gear, "haste": haste})
    school = {"frost": "frost", "fire": "fire", "arcane": "arcane"}[spec]
    H = fm.hit_chance(school, BOSS_LEVEL_DIFF, pts, ch)
    crit_t = crit + fm.tval(pts, "arcaneInstability", 1) / 100
    q = {"spec": spec, "params": params_from_build(pts), "flags": flags_from_build(pts),
         "ctx": {"T": T, "crit": crit_t, "H": H, "R": 0.0375, "sp": sp, "haste": 1 + haste, "baseMana": ch["base_mana"], "pool": ch["mana"]}}
    r = subprocess.run(["node", BRIDGE], input=json.dumps(q), capture_output=True, text=True, check=True)
    out = json.loads(r.stdout); out["hit"] = H; out["crit"] = crit_t
    return out

if __name__ == "__main__":
    import sim_leveling as sl
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, choices=["frost", "fire", "arcane"]); ap.add_argument("--talents", default="")
    ap.add_argument("--sp", type=float, default=600); ap.add_argument("--crit", type=float, default=0.15)
    ap.add_argument("--hit", type=float, default=0.0); ap.add_argument("--race", default="Gnome")
    a = ap.parse_args(); pts = sl.parse_talents(a.talents)
    err = fm.check_build(pts, 60)
    if err: raise SystemExit("Build illégal : " + " ; ".join(err))
    o = raid_dps(a.spec, pts, a.sp, a.crit, a.hit, race=a.race)
    print(f"build {fm.data().build} | {a.spec} | DPS analytique {o['dps']:.1f} | toucher {o['hit']:.1%} | crit {o['crit']:.1%}")
    for n, v in o["parts"]: print(f"  {n:40s} {v:7.1f}")
