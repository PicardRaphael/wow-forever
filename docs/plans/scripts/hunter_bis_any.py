"""Listes !NBIS1! du Chasseur par tranche (10-19 … 50-59) et au 60 (BG, raid-donjon) ; script de passage."""

import json
import sys
from pathlib import Path

from forever.config import default_deps
from forever.exports.naowh import naowh_bis
from forever.gear import _addons_dir, leveling_gear, naowh_weights  # noqa: F401
from forever.pipeline.wowsims_build import wowsims_dir
from forever.sims import wowsims
from forever.sims.brackets import item_database, pool_from_sources

deps = default_deps()
db = item_database(deps.cache_dir)
addons = _addons_dir(deps)
names = wowsims.stat_names(wowsims_dir(deps.cache_dir) / "forever")
TYPE_TO_BIS = {
    1: [1],
    2: [2],
    3: [3],
    4: [15],
    5: [5],
    6: [9],
    7: [10],
    8: [6],
    9: [7],
    10: [8],
    11: [11, 12],
    12: [13, 14],
    14: [18],
}
SLOT_NAME = {
    1: "Tête",
    2: "Cou",
    3: "Épaules",
    5: "Torse",
    6: "Taille",
    7: "Jambes",
    8: "Pieds",
    9: "Poignets",
    10: "Mains",
    11: "Doigt",
    12: "Doigt 2",
    13: "Bijou",
    14: "Bijou 2",
    15: "Dos",
    16: "Main droite",
    17: "Main gauche",
    18: "Distance",
}
import os

RACE = os.environ.get("RACE", "Orc")
FACTION = os.environ.get("FACTION", "horde")
HORDE_RANKS = (
    "Warlord",
    "Blood Guard",
    "Legionnaire",
    "Champion's",
    "General's",
    "Stone Guard",
    "Centurion",
    "First Sergeant",
    "Scout's",
    "Frostwolf",
    "Defiler",
)
ALLIANCE_RANKS = (
    "Marshal",
    "Knight-",
    "Lieutenant Commander",
    "Commander's",
    "Field Marshal",
    "Sergeant Major",
    "Stormpike",
    "Arathor",
    "Lieutenant's",
    "Knight-Captain",
)
OTHER_RANKS = ALLIANCE_RANKS if FACTION == "horde" else HORDE_RANKS
OTHER_FACTION = 1 if FACTION == "horde" else 2
EXTRA = 9


def guide_stats(row):
    opt = (row.get("scalingOptions") or {}).get("0") or {}
    out = {}
    for idx, val in (opt.get("stats") or {}).items():
        name = names[int(idx)] if int(idx) < len(names) else None
        for key in wowsims.STAT_TO_GUIDE.get(name, ())[:1]:
            out[key] = out.get(key, 0) + val
    dps = opt.get("unroundedDps")
    return out, dps or 0.0


RAID_ZONES = {2717, 2159, 2677, 1977, 3429, 3428, 3456}  # raids encore fermés


def usable(row, level):
    if any((src.get("drop") or {}).get("zoneId") in RAID_ZONES for src in row.get("sources") or []):
        return False
    if row.get("classAllowlist") and 3 not in row["classAllowlist"]:
        return False
    if any(k in (row.get("name") or "") for k in OTHER_RANKS):
        return False
    for s in row.get("sources") or []:
        sold = s.get("soldBy") or {}
        if sold.get("faction") == OTHER_FACTION:
            return False
    t = row.get("type")
    if t in (1, 3, 5, 6, 7, 8, 9, 10):
        return row.get("armorType", 0) <= (3 if level >= 40 else 2)
    if t == 13:
        return row.get("weaponType") not in (4, 5, 7)
    if t == 14:
        return row.get("rangedWeaponType") in (1, 2, 3)
    return t in TYPE_TO_BIS


def bis_slots(row):
    if row.get("type") == 13:
        return [16] if row.get("handType") == 4 else [16, 17]
    return TYPE_TO_BIS.get(row.get("type"), [])


def is_pvp(row):
    return any("pvp" in s for s in row.get("sources") or [])


VOUCHED = set()  # objets proposés par GearQuest ou Naowh pour Forever


