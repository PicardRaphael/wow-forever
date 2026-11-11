"""Listes !NBIS1! du Chasseur reclassées par simulation wowsims (optimise_from_sources), tranche par tranche."""

import json
import sys
from pathlib import Path

from forever.config import default_deps
from forever.exports.naowh import naowh_bis
from forever.sims.brackets import item_database, optimise_from_sources

deps = default_deps()
db = item_database(deps.cache_dir)
lists = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
BIS_TO_WS = {
    1: "Head",
    2: "Neck",
    3: "Shoulder",
    15: "Back",
    5: "Chest",
    9: "Wrist",
    10: "Hands",
    6: "Waist",
    7: "Legs",
    8: "Feet",
    11: "Finger1",
    12: "Finger2",
    13: "Trinket1",
    14: "Trinket2",
    16: "MainHand",
    17: "OffHand",
    18: "Ranged",
}
WS_TO_BIS = {v: k for k, v in BIS_TO_WS.items()}
PLAN = {
    "10-19": (15, "hunter/dps/bm", "beast-mastery-hunter", "Chasseur BM 10-19"),
    "20-29": (25, "hunter/dps/bm", "beast-mastery-hunter", "Chasseur BM 20-29"),
    "30-39": (35, "hunter/dps/bm", "beast-mastery-hunter", "Chasseur BM 30-39"),
    "40-49": (45, "hunter/dps/bm", "beast-mastery-hunter", "Chasseur BM 40-49"),
    "50-59": (55, "hunter/dps/bm", "beast-mastery-hunter", "Chasseur BM 50-59"),
    "60 raid-donjon": (60, "hunter/dps/sv_weave", "survival-hunter", "Chasseur SV 60 raid-donjon"),
    "60 BG": (60, "hunter/dps/mm", "marksmanship-hunter", "Chasseur MM 60 BG"),
}
out = {}
for key, (level, preset, spec, name) in PLAN.items():
    if len(sys.argv) > 3 and key not in sys.argv[3].split(","):
        continue
    ids = {int(s): v for s, v in lists[key]["ids"].items()}
    equipped = {BIS_TO_WS[s]: v[0] for s, v in ids.items() if s in BIS_TO_WS}
    cands = [{"slot": BIS_TO_WS[s], "item": i} for s, v in ids.items() if s in BIS_TO_WS for i in v[1:]]
    doc = optimise_from_sources(
        deps,
        preset=preset,
        race=__import__("os").environ.get("RACE", "Orc"),
        level=level,
        equipped=equipped,
        candidates=cands,
        path="popular",
        iterations=1000,
        objective="leveling" if level < 60 else "dps",
    )
    gains = {}
    for r in doc["candidates"]:
        gains[(WS_TO_BIS[r["slot"]], r["item"])] = (float(r.get("xp_gain", r["gain"])), r.get("verdict"))
    slots, extra, report = {}, {}, {}
    for s, v in ids.items():
        scored = [(v[0], 0.0, "porté")] + [(i, *gains.get((s, i), (-1e9, "non simulé"))) for i in v[1:]]
        scored.sort(key=lambda t: -t[1])
        slots[s] = scored[0][0]
        extra[s] = [i for i, _, _ in scored[1:]]
        report[s] = [(db[i]["name"], round(g, 1) if g > -1e8 else None, verdict) for i, g, verdict in scored]
    out[key] = {
        "objective": doc.get("objective"),
        "base_xp": doc["base"].get("xp_per_hour"),
        "code": naowh_bis(name, spec, slots, extra),
        "report": report,
        "base_dps": doc["base"]["dps"],
        "skipped": len(doc["skipped"]),
    }
    print(
        f"== {key} : base {doc['base']['dps']:.1f} DPS, {len(doc['candidates'])} candidats simulés, "
        f"{len(doc['skipped'])} absents des simulateurs",
        flush=True,
    )
    Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
