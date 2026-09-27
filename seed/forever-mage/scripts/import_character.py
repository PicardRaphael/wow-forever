"""import_character.py — enregistrer la vraie fiche du personnage : elle remplace toutes les estimations.

  python import_character.py --name raphael --level 16 --race Orc --int 52 --spirit 48 --sp 9 --spell-crit 0.031 \
         --talents improvedFrostbolt=5,elementalPrecision=2
Relève les valeurs dans la fenêtre du personnage (onglet Sorts : critique des sorts en %, puissance des sorts).
Les scripts les lisent avec --profile raphael.
"""
import argparse, json, os
import fm
PROF = os.path.join(fm.ROOT, "profiles")

def save(name, d):
    os.makedirs(PROF, exist_ok=True); json.dump(d, open(os.path.join(PROF, f"{name}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def load(name):
    p = os.path.join(PROF, f"{name}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

if __name__ == "__main__":
    import sim_leveling as sl
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True); ap.add_argument("--level", type=int, required=True); ap.add_argument("--race", default="Orc")
    for f in ("int", "spirit", "sp", "spell-crit", "hit-gear", "haste", "mana", "hp", "armor"):
        ap.add_argument("--" + f, type=float)
    ap.add_argument("--sword", action="store_true"); ap.add_argument("--talents", default="")
    a = ap.parse_args()
    over = {k.replace("-", "_"): getattr(a, k.replace("-", "_")) for k in ("int", "spirit", "sp", "spell-crit", "hit-gear", "haste", "mana", "hp", "armor") if getattr(a, k.replace("-", "_")) is not None}
    if a.sword: over["sword"] = True
    pts = sl.parse_talents(a.talents); err = fm.check_build(pts, a.level)
    if err: raise SystemExit("Talents illégaux : " + " ; ".join(err))
    save(a.name, {"level": a.level, "race": a.race, "over": over, "talents": pts, "build": fm.data().build})
    print(f"profil {a.name} enregistré ({len(over)} stats réelles, {sum(pts.values())} points).")
