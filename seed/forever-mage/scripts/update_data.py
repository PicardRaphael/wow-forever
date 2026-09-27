"""update_data.py — garder l'agent à jour avec le client Forever.

  python update_data.py check            # compare le build des données au dernier build publié (wago.tools)
  python update_data.py pull             # reconstruit les talents depuis les sources open source et crée data/<build>/
  python update_data.py diff A B         # liste ce qui a changé entre deux builds de données

Sources (voir references/data-sources.md) :
  - https://wago.tools/api/builds (produit wow_classic_beta, versions 1.60.x ; liste non triée : trier par created_at)
  - https://wago.tools/db2/<Table>/csv?build=<build> (tables Trait*, Spell*, SpellEffect... pour la vérification profonde)
  - arbres de talents wowsims Forever tenus à jour depuis le client (gunba/wow-forever-sim, ElliotWood/Forever, MIT)
Principe : on ne remplace jamais une valeur sans laisser de trace ; toute valeur héritée d'un build précédent est marquée.
"""
import json, os, shutil, sys, urllib.request
import fm

UA = {"User-Agent": "forever-mage-agent/1.0"}
TREE_URL = "https://raw.githubusercontent.com/gunba/wow-forever-sim/master/ui/core/talents/trees/mage.json"
CONF_URL = "https://raw.githubusercontent.com/ElliotWood/Forever/master/assets/confirmed_talents.json"
WAGO_BUILDS = "https://wago.tools/api/builds"
OVERRIDES = os.path.join(fm.DATA, "overrides.json")

def get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()

def latest_wago_build(product="wow_classic_beta", prefix="1.60."):
    raw = json.loads(get(WAGO_BUILDS))
    items = raw.get(product, []) if isinstance(raw, dict) else raw
    items = [b for b in items if str(b.get("version", "")).startswith(prefix)]
    items.sort(key=lambda b: b.get("created_at", ""))
    return items[-1]["version"] if items else None

def check():
    cur = fm.builds()[-1]
    try:
        latest = latest_wago_build()
    except Exception as e:
        latest = None; print(f"wago.tools injoignable ({e}) : vérifie le build à la main sur https://wago.tools/builds")
    try:
        conf = json.loads(get(CONF_URL)); src = conf.get("generated")
    except Exception as e:
        src = None; print(f"source des rangs confirmés injoignable ({e})")
    print(f"données de l'agent : {cur}\ndernier build client : {latest}\nrangs confirmés open source : {src}")
    if latest and fm._vkey(latest) > fm._vkey(cur):
        print("=> NOUVEAU BUILD : lancer `python update_data.py pull`, puis vérifier spells.json (voir references/data-sources.md).")
    else:
        print("=> à jour.")

def build_talents(tree, target_build, overrides):
    out = {"build": target_build, "class": "Mage", "trees": [], "notes": [f"Reconstruit par update_data.py depuis {TREE_URL}"]}
    for tr in tree:
        T = {"name": tr["name"], "talents": []}
        for x in tr["talents"]:
            ov = overrides.get(f"{tr['name']}/{x['name']}")
            ranks = x["ranks"]; cert = "FS-arbre-open-source"
            if ov and fm._vkey(ov["build"]) > fm._vkey(ov.get("source_build", "0.0.0.0")):
                ranks = ov["ranks"]; cert = f"FC-{ov['build']} (correction manuelle)"
            e = {"key": x["fieldName"], "name": x["name"], "tree": tr["name"], "tier": x["location"]["rowIdx"] + 1,
                 "col": x["location"]["colIdx"] + 1, "max": x["maxPoints"], "ranks": ranks, "desc": x["description"],
                 "spellIds": x.get("spellIds", []),
                 "prereq": ({"tier": x["prereqLocation"]["rowIdx"] + 1, "col": x["prereqLocation"]["colIdx"] + 1} if x.get("prereqLocation") else None),
                 "wowsims_not_simulated": bool(x.get("notSimulated")), "certainty": cert}
            T["talents"].append(e)
        out["trees"].append(T)
    return out

def pull(target_build=None):
    cur = fm.builds()[-1]
    target_build = target_build or latest_wago_build() or cur
    tree = json.loads(get(TREE_URL))
    overrides = json.load(open(OVERRIDES)) if os.path.exists(OVERRIDES) else {}
    dst = os.path.join(fm.DATA, target_build)
    if os.path.exists(dst) and target_build != cur:
        raise SystemExit(f"{dst} existe déjà")
    if target_build != cur:
        shutil.copytree(os.path.join(fm.DATA, cur), dst)
        for n in ("spells.json", "racials.json", "leveling.json", "respec.json"):
            p = os.path.join(dst, n); d = json.load(open(p, encoding="utf-8"))
            d["inherited_from"] = cur; d["build"] = target_build
            json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t = build_talents(tree, target_build, overrides)
    json.dump(t, open(os.path.join(dst, "talents.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"talents reconstruits dans {dst}. Les sorts, raciaux et règles sont hérités de {cur} : à revérifier.")
    diff(cur, target_build)

def diff(a, b):
    A = fm.Data(a).T; B = fm.Data(b).T; n = 0
    for k in sorted(set(A) | set(B)):
        if k not in A: print(f"+ nouveau talent : {B[k]['name']}"); n += 1; continue
        if k not in B: print(f"- talent retiré : {A[k]['name']}"); n += 1; continue
        for f in ("tier", "col", "max", "ranks", "prereq"):
            if A[k][f] != B[k][f]:
                print(f"~ {A[k]['name']} : {f} {A[k][f]} -> {B[k][f]}"); n += 1
    print(f"{n} différence(s) de talents entre {a} et {b}.")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check": check()
    elif cmd == "pull": pull(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "diff": diff(sys.argv[2], sys.argv[3])
    else: print(__doc__)
