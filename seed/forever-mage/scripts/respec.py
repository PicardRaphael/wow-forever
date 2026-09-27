"""respec.py — faut-il réinitialiser ses talents ? Coût (barème bêta/Classic) contre gain (sims). Statut : PC/EST."""
import argparse, fm, sim_leveling as sl

GOLD_PER_HOUR = {10: 1.0, 20: 4.0, 30: 9.0, 40: 16.0, 50: 25.0, 60: 40.0}      # EST : à remplacer par ton propre rythme

def cost(n_previous):
    sch = fm.data().respec["classic_schedule_gold"]
    return sch[min(n_previous, len(sch) - 1)]

def gold_per_hour(level):
    ks = sorted(GOLD_PER_HOUR); lo = max([k for k in ks if k <= level] or [ks[0]])
    return GOLD_PER_HOUR[lo]

def advise_leveling(level, current, target, hours, race="Orc", n_previous=0, trip_minutes=6, gph=None):
    cur = min(sl.kill_analytic(level, current, race, r)["xp_h"] for r in ("frost", "fire"))
    cur = max(sl.kill_analytic(level, current, race, r)["xp_h"] for r in ("frost", "fire"))
    tgt = max(sl.kill_analytic(level, target, race, r)["xp_h"] for r in ("frost", "fire"))
    gain_h = hours * (1 - cur / tgt) if tgt > cur else -hours * (1 - tgt / cur)
    g = cost(n_previous); gph = gph or gold_per_hour(level)
    value = gain_h * gph - g - trip_minutes / 60 * gph
    return {"xp_h_actuel": round(cur), "xp_h_cible": round(tgt), "heures_gagnees": round(gain_h, 2), "cout_po": g,
            "bilan_po_equiv": round(value, 1), "verdict": "réinitialiser" if value > 0 else "garder",
            "hypotheses": f"{gph} po/h (EST), trajet {trip_minutes} min, barème {fm.data().respec['classic_schedule_gold']}"}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--current", required=True); ap.add_argument("--target", required=True)
    ap.add_argument("--hours", type=float, default=10); ap.add_argument("--race", default="Orc"); ap.add_argument("--n", type=int, default=0)
    a = ap.parse_args()
    print(advise_leveling(a.level, sl.parse_talents(a.current), sl.parse_talents(a.target), a.hours, a.race, a.n))