def build(name, spec, ids, weights, level, prefer=None):
    """Classe chaque emplacement par score ; `prefer` : objets à garder en tête s'ils sont candidats."""
    per = {}
    for item in dict.fromkeys(ids):
        row = db.get(int(item))
        if not row or not usable(row, level) or (row.get("reqLvl") or 0) > level:
            continue
        if not row.get("sources") and item not in VOUCHED:
            continue  # source inconnue et non proposé par un addon de Forever
        ilvl = ((row.get("scalingOptions") or {}).get("0") or {}).get("ilvl") or 0
        if level >= 60 and ilvl > 65 and not is_pvp(row):
            continue  # niveau d'objet de raid : raids fermés
        stats, dps = guide_stats(row)
        score = sum(weights.get(k, 0.0) * v for k, v in stats.items()) + 2.0 * dps
        for s in bis_slots(row):
            per.setdefault(s, []).append((item, score))
    slots, extra = {}, {}
    for s in sorted(per):
        order = [i for i, _ in sorted(per[s], key=lambda t: -t[1])]
        if prefer:
            order = [i for i in order if i in prefer] + [i for i in order if i not in prefer]
        pair = {12: 11, 14: 13, 17: 16}.get(s)
        if pair in slots:
            taken = db[slots[pair]]["name"]
            order = [i for i in order if i != slots[pair] and db[i]["name"] != taken]
        if s == 17 and 16 in slots and db[slots[16]].get("handType") == 4:
            continue  # arme à deux mains en main droite : pas de main gauche
        seen_names = set()
        order = [i for i in order if not (db[i]["name"] in seen_names or seen_names.add(db[i]["name"]))]
        if order:
            slots[s] = order[0]
            extra[s] = order[1 : 1 + EXTRA]
    code = naowh_bis(name, spec, slots, extra)
    return (
        code,
        {SLOT_NAME[s]: [db[i]["name"] for i in [slots[s], *extra[s]]] for s in slots},
        {s: [slots[s], *extra[s]] for s in slots},
    )


out = {}
BRACKETS = [(10, 19), (20, 29), (30, 39), (40, 49), (50, 59)]
w_bm = naowh_weights(addons, "beast-mastery-hunter")
for a, b in BRACKETS:
    ids = [int(p["item"]) for p in pool_from_sources(deps, "Hunter", "beast_mastery-hunter", b, RACE)[0]]
    VOUCHED.update(ids)
    ids += [
        i
        for i, r in db.items()
        if a <= (r.get("reqLvl") or 0) <= b
        and (r.get("quality") or 0) >= 2
        and (r.get("phase") or 1) <= 1
        and not is_pvp(r)
    ]
    ids = [i for i in ids if (db.get(i, {}).get("reqLvl") or 0) >= a - 6]
    out[f"{a}-{b}"] = build(f"Chasseur BM {a}-{b}", "beast-mastery-hunter", ids, w_bm, b)

pool60 = [
    int(p["item"])
    for spec in ("beast_mastery-hunter", "marksmanship-hunter", "survival-hunter")
    for p in pool_from_sources(deps, "Hunter", spec, 60, RACE)[0]
]
wide = [
    i
    for i, r in db.items()
    if (r.get("reqLvl") or 0) >= 55 and (r.get("quality") or 0) >= 3 and (r.get("phase") or 1) <= 1
]
p1 = set()
for gset in ("p1", "p1_melee"):
    txt = (
        wowsims_dir(deps.cache_dir) / "forever" / "ui" / "specs" / "hunter" / "dps" / "gear_sets" / f"{gset}.gear.siml"
    ).read_text(encoding="utf-8")
    for line in txt.splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 2:
            slug = parts[1]
            for i, r in db.items():
                if (r.get("name") or "").lower().replace("'", "").replace(" ", "_").replace(":", "") == slug:
                    p1.add(i)
w_sv = naowh_weights(addons, "survival-hunter")
pve = [i for i in pool60 + wide + list(p1) if not is_pvp(db.get(i, {}))]
out["60 raid-donjon"] = build("Chasseur SV 60 raid-donjon", "survival-hunter", pve, w_sv, 60, prefer=p1)
w_mm = naowh_weights(addons, "marksmanship-hunter")
pvp = [i for i in wide + pool60 if is_pvp(db.get(i, {}))]
pvp_set = set(pvp)
out["60 BG"] = build("Chasseur MM 60 BG", "marksmanship-hunter", pvp + pool60, w_mm, 60, prefer=pvp_set)
Path(sys.argv[1]).write_text(
    json.dumps({k: {"code": v[0], "slots": v[1], "ids": v[2]} for k, v in out.items()}, ensure_ascii=False, indent=1),
    encoding="utf-8",
)
for k, (code, slots, _ids) in out.items():
    print("==", k, "|", sum(len(v) for v in slots.values()), "objets")
    for s, items in slots.items():
        print(f"   {s:12} {items[0]}  (+{len(items) - 1})")
