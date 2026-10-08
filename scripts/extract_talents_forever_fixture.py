"""Extrait hors ligne, de l'addon Talents Forever installé, les fixtures de FA1 (`tests/fixtures/talents_forever/`).

    uv run python scripts/extract_talents_forever_fixture.py [--addon <dossier TalentsForeverBook>]

Lecture locale de `Data.lua` par `forever/pipeline/lua_table.py`, jamais par du Lua exécuté ; rien du code de l'addon
ni de ses textes n'est recopié. Écrit (octets, fins de ligne LF) :

- `popular.json` : en-tête de l'addon (version du `.toc`, `build`, `generated`, `codeVersion`) et, par classe, les
  agrégats du bloc `popular` (`builds`, `window`, `asOf`, `full`, `spec`, et pour chaque build `code`, `lead`, `pts`,
  `rank`) ;
- `layout.json` : par classe, arbres de l'addon dans son ordre, et pour chaque position de liste notre clé
  (`classes.json` de la version installée), plus ses seuls écarts : nœud numéroté autrement (`node`), prérequis
  différent du nôtre (`req`), position sans correspondance (`tf` : nom, sort, rangée, colonne, rangs, nœud) ; nos
  talents sans correspondance avec leur raison.

`mage_builds.json` n'est pas écrit ici : builds fixes sourcés (témoins relevés en jeu), jamais recalculés par
l'optimiseur, pour qu'un changement des données ne casse pas les tests du format.

Contrôle avant écriture : le `Data.lua` synthétique de `tests/talents_forever_data.py`, rebâti depuis `classes.json`
et ces fixtures, rend exactement les champs lus de l'addon (nom, rangs, rangée, colonne, nœud, sort, prérequis par
position ; agrégats des builds populaires)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from talents_forever_data import build_doc

from forever.addons import _version
from forever.config import default_wow_dir
from forever.pipeline.lua_table import parse_lua_value_at
from forever.pipeline.talents_forever import read_head_and_doc
from forever.store import current_identity

OUT = ROOT / "tests" / "fixtures" / "talents_forever"
DATA_DIR = ROOT / "forever" / "data"
POPULAR = "TalentsForeverBookData.popular ="
POPULAR_FIELDS = ("builds", "window", "asOf", "full", "spec")
BUILD_FIELDS = ("rank", "lead", "pts", "code")
POSITION_FIELDS = ("name", "max", "row", "col", "node", "spell", "req")


def read_addon(folder: Path) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    version = _version(folder)
    if version is None:
        raise SystemExit(f"{folder} : version du .toc introuvable")
    head, doc = read_head_and_doc(folder / "Data.lua")
    text = (folder / "Data.lua").read_text(encoding="utf-8")
    popular, _ = parse_lua_value_at(text, text.index("{", text.index(POPULAR)))
    if not isinstance(popular, dict):
        raise SystemExit("bloc popular illisible")
    return version, head, doc, popular


def popular_fixture(version: str, head: dict[str, Any], popular: dict[str, Any]) -> dict[str, Any]:
    classes = {
        file: {
            **{k: block[k] for k in POPULAR_FIELDS},
            "top": [{k: b[k] for k in BUILD_FIELDS} for b in block["top"]],
        }
        for file, block in popular.items()
    }
    return {"addon": {"version": version, **head}, "classes": classes}


def layout_fixture(doc: dict[str, Any], classes_json: Path, game_version: str) -> dict[str, Any]:
    ours = {c["file"]: c for c in json.loads(classes_json.read_text(encoding="utf-8"))["classes"].values()}
    out: dict[str, Any] = {}
    for file, cls in doc["classes"].items():
        mine = ours[file]
        trees = []
        referenced: set[str] = set()
        matched: set[str] = set()
        for ti, tree in enumerate(cls["trees"]):
            my_talents = mine["trees"][ti]["talents"]
            positions: list[dict[str, Any]] = []
            for t in tree["talents"]:
                same = [
                    m
                    for m in my_talents
                    if m["spell_id"] == t.get("spell") and m["tier"] == t["row"] and m["col"] == t["col"]
                ]
                if len(same) == 1:
                    m = same[0]
                    matched.add(m["key"])
                    pos: dict[str, Any] = {"key": m["key"]}
                    if t.get("node") != m["node_id"]:
                        pos["node"] = t.get("node")
                    if t.get("name") != m["name"] or t.get("max") != m["max"]:
                        raise SystemExit(f"{file} {m['key']} : nom ou rangs différents (à décrire dans la fixture)")
                    positions.append(pos)
                    continue
                spell = [m for m in my_talents if m["spell_id"] == t.get("spell")]
                tf = {k: t.get(k) for k in ("name", "spell", "row", "col", "max", "node")}
                if len(same) > 1:
                    positions.append({"tf": tf, "reason": "ambigu"})
                elif len(spell) == 1 and spell[0]["tier"] is None:
                    referenced.add(spell[0]["key"])
                    positions.append({"tf": tf, "reason": "position_inconnue", "key": spell[0]["key"]})
                else:
                    positions.append({"tf": tf, "reason": "seulement_talents_forever"})
            trees.append({"name": tree["name"], "positions": positions})
        forever_only = [
            {"key": m["key"], "reason": "seulement_forever"}
            for tree in mine["trees"]
            for m in tree["talents"]
            if m["key"] not in matched and m["key"] not in referenced
        ]
        out[file] = {"name": cls["name"], "trees": trees, "forever_only": forever_only}
    # prérequis : écart avec celui que rebâtit l'aide de test, écrit seulement là où il diffère
    draft = {"game_version": game_version, "classes": out}
    rebuilt = build_doc(
        classes_json, draft, {"addon": {"build": "", "generated": "", "codeVersion": ""}, "classes": {}}
    )
    for file, cls in doc["classes"].items():
        for ti, tree in enumerate(cls["trees"]):
            for i, t in enumerate(tree["talents"]):
                if rebuilt["classes"][file]["trees"][ti]["talents"][i].get("req") != t.get("req"):
                    out[file]["trees"][ti]["positions"][i]["req"] = t.get("req")
    return draft


def check(doc: dict[str, Any], popular: dict[str, Any], classes_json: Path, lay: dict[str, Any], pop: dict[str, Any]):
    rebuilt = build_doc(classes_json, lay, pop)
    for file, cls in doc["classes"].items():
        for ti, tree in enumerate(cls["trees"]):
            mine = rebuilt["classes"][file]["trees"][ti]
            if tree["name"] != mine["name"] or len(tree["talents"]) != len(mine["talents"]):
                raise SystemExit(f"{file} arbre {ti + 1} : structure différente")
            for a, b in zip(tree["talents"], mine["talents"], strict=True):
                for k in POSITION_FIELDS:
                    if a.get(k) != b.get(k):
                        raise SystemExit(f"{file} {a.get('name')} : {k} {a.get(k)!r} != {b.get(k)!r}")
    for file, block in popular.items():
        mine = rebuilt["popular"][file]
        if any(block[k] != mine[k] for k in POPULAR_FIELDS):
            raise SystemExit(f"{file} : agrégats différents")
        for a, b in zip(block["top"], mine["top"], strict=True):
            if any(a[k] != b[k] for k in BUILD_FIELDS):
                raise SystemExit(f"{file} build {a['rank']} : différent")


def write(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"écrit : {path.relative_to(ROOT).as_posix()}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--addon", type=Path)
    args = parser.parse_args(argv)
    folder = args.addon or default_wow_dir() / "Interface" / "AddOns" / "TalentsForeverBook"
    game_version = current_identity(DATA_DIR).game_version
    classes_json = DATA_DIR / game_version / "classes.json"
    version, head, doc, popular = read_addon(folder)
    pop = popular_fixture(version, head, popular)
    lay = layout_fixture(doc, classes_json, game_version)
    check(doc, popular, classes_json, lay, pop)
    write(OUT / "popular.json", pop)
    write(OUT / "layout.json", lay)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
