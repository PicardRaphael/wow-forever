import re
import statistics
from pathlib import Path

base = "C:/Program Files (x86)/World of Warcraft/_forever_/Interface/AddOns/"
tam = Path(base + "Tamed/src/data/TameableNPCs-Vanilla.lua").read_text(encoding="utf-8")
fdb = {}
for line in Path(base + "LibForeverData/Data/Npcs.lua").read_text(encoding="utf-8").splitlines():
    p = line.rstrip("\n").split(";")
    if len(p) >= 5 and p[0].split("\t")[0].isdigit():
        i, name = p[0].split("\t", 1)
        fdb[int(i)] = (name, p[2], p[3])
MAPS = {
    1438: "Teldrassil",
    1439: "Darkshore",
    1440: "Ashenvale",
    1411: "Durotar",
    1413: "The Barrens",
    1412: "Mulgore",
    1442: "Stonetalon Mountains",
    1424: "Hillsbrad Foothills",
    1441: "Thousand Needles",
    1445: "Dustwallow Marsh",
    1426: "Dun Morogh",
    1429: "Elwynn Forest",
    1436: "Westfall",
    1431: "Duskwood",
    1433: "Redridge Mountains",
    1421: "Silverpine Forest",
    1420: "Tirisfal Glades",
    1437: "Wetlands",
    1432: "Loch Modan",
    1443: "Desolace",
    1434: "Stranglethorn Vale",
}
rows = []
for m in re.finditer(r'\n  \["(\d+)"\] = \{(.*?)\n  \}', tam, re.DOTALL):
    nid, body = int(m.group(1)), m.group(2)
    g = lambda k, body=body: (re.search(rf'\["{k}"\] = "?([^",\n]*)"?', body) or [None, None])[1]
    fam, mp = g("family"), int(g("ui_map_id") or 0)
    if fam not in ("Cat", "Raptor", "Bear", "Boar") or mp not in MAPS:
        continue
    if nid not in fdb:
        continue  # absente de Forever (LibForeverData)
    name, lo, hi = fdb[nid]
    if not lo.isdigit() or int(lo) > 30:
        continue
    ab = re.findall(r'\["key"\] = "(\w+)",\s*\["rank"\] = (\d+)', body)
    xy = re.findall(r"\{([\d.]+), ([\d.]+)\}", body.split('["coords"]')[-1])
    cx = (
        (round(statistics.median(float(a) for a, _ in xy)), round(statistics.median(float(b) for _, b in xy)))
        if xy
        else None
    )
    rows.append((int(lo), int(hi), fam, name, MAPS[mp], cx, ", ".join(f"{k} {r}" for k, r in ab), nid))
for r in sorted(rows, key=lambda r: (r[2], r[0])):
    print(f"{r[2]:6} niv {r[0]:>2}-{r[1]:<2} {r[3]:30} {r[4]:22} {r[5]!s:10} {r[6]}")
