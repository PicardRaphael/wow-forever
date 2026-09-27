"""optimize.py — recherche de builds : leveling (ordre des points niveau par niveau), raid (51 points), PvP.

Méthode (voir references/method.md) :
  - leveling : recherche en faisceau sur les ordres légaux, notée par le temps total pondéré par l'XP de chaque
    niveau (modèle analytique), avec anticipation (rollout) pour ne pas rater les talents « déclencheurs » dont
    la valeur n'apparaît qu'après (Frostbite avant Ice Lance, Ice Lance avant Fingers of Frost...).
    Le meilleur ordre est ensuite validé au Monte Carlo.
  - raid : faisceau sur les 51 points noté par le moteur analytique (pve_raid), variantes Givre/Feu/Arcanes.
  - PvP : faisceau noté par pvp.score() (modèle de scénarios, statut EST).
Usage :
  python optimize.py leveling --race Orc --from 10 --to 40
  python optimize.py raid --spec frost
  python optimize.py pvp --weights burst=0.35,control=0.25,survival=0.25,sustain=0.15
  python optimize.py score --plan "10:improvedFrostbolt,11:improvedFrostbolt,..."
"""
import argparse, json, subprocess
import fm, sim_leveling as sl

def level_weight(level):
    xp = fm.data().lv["xp_to_next"]["values"]
    return xp[level - 1] / sl.mob_xp(level) if level - 1 < len(xp) else 0.0

def best_rotation_time(level, pts, race, over):
    return min((sl.kill_analytic(level, pts, race, rot, over)["total"], rot) for rot in ("frost", "fire"))

def rollout_value(level, pts, race, over, depth):
    """Complète gloutonnement `depth` points et renvoie le temps obtenu au niveau level+depth."""
    p = dict(pts)
    for d in range(depth):
        L = level + d + 1
        cands = fm.legal_additions(p, L)
        if not cands: break
        best = min(cands, key=lambda k: best_rotation_time(L, {**p, k: p.get(k, 0) + 1}, race, over)[0])
        p[best] = p.get(best, 0) + 1
    return best_rotation_time(min(60, level + depth), p, race, over)[0]

def leveling(race="Orc", lfrom=10, lto=60, beam=3, depth=4, over=None, start=None, mc_n=200, shortlist=4):
    """Faisceau hybride : présélection analytique (avec anticipation), décision au Monte Carlo (tirages communs)."""
    beams = [(0.0, dict(start or {}), [])]
    for L in range(lfrom, lto + 1):
        nxt = []
        for score, pts, hist in beams:
            cands = fm.legal_additions(pts, L) or [None]
            pre = []
            for k in cands:
                p2 = dict(pts)
                if k: p2[k] = p2.get(k, 0) + 1
                t_now, rot = best_rotation_time(L, p2, race, over)
                look = rollout_value(L, p2, race, over, min(depth, 60 - L)) if depth and L < lto else t_now
                pre.append((0.5 * t_now + 0.5 * look, k, p2))
            pre.sort(key=lambda x: x[0])
            for look, k, p2 in pre[:shortlist]:
                if mc_n:
                    t_mc = min((sl.mc(L, p2, race, rot, mc_n, over=over)["total"], rot) for rot in ("frost", "fire"))
                    t_now, rot = t_mc
                else:
                    t_now, rot = best_rotation_time(L, p2, race, over)
                nxt.append((score + t_now * level_weight(L), look, p2, hist + [(L, k, round(t_now, 2), rot)]))
        nxt.sort(key=lambda x: (x[0] + 0.25 * x[1] * level_weight(L)))
        seen = set(); beams = []
        for sc, lk, p2, h in nxt:
            sig = tuple(sorted(p2.items()))
            if sig in seen: continue
            seen.add(sig); beams.append((sc, p2, h))
            if len(beams) >= beam: break
    sc, pts, hist = min(beams, key=lambda b: b[0])
    return {"build": fm.data().build, "hours_equiv": sc / 3600.0, "points": pts, "steps": hist}

def score_plan(plan, race="Orc", over=None):
    """plan : liste (niveau, talent). Renvoie les heures équivalentes (même métrique que leveling())."""
    pts = {}; total = 0.0; steps = []
    for L in range(min(l for l, _ in plan), max(l for l, _ in plan) + 1):
        for l, k in plan:
            if l == L and k:
                pts[k] = pts.get(k, 0) + 1
        err = fm.check_build(pts, L)
        if err: raise ValueError(f"plan illégal au niveau {L} : {err}")
        t, rot = best_rotation_time(L, pts, race, over); total += t * level_weight(L); steps.append((L, round(t, 2), rot))
    return {"hours_equiv": total / 3600.0, "steps": steps, "points": pts}

# --------------------------------------------------------------------------- raid
def raid(spec="frost", sp=600, crit=0.15, hit=0.0, race="Gnome", beam=4):
    import pve_raid as pr
    beams = [dict()]
    for n in range(1, 52):
        cand = []
        for pts in beams:
            for k in fm.legal_additions(pts, 60):
                p2 = dict(pts); p2[k] = p2.get(k, 0) + 1; cand.append(p2)
        uniq = {tuple(sorted(p.items())): p for p in cand}; cand = list(uniq.values())
        qs = [pr_query(spec, p, sp, crit, hit, race) for p in cand]
        res = run_bridge(qs)
        scored = sorted(zip([r["dps"] for r in res], range(len(cand))), reverse=True)
        beams = [cand[i] for _, i in scored[:beam]]
    best = beams[0]
    import pve_raid as pr2
    return {"build": fm.data().build, "spec": spec, "dps": pr2.raid_dps(spec, best, sp, crit, hit, race=race)["dps"], "points": best, "split": fm.tree_split(best)}

def pr_query(spec, pts, sp, crit, hit, race):
    import pve_raid as pr
    ch = fm.character(60, race, {"sp": sp, "spell_crit": crit, "hit_gear": hit})
    school = spec
    H = fm.hit_chance(school, pr.BOSS_LEVEL_DIFF, pts, ch)
    return {"spec": spec, "params": pr.params_from_build(pts), "flags": pr.flags_from_build(pts),
            "ctx": {"T": 180, "crit": crit + fm.tval(pts, "arcaneInstability", 1) / 100, "H": H, "R": 0.0375, "sp": sp,
                    "haste": 1, "baseMana": ch["base_mana"], "pool": ch["mana"]}}

def run_bridge(qs):
    import pve_raid as pr
    r = subprocess.run(["node", pr.BRIDGE], input=json.dumps(qs), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

# --------------------------------------------------------------------------- PvP
def pvp(weights=None, level=60, race="Orc", beam=4):
    import pvp as pv
    beams = [dict()]
    for n in range(1, fm.points_available(level) + 1):
        cand = {}
        for pts in beams:
            for k in fm.legal_additions(pts, level):
                p2 = dict(pts); p2[k] = p2.get(k, 0) + 1; cand[tuple(sorted(p2.items()))] = p2
        scored = sorted(cand.values(), key=lambda p: -pv.score(p, level, race, weights)["score"])
        beams = scored[:beam]
    best = beams[0]
    return {"build": fm.data().build, "points": best, "split": fm.tree_split(best), "profile": pv.score(best, level, race, weights)}

def fmt_points(pts):
    D = fm.data(); by_tree = {}
    for k, r in sorted(pts.items(), key=lambda kv: (D.T[kv[0]]["tree"], D.T[kv[0]]["tier"], D.T[kv[0]]["col"])):
        by_tree.setdefault(D.T[k]["tree"], []).append(f"{D.T[k]['name']} {r}/{D.T[k]['max']}")
    return " | ".join(f"{t} : " + ", ".join(v) for t, v in by_tree.items())

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("leveling"); a1.add_argument("--race", default="Orc"); a1.add_argument("--from", dest="lfrom", type=int, default=10)
    a1.add_argument("--to", dest="lto", type=int, default=30); a1.add_argument("--beam", type=int, default=3); a1.add_argument("--depth", type=int, default=4); a1.add_argument("--mc", type=int, default=200)
    a2 = sub.add_parser("raid"); a2.add_argument("--spec", default="frost"); a2.add_argument("--sp", type=float, default=600)
    a2.add_argument("--crit", type=float, default=0.15); a2.add_argument("--hit", type=float, default=0.0); a2.add_argument("--race", default="Gnome")
    a3 = sub.add_parser("pvp"); a3.add_argument("--weights", default=""); a3.add_argument("--level", type=int, default=60); a3.add_argument("--race", default="Orc")
    a4 = sub.add_parser("score"); a4.add_argument("--plan", required=True); a4.add_argument("--race", default="Orc")
    a = ap.parse_args()
    if a.cmd == "leveling":
        r = leveling(a.race, a.lfrom, a.lto, a.beam, a.depth, mc_n=a.mc)
        print(f"build {r['build']} | temps pondéré {r['hours_equiv']:.2f} h (combat + repos, monstres équivalents)")
        for L, k, t, rot in r["steps"]:
            print(f"  niv {L:2d} : {fm.data().T[k]['name'] if k else '-':24s} {t:6.1f} s/monstre ({'Givre' if rot=='frost' else 'Feu'})")
        print("  final :", fmt_points(r["points"]))
    elif a.cmd == "raid":
        r = raid(a.spec, a.sp, a.crit, a.hit, a.race)
        print(f"build {r['build']} | {a.spec} | DPS {r['dps']:.1f} | répartition {r['split']}\n  {fmt_points(r['points'])}")
    elif a.cmd == "pvp":
        w = {k: float(v) for k, v in (x.split("=") for x in a.weights.split(",") if "=" in x)} or None
        r = pvp(w, a.level, a.race)
        print(f"build {r['build']} | PvP | répartition {r['split']} | profil {json.dumps(r['profile'], ensure_ascii=False)}\n  {fmt_points(r['points'])}")
    else:
        plan = [(int(x.split(':')[0]), x.split(':')[1]) for x in a.plan.split(',')]
        r = score_plan(plan, a.race); print(f"temps pondéré {r['hours_equiv']:.2f} h")
